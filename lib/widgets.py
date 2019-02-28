import os
import re
import shutil
from queue import Queue
from datetime import datetime
import operator
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, QThread, QAbstractTableModel, Qt, QVariant,\
        pyqtSignal, QPoint,\
        pyqtSlot, QMimeData, QByteArray, QEvent, QRect, QSize
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon, QFont, QFontMetrics,\
        QCursor, QRegExpValidator, QPainter
from PyQt5.QtWidgets import QStyle, QStyleOptionSlider, QDialogButtonBox
import resources
from lib import sqlitedb
from .tools import getHLine, getXExpandYMinSizePolicy, getXMinYExpandSizePolicy,\
    parseAuthors, getXExpandYExpandSizePolicy, getMinSizePolicy, fuzzyMatch
import networkx as nx


LOGGER=logging.getLogger('default_logger')




class TreeWidgetDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None):
        QtWidgets.QItemDelegate.__init__(self, parent=parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        reg=QtCore.QRegExp('[A-z0-9\[\]_-\s]+')
        vd=QRegExpValidator(reg)
        editor.setValidator(vd)
        return editor


    '''
    def eventFilter(self, editor, event):
        # NOTE: possibly move the name conflict check inside
        print('# <eventFilter>: editor:', editor, 'event', event)


        if event.type()==QEvent.KeyPress:
            if event.key()==Qt.Key_Enter or event.key()==Qt.Key_Return:
                print('# <eventFilter>: Keypress', event.key())

                if editor.text()=='aaa':
                    return False
                self.commitData.emit(editor)
                self.closeEditor.emit(editor,0)
                return True
            else:
                return False
        else:
            return False
    '''





class MyTreeWidget(QtWidgets.QTreeWidget):

    folder_move_signal=pyqtSignal(str,str)
    folder_del_signal=pyqtSignal(QtWidgets.QTreeWidgetItem,\
            QtWidgets.QTreeWidgetItem,bool)
    add_doc_to_folder_signal=pyqtSignal(int,str)

    def __init__(self,parent=None):
        self.parent=parent
        super(MyTreeWidget,self).__init__(parent=parent)

        self._trashed_folder_ids=[]
        self._trashed_doc_ids=[]
        self.setDropIndicatorShown(True)

    def commitData(self,widget):
        print('# <commitData>: widget',widget)
        self.itemChanged.connect(self.parent.addNewFolderToDict, Qt.QueuedConnection)
        super(MyTreeWidget,self).commitData(widget)
        recs=self.receivers(self.itemChanged)
        print('# <commitData>: recs',recs)
        if recs>0:
            self.itemChanged.disconnect()
        return

    def selectedIndexes(self):
        return self.selectionModel().selectedIndexes()

    def startDrag(self,actions):

        move_item=self.selectedItems()[0]

        print('# <startDrag>: move_item.data(0,0)=%s, move_item.data(1,0)=%s'\
                %(move_item.data(0,0), move_item.data(1,0)))
        LOGGER.info('move_item.data(0,0)=%s, move_item.data(1,0)=%s'\
                %(move_item.data(0,0), move_item.data(1,0)))

        self._move_item=move_item
        # TODO: abort if item is system folders?

        super(MyTreeWidget,self).startDrag(actions)

    def dragEnterEvent(self,event):

        mime_data=event.mimeData()

        print('# <dragEnterEvent>: event.mimeData()=',
                'formats', mime_data.formats())

        if mime_data.hasFormat('doc_table_item'):
            event.setDropAction(Qt.CopyAction)
            event.accept()
        elif mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

        return

    def dragMoveEvent(self,event):

        mime_data=event.mimeData()

        if mime_data.hasFormat('doc_table_item'):
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        elif mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):

            # deny droping to self
            pos=event.pos()
            newparent=self.itemAt(pos)
            if newparent==self._move_item:
                event.ignore()
                return

            event.setDropAction(Qt.MoveAction)
            event.acceptProposedAction()

            # need this to make dropIndicatorPosition work
            super(MyTreeWidget,self).dragMoveEvent(event)
        else:
            event.ignore()

        return


    def dropEvent(self,event):

        mime_data=event.mimeData()

        if mime_data.hasFormat('doc_table_item'):
            # decode byte to str
            dropped_docid=mime_data.data('doc_table_item').data().decode('ascii')
            dropped_docid=int(dropped_docid)

            pos=event.pos()
            newparent=self.itemAt(pos)

            parentidx=self.indexFromItem(newparent)
            #indicatorpos=self.dropIndicatorPosition()

            print('# <dropEvent>: doc id=',dropped_docid,'parentid=',
                    newparent.data(1,0))

            self.add_doc_to_folder_signal.emit(dropped_docid, newparent.data(1,0))

            return

        elif mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):
            event.setDropAction(Qt.MoveAction)

            if self._move_item.data(1,0) in ['-1','-2','-3']:
                return

            pos=event.pos()
            newparent=self.itemAt(pos)

            parentidx=self.indexFromItem(newparent)
            indicatorpos=self.dropIndicatorPosition()

            print('# <dropEvent>: parentidx.row()=%s. newparent=.data(0,0=%s.'\
                    %(parentidx.row(), newparent.data(0,0)))
            LOGGER.info('parentidx.row()=%s. newparent=.data(0,0=%s.'\
                    %(parentidx.row(), newparent.data(0,0)))

            print('# <dropEvent>: dropIndicatorPosition=%s' %indicatorpos)
            LOGGER.info('dropIndicatorPosition=%s' %indicatorpos)

            # on item
            if indicatorpos==0:

                # get children
                children=[newparent.child(ii) for ii in range(newparent.childCount())]
                children_names=[ii.data(0,0) for ii in children]

                print('# <dropEvent>: Got children=%s' %children_names)
                LOGGER.info('Got children=%s' %children_names)

                if newparent.data(0,0) in ['All', 'Needs Review']:
                    event.ignore()
                    return

                # move to trash
                elif newparent.data(1,0) in ['-3']+self._trashed_folder_ids:

                    print('# <dropEvent>: Trashing folder.')
                    LOGGER.info('Trashing folder.')

                    self.folder_del_signal.emit(self._move_item,newparent,True)
                    return 

                # change folder parent
                if self._move_item.data(0,0) in children_names:

                    print('# <dropEvent>: Name conflict.')
                    LOGGER.info('Name conflict.')

                    event.ignore()
                    msg=QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setWindowTitle('Name conflict')
                    msg.setText('Move cancelled due to name conflict.')
                    msg.setInformativeText('Folder name\n\t%s\nconflicts with another folder in the target folder.\nPlease rename before moving.' %self._move_item.data(0,0))
                    msg.exec_()
                    return
                else:
                    event.setDropAction(Qt.MoveAction)
                    self.folder_move_signal.emit(self._move_item.data(1,0),\
                            newparent.data(1,0))
                    super(MyTreeWidget,self).dropEvent(event)
                    return

            # above item
            elif indicatorpos==1:
                if parentidx.row()<=3:
                    event.ignore()
                    return

            # below item
            elif indicatorpos==2:
                if parentidx.row()<=2:
                    event.ignore()
                    return

            super(MyTreeWidget,self).dropEvent(event)




class TableModel(QAbstractTableModel):
    def __init__(self, parent, datain, headerdata, settings):
        QAbstractTableModel.__init__(self, parent)

        self.ncol=len(headerdata)
        if datain is None:
            self.arraydata=[None]*self.ncol
        else:
            self.arraydata=datain
        self.headerdata=headerdata
        self.settings=settings

        self.icon_section={
                'has_file': QIcon(':/file_icon.png')
                }
        self.check_section={
                'favourite': QPixmap(':/bf.png'),
                'read': QPixmap(':/clap.png')
                }
        self.icon_sec_indices=[self.headerdata.index(kk) for kk
                in self.icon_section.keys()]
        self.check_sec_indices=[self.headerdata.index(kk) for kk
                in self.check_section.keys()]

    def rowCount(self,p):
        return len(self.arraydata)

    def columnCount(self,p):
        return self.ncol

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        if role == Qt.BackgroundRole:
            if index.row()%2==0:
                return QBrush(QColor(230,230,249))
        if role == Qt.FontRole:
            font=self.settings.value('display/fonts/doc_table',QFont)
            if self.arraydata[index.row()][9] in [None, 'false']:
                font.setBold(True)
            else:
                font.setBold(False)
            return font
        if role==Qt.DisplayRole:
            if index.column() in self.icon_sec_indices:
                return
            elif index.column()==self.headerdata.index('added'):
                added=self.arraydata[index.row()][index.column()]
                if added:
                    added=int(added[:10])
                    added=datetime.fromtimestamp(added)
                    if added.year==datetime.today().year:
                        added=added.strftime('%b-%d')
                    else:
                        added=added.strftime('%b-%d-%y')
                    return QVariant(added)
                else:
                    return
            else:
                return QVariant(self.arraydata[index.row()][index.column()])
        if role==Qt.EditRole:
            return QVariant(self.arraydata[index.row()][index.column()])

        #if role==Qt.TextAlignmentRole:
            #return Qt.AlignCenter
        if index.column() in self.check_sec_indices and role==Qt.CheckStateRole:
            if self.arraydata[index.row()][index.column()].isChecked():
                return Qt.Checked
            else:
                return Qt.Unchecked
        if index.column() in self.icon_sec_indices and role==Qt.DecorationRole:
            if self.arraydata[index.row()][index.column()]:
                return self.icon_section['has_file']
            else:
                return None

        if role != Qt.DisplayRole:
            return QVariant()

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if index.column() in self.check_sec_indices and role==Qt.CheckStateRole:
            if value == Qt.Checked:
                self.arraydata[index.row()][index.column()].setChecked(True)
            else:
                self.arraydata[index.row()][index.column()].setChecked(False)

        self.dataChanged.emit(index,index)
        return True

    def flags(self, index):
        if index.column() in self.check_sec_indices:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable\
                    | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |\
                    QtCore.Qt.ItemIsDragEnabled


    def headerData(self, col, orientation, role):

        if col in self.icon_sec_indices:
            label=self.headerdata[col]
            if orientation==Qt.Horizontal and role==Qt.DecorationRole:
                return self.icon_section[label]
        elif col in self.check_sec_indices:
            label=self.headerdata[col]
            if orientation==Qt.Horizontal and role==Qt.DecorationRole:
                return self.check_section[label]
        else:
            if orientation==Qt.Horizontal and role==Qt.DisplayRole:
                return self.headerdata[col]
        return None

    def sort(self,col,order):
        self.layoutAboutToBeChanged.emit()

        #NOTE that python3 doesn't support mixed type sorting (e.g. 1<None,
        # 'a' > 2. So convert everything to str.
        self.arraydata=sorted(self.arraydata,key=lambda x: \
                str(operator.itemgetter(col)(x)) or '')
        if order==Qt.DescendingOrder:
            self.arraydata.reverse()
        self.layoutChanged.emit()

    def mimeTypes(self):
        return ['doc_table_item',]

    def mimeData(self,indices):

        print('# <mimeData>: headerdata=', self.headerdata)
        print('# <mimeData>: indices=', indices)

        for idii in indices:
            print('# <mimeData>: idii',idii.row(), idii.column(), idii.data())

        ids=[ii for ii in indices if ii.isValid()]
        print('# <mimeData>: ids=', ids)
        rowids=[ii.row() for ii in ids]
        rowids=list(set(rowids))
        print('# <mimeData>: rowids=', rowids)
        encode_data=[str(self.arraydata[ii][0]) for ii in rowids]
        encode_data=', '.join(encode_data)
        print('# <mimeData>: encode_data', encode_data,type(encode_data))
        encode_data_array=QByteArray()
        encode_data_array.append(encode_data)
        print('# <mimeData>: encode_data_array', encode_data_array)

        mimedata=QMimeData()
        mimedata.setData('doc_table_item',encode_data_array)

        return mimedata


class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)

        self.colSizes={'docid':0, 'favourite': 20, 'read': 20, 'has_file': 20,
            'author': 200, 'title': 500, 'journal':100,'year':50,'added':50,
            'confirmed':0}

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.sectionResized.connect(self.myresize)
        self.setStretchLastSection(False)
        self.setSectionsMovable(True)

    def initresizeSections(self):
        model=self.model()
        if model is None:
            return
        self.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        headers=model.headerdata

        for ii in range(self.count()):
            lii=headers[ii]
            sii=self.colSizes[lii]
            if lii in self.colSizes:
                self.setSectionResizeMode(ii, QtWidgets.QHeaderView.Fixed)
                self.resizeSection(ii,sii)
            else:
                self.setSectionResizeMode(ii, QtWidgets.QHeaderView.Stretch)
                wnow=self.sectionSize(ii)
                self.resizeSection(ii,wnow)
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Interactive)



    def myresize(self, *args):

        model=self.model()
        if model is None:
            return
        ws=[]
        for c in range(self.count()):
            wii=self.sectionSize(c)
            ws.append(wii)

        if args[0]>0 or args[0]<self.count():
            for ii in range(args[0],self.count()):
                lii=model.headerdata[ii]
                if lii in ['favourite','read','has_file']:
                    continue
                if ii==args[0]:
                    continue
                if ii==self.count()-1:
                    self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Stretch)
                else:
                    pass


    def resizeEvent(self, event):

        super(QtWidgets.QHeaderView, self).resizeEvent(event)

        model=self.model()
        if model is None:
            return

        ws=[]
        perc=[]
        total_w=self.length() # width of the table
        total_w2=self.size().width()   # new available space after resizing
        for c in range(self.count()):
            wii=self.sectionSize(c)
            ws.append(wii)
            perc.append(float(wii)/total_w)

        headers=model.headerdata

        for ii in range(self.count()):
            lii=headers[ii]
            if lii in ['favourite','read','has_file']:
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Fixed)
                continue
            elif lii=='year':
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Stretch)
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Interactive)
            else:
                wnow=int(perc[ii]*total_w2)
                self.resizeSection(ii,wnow)
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Interactive)

        return

    def columnFromLabel(self, label):
        headers=self.model().headerdata
        if label in headers:
            return headers.index(label)
        return -1

class AdjustableTextEdit(QtWidgets.QTextEdit):

    edited_signal=pyqtSignal(str)
    def __init__(self,field,parent=None):
        super(AdjustableTextEdit,self).__init__(parent)

        self.field=field # field name, e.g. title, year, tags_l ...
        self.tooltip_label=QtWidgets.QLabel()
        self.tooltip_label.setWindowFlags(Qt.SplashScreen)
        self.tooltip_label.setMargin(3)
        self.tooltip_label.setStyleSheet('''
                background-color: rgb(235,225,120)
                ''')
        self.tooltip_text=''
        self.label_enabled=False

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self.resizeTextEdit)
        self.document().documentLayout().documentSizeChanged.connect(
                self.resizeTextEdit)
        self.setTabChangesFocus(True)

    def focusInEvent(self,event):
        #self.setToolTip('tooltip')
        #print('focusInEvent: QCursor.pos()', QCursor.pos())
        #QtWidgets.QToolTip.showText(QCursor.pos(), 'tooltip')
        if self.label_enabled and self.tooltip_text:
            self.tooltip_label.move(self.mapToGlobal(
                QPoint(0, self.height()-120)))
            self.tooltip_label.setText(self.tooltip_text)
            self.tooltip_label.show()

        super(AdjustableTextEdit,self).focusInEvent(event)

    def focusOutEvent(self,event):
        if self.document().isModified():
            self.edited_signal.emit(self.field)
        if self.label_enabled:
            self.tooltip_label.close()
        super(AdjustableTextEdit,self).focusOutEvent(event)

    def setText(self,text):
        super(AdjustableTextEdit,self).setText(text)
        self.document().setModified(False)

    def resizeTextEdit(self):
        '''
        self.setAttribute(103)
        self.show()
        docheight=self.document().size().height()+3
        print('docheight',docheight)
        self.setFixedHeight(docheight)
        '''

        '''
        f=self.currentFont()
        fm=QFontMetrics(f)
        text=self.toPlainText()
        print('fm',fm)
        print('text',text)
        textsize=fm.size(0,text)
        textw=textsize.width()+1
        texth=textsize.height()+4
        self.setMinimumHeight(texth)
        '''
        '''
        if self.getNumberOfLines()<self.fold_above_nl:
            self.fold_button.setVisible(False)
            self.unfoldText()
        else:
            self.fold_button.setVisible(True)
            if self.is_fold:
                self.foldText()
            else:
                self.unfoldText()

        '''
        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)


        return


class AdjustableTextEditWithFold(AdjustableTextEdit):

    fold_change_signal=pyqtSignal(str,bool)
    def __init__(self,field,parent=None):
        super(AdjustableTextEditWithFold,self).__init__(parent)

        self.field=field
        self.is_fold=False
        self.fold_above_nl=3

        self.fold_button=QtWidgets.QPushButton()
        self.fold_button.setText('-')
        font_height=self.fontMetrics().height()
        self.fold_button.setFixedWidth(int(font_height))
        self.fold_button.setFixedHeight(int(font_height))
        self.fold_button.clicked.connect(self.toggleFold)
        self.fold_button.setStyleSheet('''
        QPushButton {
            border: 1px solid rgb(190,190,190);
            background-color: rgb(190,190,190);
            border-radius: %dpx;
            font: bold %dpx;
            color: white;
            text-align: center;
            padding-bottom: 2px;
            }

        QPushButton:pressed {
            border-style: inset;
            } 
        ''' %(int(font_height/2), max(1,font_height-2))
        )

    def getNumberOfLines(self):
        fm=self.fontMetrics()
        doc=self.document()
        docheight=doc.size().height()
        margin=doc.documentMargin()
        nlines=(docheight-2*margin)/fm.height()

        return nlines

    def resizeTextEdit(self):
        if self.getNumberOfLines()<self.fold_above_nl:
            self.fold_button.setVisible(False)
            self.unfoldText()
        else:
            self.fold_button.setVisible(True)
            if self.is_fold:
                self.foldText()
            else:
                self.unfoldText()

        return

    def toggleFold(self):
        self.unfoldText() if self.is_fold else self.foldText()
        self.fold_change_signal.emit(self.label,self.is_fold)
        return

    def foldText(self):
        nlines=self.getNumberOfLines()
        if nlines>=self.fold_above_nl:
            fontheight=self.fontMetrics().height()
            margin=self.document().documentMargin()
            self.setMinimumHeight(fontheight+2*margin)
            self.setMaximumHeight(fontheight+2*margin)
            self.is_fold=True
            self.fold_button.setText('+')
            #self.fold_button.setIcon(QIcon.fromTheme('list-add'))

        return

    def unfoldText(self):
        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)
        self.is_fold=False
        self.fold_button.setText('\u2212')
        return


class FileLineEdit(QtWidgets.QLineEdit):
    def __init__(self,parent=None):
        super(FileLineEdit,self).__init__(parent)

        self.fm=QFontMetrics(self.font())

    def setText(self,text,elide=True):
        self.full_text=text
        self.short_text=os.path.split(self.full_text)[1]
        #self.short_text=text

        '''
        if elide:
            super(FileLineEdit,self).setText(
                self.fm.elidedText(self.short_text,Qt.ElideRight,self.width()))
        else:
            super(FileLineEdit,self).setText(self.short_text)
        '''
        #super(FileLineEdit,self).setText(text)
        super(FileLineEdit,self).setText(
             self.fm.elidedText(self.short_text,Qt.ElideRight,self.width()))

        return

    def text(self):
        #return self.full_text
        return self.fm.elidedText(self.short_text,Qt.ElideRight,self.width())


    def resizeEvent(self,event):
        super(QtWidgets.QLineEdit, self).resizeEvent(event)
        if hasattr(self,'full_text'):
            self.setText(self.full_text,elide=True)


class MetaTabScroll(QtWidgets.QScrollArea):

    meta_edited=pyqtSignal(list) # send field names
    def __init__(self,settings,parent=None):
        super(MetaTabScroll,self).__init__(parent)

        self.settings=settings
        self.parent=parent

        #self.font_dict={
            #'meta_title': self.settings.value('display/fonts/meta_title',QFont),
            #'meta_authors': self.settings.value('display/fonts/meta_authors',QFont),
            #'meta_keywords': self.settings.value('display/fonts/meta_keywords',QFont)
            #}

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.label_font=QFont('Serif',12,QFont.Bold)

        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        self.setWidgetResizable(True)
        self.setWidget(frame)
        self.fields_dict={}  # key: field name, value: textedit or lineedit
        self.fold_dict={} # key: field name, value: is textedit folded

        #-------------------Add widgets-------------------
        self.v_layout=QtWidgets.QVBoxLayout()

        #--------------------Add title--------------------
        title_te=AdjustableTextEdit('title')
        title_te.setFrameStyle(QtWidgets.QFrame.NoFrame)
        title_te.setFont(self.settings.value('display/fonts/meta_title', QFont))
        self.fields_dict['title']=title_te
        self.v_layout.addWidget(title_te)

        self.v_layout.addWidget(getHLine(self))

        #-------------------Add authors-------------------
        self.createMultiLineField('Authors','authors_l','meta_authors')

        #-----Add journal, year, volume, issue, pages-----
        grid_layout=QtWidgets.QGridLayout()

        for fii in ['publication','year','volume','issue','pages',
                'citationkey']:
            self.createOneLineField(fii,fii,'meta_keywords',grid_layout)

        self.v_layout.addLayout(grid_layout)

        #---------------------Add tags---------------------
        self.createMultiLineField('Tags','tags_l','meta_keywords')

        #-------------------Add abstract-------------------
        self.createMultiLineField('Abstract','abstract','meta_keywords')

        #-------------------Add keywords-------------------
        self.createMultiLineField('Keywords','keywords_l',
                'meta_keywords')

        #-----------------Add catalog ids-----------------
        self.v_layout.addWidget(self.createLabel('Catalog IDs'))

        grid_layout=QtWidgets.QGridLayout()

        for fii in ['arxivId','doi','issn','pmid']:
            self.createOneLineField(fii,fii,'meta_keywords',grid_layout)

        self.v_layout.addLayout(grid_layout)

        #--------------------Add files--------------------
        self.fields_dict['files_l']=[]
        self.v_layout.addWidget(self.createLabel('Files'))
        self.file_insert_idx=self.v_layout.count()

        print('# <MetaTabScroll>: NO of widgets in v_layout=%d' %self.v_layout.count())
        LOGGER.info('NO of widgets in v_layout=%d' %self.v_layout.count())

        #---------------Add add file button---------------
        add_file_button=QtWidgets.QPushButton()
        add_file_button.setText('Add File...')
        add_file_button.setSizePolicy(getXExpandYMinSizePolicy())
        add_file_button.setStyleSheet('''
        QPushButton {
            background-color: rgb(220,220,220);
            border-radius: 2px;
            }

        QPushButton:pressed {
            border-style: inset;
            } 
        ''')
        add_file_button.clicked.connect(self.addFileButtonClicked)
        self.v_layout.addWidget(add_file_button)

        self.v_layout.addStretch()
        frame.setLayout(self.v_layout)

        #-------------Connect focus out events-------------
        for kk,vv in self.fields_dict.items():
            if isinstance(vv,(list,tuple)):
                for vii in vv:
                    vii.edited_signal.connect(self.fieldEdited)
            else:
                vv.edited_signal.connect(self.fieldEdited)

        #------------------Set tab orders------------------
        field_keys=['title', 'authors_l', 'publication', 'year', 'volume',
                'issue', 'pages', 'citationkey', 'tags_l', 'abstract',
                'keywords_l', 'arxivId', 'doi', 'issn', 'pmid']
        for ii,kk in enumerate(field_keys[:-1]):
            w1=self.fields_dict[kk]
            w2=self.fields_dict[field_keys[ii+1]]
            self.setTabOrder(w1,w2)


    @pyqtSlot(str)
    def fieldEdited(self,field):

        print('# <fieldEdited>: Changed field=%s' %field)
        LOGGER.info('Changed field=%s' %field)

        print(self._meta_dict)
        self.meta_edited.emit([field,])

    def createLabel(self,label):
        qlabel=QtWidgets.QLabel(label)
        qlabel.setStyleSheet(self.label_color)
        qlabel.setFont(self.label_font)
        return qlabel


    def createOneLineField(self,label,key,font_name,grid_layout):
        te=AdjustableTextEdit(key)
        qlabel=QtWidgets.QLabel(label)
        qlabel.setStyleSheet(self.label_color)

        #if font_name in self.font_dict:
        te.setFont(self.settings.value('display/fonts/%s' %font_name, QFont))

        rnow=grid_layout.rowCount()
        grid_layout.addWidget(qlabel,rnow,0)
        grid_layout.addWidget(te,rnow,1)
        self.fields_dict[key]=te

        return

    def createMultiLineField(self,label,key,font_name):
        te=AdjustableTextEditWithFold(key)
        te.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.fold_dict[key]=te.is_fold
        te.fold_change_signal.connect(self.foldChanged)

        #if font_name in self.font_dict:
        te.setFont(self.settings.value('display/fonts/%s' %font_name, QFont))

        if key=='authors_l':
            te.label_enabled=True
            te.tooltip_text='lastname, firstname\nlastname, firstname\n...'
        elif key=='tags_l':
            te.label_enabled=True
            te.tooltip_text='tag1; tag2; tag3 ...'
        elif key=='keywords_l':
            te.label_enabled=True
            te.tooltip_text='keyword1; keyword2; keyword3 ...'
        self.fields_dict[key]=te

        h_layout=QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.createLabel(label))
        h_layout.addWidget(te.fold_button)

        self.v_layout.addLayout(h_layout)
        self.v_layout.addWidget(te)

        return te

    def createFileField(self,text=None,font_name='meta_keywords'):

        h_layout=QtWidgets.QHBoxLayout()

        le=FileLineEdit()
        le.setReadOnly(True)

        #if font_name in self.font_dict:
            #le.setFont(self.font_dict[font_name])
        le.setFont(self.settings.value('display/fonts/%s' %font_name, QFont))

        if text is not None:
            le.setText(text)

        if le not in self.fields_dict['files_l']:
            self.fields_dict['files_l'].append(le)
        #self.v_layout.addWidget(le)

        # create a del file button
        button=QtWidgets.QPushButton()
        font_height=le.fm.height()
        button.setFixedWidth(int(font_height))
        button.setFixedHeight(int(font_height))
        button.setText('\u2715')
        button.setStyleSheet('''
        QPushButton {
            border: 1px solid rgb(190,190,190);
            background-color: rgb(190,190,190);
            border-radius: %dpx;
            font: bold %dpx;
            color: white;
            text-align: center;
            padding-bottom: 2px;
            }

        QPushButton:pressed {
            border-style: inset;
            } 
        ''' %(int(font_height/2), max(1,font_height-2))
        )
        button.clicked.connect(lambda: self.delFileButtonClicked(
            self.fields_dict['files_l'].index(le)))

        le.del_button=button
        h_layout.addWidget(le)
        h_layout.addWidget(button)

        print('# <createFileField>: Insert at %s' %self.file_insert_idx)
        LOGGER.info('Insert at %s' %self)

        self.v_layout.insertLayout(self.file_insert_idx,h_layout)
        self.file_insert_idx+=1

        return

    def delFileButtonClicked(self, idx=None):

        self.delFileField(idx)
        self.fieldEdited('files_l')

        return


    def delFileField(self,idx=None):
        def delFile(le):
            self.v_layout.removeWidget(le.del_button)
            self.v_layout.removeWidget(le)
            le.deleteLater()
            le.del_button.deleteLater()
            self.fields_dict['files_l'].remove(le)
            self.file_insert_idx-=1

        if idx is None:
            #for ii in range(len(self.fields_dict['files'])):
            for leii in self.fields_dict['files_l']:

                print('# <delFile>: Del %s. Current file_insert_idx=%s'\
                        %(leii, self.file_insert_idx))
                LOGGER.info('Del %s. Current file_insert_idx=%s'\
                        %(leii, self.file_insert_idx))

                delFile(leii)
        else:
            if idx in range(len(self.fields_dict['files_l'])):
                leii=self.fields_dict['files_l'][idx]
                delFile(leii)


        return


    def addFileButtonClicked(self):

        if hasattr(self.parent, '_current_doc') and self.parent._current_doc is None:
            return

        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a PDF file',
         '',"PDF files (*.pdf);; All files (*)")[0]

        if fname:

            print('# <addFileButtonClicked>: New file=%s' %fname)
            LOGGER.info('New file=%s' %fname)

            self.createFileField(fname)
            self.fieldEdited('files_l')

        return

    def foldChanged(self,field,isfold):
        self.fold_dict[field]=isfold

        print('# <foldChanged>: Field=%s. isfold=%s' %(field, isfold))
        LOGGER.info('Field=%s. isfold=%s' %(field, isfold))

        return



    @property
    def _meta_dict(self):

        def parseToList(text):
            result=[]
            textlist=text.replace('\n',';').strip(';').split(';')
            for tii in textlist:
                tii=tii.strip()
                if len(tii)>0:
                    result.append(tii)
            return result

        #result_dict={}
        result_dict=sqlitedb.DocMeta()
        for kk,vv in self.fields_dict.items():
            # field should be a list
            if kk.endswith('_l'):
                if isinstance(vv,(tuple,list)):
                    values=[]
                    for vii in vv:
                        if isinstance(vii,QtWidgets.QLineEdit):
                            if kk=='files_l':
                                textii=vii.full_text
                            else:
                                textii=vii.text().strip()
                        elif isinstance(vii,QtWidgets.QTextEdit):
                            textii=vii.toPlaintext().strip()
                        if textii:
                            values.append(textii)
                    result_dict[kk]=values
                elif isinstance(vv,QtWidgets.QTextEdit):
                    if kk=='authors_l':
                        names=parseToList(vv.toPlainText())
                        firsts,lasts,authors=parseAuthors(names)
                        result_dict['firstNames_l']=firsts
                        result_dict['lastName_l']=lasts
                        #result_dict['authors_l']=authors
                    else:
                        result_dict[kk]=parseToList(vv.toPlainText())
                elif isinstance(vv,QtWidgets.QLineEdit):
                    result_dict[kk]=parseToList(vv.toText())
            # field should be a str
            else:
                if isinstance(vv,QtWidgets.QLineEdit):
                    values=vv.toText().strip()
                    result_dict[kk]=values or None
                elif isinstance(vv,QtWidgets.QTextEdit):
                    values=vv.toPlainText().strip()
                    result_dict[kk]=values or None


        return result_dict




class MetaDataEntryDialog(QtWidgets.QDialog):

    def __init__(self,settings,parent=None):
        super(MetaDataEntryDialog,self).__init__(parent)

        self.resize(500,700)
        self.setWindowTitle('Add New Entry')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()

        self.scroll=MetaTabScroll(settings,self)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.scroll.meta_edited.connect(self.checkOkButton)

        v_layout.addWidget(self.scroll)
        v_layout.addWidget(self.buttons)

        self.setLayout(v_layout)

        self.initialized=False
        self.empty_dict=sqlitedb.DocMeta()
        self.empty_dict.pop('added')
        self.empty_dict.pop('files_l')

    def checkOkButton(self):
        def checkDictChanged(d1,d2):
            for kk in d1.keys():
                if d1[kk]!=d2[kk]:
                    return True
            return False

        if checkDictChanged(self.empty_dict,self.scroll._meta_dict):
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def showEvent(self,e):
        if not self.initialized:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            self.initialized=True

        self.scroll.fields_dict['title'].setFocus()
        super(MetaDataEntryDialog,self).showEvent(e)
        return

    def exec_(self):
        ret=super(MetaDataEntryDialog,self).exec_()
        return ret, self.scroll._meta_dict


class NoteTextEdit(QtWidgets.QTextEdit):

    note_edited_signal=pyqtSignal()
    def __init__(self,settings,parent=None):

        self.settings=settings

        super(NoteTextEdit,self).__init__(parent=parent)

        self.setFont(self.settings.value('display/fonts/notes',QFont))
        self.setSizePolicy(getXExpandYExpandSizePolicy())


    def focusOutEvent(self,event):
        if self.document().isModified():
            self.note_edited_signal.emit()
        super(NoteTextEdit,self).focusOutEvent(event)



class PreferenceDialog(QtWidgets.QDialog):

    def __init__(self,settings,parent=None):
        super(PreferenceDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.font_dict=OrderedDict([
            ('Meta Tab -> Title'      , 'display/fonts/meta_title')    ,
            ('Meta Tab -> Authors'    , 'display/fonts/meta_authors')  ,
            ('Meta Tab -> Keywords'   , 'display/fonts/meta_keywords') ,
            ('Document Table Entries' , 'display/fonts/doc_table')     ,
            ('Bibtex Tab'             , 'display/fonts/bibtex')        ,
            ('Notes Tab'              , 'display/fonts/notes')         ,
            ('Scratch Pad Tab'        , 'display/fonts/scratch_pad')
            ])

        self.new_values={} # store changes before applying

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(800,600)
        self.setWindowTitle('Preferences')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Change Preference Settings')
        title_label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(title_label)

        v_layout.addLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        #self.list.setSizePolicy(getXMinYExpandSizePolicy())
        self.cate_list.setMaximumWidth(150)
        h_layout.addWidget(self.cate_list)

        #self.cate_list.setStyleSheet('''
            #QListWidget::item { border: 0px solid rgb(235,235,240);
            #font: 14px;
            #background-color: rgb(205,205,245);
            #color: rgb(100,10,13) };
            #background-color: rgb(230,234,235);
            #''')

        self.cate_list.addItems(['Citation Style', 'Display', 'Export',
            'Savings', 'Miscellaneous'])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply |\
                    QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(lambda: (self.applyChanges(), self.accept()))
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Apply).clicked.connect(
                self.applyChanges)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)

    @pyqtSlot()
    def applyChanges(self):

        print('# <applyChanges>: Apply settings changes')
        print('# <applyChanges>: Changes:',self.new_values)

        for kk,vv in self.new_values.items():
            self.settings.setValue(kk,vv)

        #------------------Set new timer------------------
        if 'saving/auto_save_min' in self.new_values:
            self.parent.main_frame.auto_save_timer.setInterval(
                    self.settings.value('saving/auto_save_min',1,int)*60*1000)

        self.new_values={}

        #---------------Create output folder---------------
        storage_folder=self.settings.value('saving/storage_folder')
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)
            print('# <applyChanges>: Create new storage folder %s' %storage_folder)
            LOGGER.info('Create new storage folder %s' %storage_folder)



        # TODO: apply change to database and meta_dict
        # need to call saveFoldersToDatabase() with new folder, and
        # metaDictToDatabase() for all docids. Then move database file over.
        # may need to require a reboot if so.

        #sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                #self.settings.value('saving/storage_folder'))

        return



    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):

        item_text=item.text()
        print('# <cateSelected>: item.text()=%s' %item_text)

        if self.content_vlayout.count()>1:
            self.content_vlayout.removeWidget(self.content_frame)

        if item_text=='Display':
            self.content_frame=self.loadDisplayOptions()
        elif item_text=='Export':
            self.content_frame=self.loadExportOptions()
        elif item_text=='Citation Style':
            self.content_frame=self.loadCitationStyleOptions()
        elif item_text=='Savings':
            self.content_frame=self.loadSavingsOptions()
        elif item_text=='Miscellaneous':
            self.content_frame=self.loadMiscellaneousOptions()

        self.content_vlayout.insertWidget(0,self.content_frame)


    def createFrame(self,title):

        frame=QtWidgets.QWidget(self)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        va=QtWidgets.QVBoxLayout()
        frame.setLayout(va)
        va.setSpacing(int(va.spacing()*2))

        label=QtWidgets.QLabel(title)
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        va.addWidget(label)
        #va.addWidget(getHLine(self))

        return scroll, va


    def createOmitKeyGroup(self):

        grid=QtWidgets.QGridLayout()

        self.groupbox=QtWidgets.QGroupBox('Omit these fields in the exported bib entry.')
        self.groupbox.setCheckable(True)

        omittable_keys=[
            'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
            'lastName_l', 'pend_delete', 'folders_l', 'type', 'id',
            'abstract', 'advisor', 'month', 'language', 'confirmed',
            'deletionPending', 'note', 'publicLawNumber', 'sections',
            'reviewedArticle', 'userType', 'shortTitle', 'sourceType',
            'code', 'codeNumber', 'codeSection', 'codeVolume', 'citationKey',
            'day', 'dateAccessed', 'internationalAuthor', 'internationalUserType',
            'internationalTitle', 'internationalNumber', 'genre', 'lastUpdate',
            'legalStatus', 'length', 'medium'
            ]
        omittable_keys.sort()

        omit_keys=self.settings.value('export/bib/omit_fields', [], str)
        # likely something wrong with qt. When list is set empty by
        # settings.setValue('key',[]), on the NEXT load of the program,
        # settings.value('export/bib/omit_fields', [], str) gives ''
        if isinstance(omit_keys,str) and omit_keys=='':
            omit_keys=[]

        for ii,keyii in enumerate(omittable_keys):
            checkboxii=QtWidgets.QCheckBox(keyii,self.groupbox)
            if keyii in omit_keys:
                checkboxii.setChecked(True)
            checkboxii.stateChanged.connect(self.omitKeyChanged)
            grid.addWidget(checkboxii,int(ii/3),ii%3)

        self.groupbox.toggled.connect(lambda on: self.omitKeysGroupChanged(on,
            self.groupbox))

        self.groupbox.setLayout(grid)


        return self.groupbox


    def loadDisplayOptions(self):

        scroll,va=self.createFrame('Select Fonts')

        ha=QtWidgets.QHBoxLayout()
        #ha.addStretch()
        label=QtWidgets.QLabel('NOTE some changes requires re-booting.')
        ha.addWidget(label,0,Qt.AlignTop)

        text_list=QtWidgets.QListWidget()
        text_list.setSizePolicy(getXMinYExpandSizePolicy())
        text_list.addItems(self.font_dict.keys())

        ha.addWidget(text_list)

        text_list.itemDoubleClicked.connect(self.chooseFont)
        va.addLayout(ha)

        return scroll


    @pyqtSlot(QtWidgets.QListWidgetItem)
    def chooseFont(self,item):
        item_text=item.text()

        print('# <chooseFont>: item.text()=%s' %item_text)

        font_setting_name=self.font_dict[item_text]
        default=self.settings.value(font_setting_name, QFont)

        new_font,isok=QtWidgets.QFontDialog.getFont(default,
                caption='Choose Font for %s' %item_text)

        print('# <loadDisplayOptions>: new_font', new_font,'isok',isok)
        if isok:
            self.new_values[font_setting_name]=new_font
            print('# <chooseFont>: Font after change:', new_font)

        return



    def loadSavingsOptions(self):

        scroll, va=self.createFrame('Choose Storage Folder')

        #-------------Choose storage folder section-------------
        label2=QtWidgets.QLabel('''
        Select folder to save document files. <br/>
        &nbsp;&nbsp; Document (e.g. PDFs) will be copied to the
        <span style="font:bold;">
        "Collections" </span> <br/> &nbsp;&nbsp; sub-folder of the chosen folder.
        ''')
        label2.setTextFormat(Qt.RichText)
        va.addWidget(label2)

        ha=QtWidgets.QHBoxLayout()
        ha.addStretch()

        storage_folder=self.settings.value('saving/storage_folder')
        le=QtWidgets.QLineEdit()
        le.setText(storage_folder)

        va.addWidget(le)
        va.addLayout(ha)
        button=QtWidgets.QPushButton(self)
        button.setText('Choose')

        button.clicked.connect(self.chooseSaveFolder)
        ha.addWidget(button)
        va.addWidget(getHLine())

        #---------------Rename file section---------------
        checkbox=QtWidgets.QCheckBox('Rename Files')
        checked=self.settings.value('saving/rename_files',type=int)
        print('# <loadSavingsOptions>: Got rename files=',checked)
        checkbox.setChecked(checked)

        le=QtWidgets.QLineEdit(self)
        le.setReadOnly(True)
        le.setDisabled(1-checked)
        checkbox.stateChanged.connect(lambda on: self.changeRenameFiles(on))
        checkbox.stateChanged.connect(lambda on: le.setEnabled(on))

        le.setText('Renaming Format: Author_Year_Title.pdf')

        va.addWidget(checkbox)
        va.addWidget(le)

        #----------------Auto save section----------------
        va.addWidget(getHLine(self))
        label3=QtWidgets.QLabel('Auto save interval (min)')
        label3.setStyleSheet(self.label_color)
        label3.setFont(self.title_label_font)
        va.addWidget(label3)
        va.addWidget(getHLine(self))

        slider=LabeledSlider(1,10,1,parent=self)
        slider.sl.setValue(self.settings.value('saving/auto_save_min',2,int))
        slider.sl.valueChanged.connect(self.changeSavingInterval)
        slider.setMaximumWidth(400)

        va.addWidget(slider)

        va.addStretch()


        return scroll


    def chooseSaveFolder(self):
        fname=QtWidgets.QFileDialog.getExistingDirectory(self,
            'Choose a folder to save documents and database')

        if fname:
            print('# <chooseFont>: Folder after change:', fname)
            self.new_values['saving/storage_folder']=fname


        return

    def changeRenameFiles(self,on):
        on=1 if on>0 else 0 # for some reason <on> keeps giving me 2
        self.new_values['saving/rename_files']=on
        print('# <changeRenameFiles>: Change rename files to %s' %on)
        LOGGER.info('Change rename files to %s' %on)
        return


    def changeSavingInterval(self,value):
        print('# <changeSavingInterval>: Change auto saving interval to %s' %value)
        LOGGER.info('Change auto saving interval to %s' %value)

        self.new_values['saving/auto_save_min']=value
        return



    def loadExportOptions(self):

        scroll, va=self.createFrame('bibtex Export')

        self.groupbox=self.createOmitKeyGroup()
        va.addWidget(self.groupbox)

        return scroll


    def omitKeyChanged(self,on):
        self.new_values['export/bib/omit_fields']=self.getOmitKeys()

        return

    def omitKeysGroupChanged(self, on, groupbox):
        omit_keys=[]

        for box in groupbox.findChildren(QtWidgets.QCheckBox):
            box.stateChanged.disconnect()
            box.setChecked(on)
            box.setEnabled(True)
            box.stateChanged.connect(self.omitKeyChanged)
            if box.isChecked():
                omit_keys.append(box.text())

        self.new_values['export/bib/omit_fields']=omit_keys

        return

    def getOmitKeys(self):

        omit_keys=[]

        for box in self.groupbox.findChildren(QtWidgets.QCheckBox):
            if box.isChecked():
                omit_keys.append(box.text())

        return omit_keys



    def loadCitationStyleOptions(self):

        scroll, va=self.createFrame('Citation Styles')
        va.addStretch()

        return scroll


    def loadMiscellaneousOptions(self):

        scroll, va=self.createFrame('Auto Open')

        #-------Open last database on launch section-------
        checkbox=QtWidgets.QCheckBox('Automatically Open Last Database on Start-up?')
        checkbox.stateChanged.connect(self.changeAutoOpenLast)
        auto_open_last=self.settings.value('file/auto_open_last',type=int)
        if auto_open_last==1:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)

        va.addWidget(checkbox)
        va.addWidget(getHLine(self))

        #--------------Recent number section--------------
        label1=QtWidgets.QLabel('Number of Recently Opened Database')
        label1.setStyleSheet(self.label_color)
        label1.setFont(self.title_label_font)
        va.addWidget(label1)

        slider2=LabeledSlider(0,10,1,parent=self)
        slider2.sl.setValue(self.settings.value('file/recent_open_num',type=int))
        slider2.sl.valueChanged.connect(self.changeRecentNumber)
        slider2.setMaximumWidth(400)

        va.addWidget(slider2)
        va.addWidget(getHLine())

        #------------Duplicate check min score------------
        label2=QtWidgets.QLabel('Duplicate Check')
        label2.setStyleSheet(self.label_color)
        label2.setFont(self.title_label_font)
        va.addWidget(label2)

        label3=QtWidgets.QLabel('Minimum Similarity Score to Define Duplicate (1-100)')
        self.spinbox=QtWidgets.QSpinBox()
        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(100)
        self.spinbox.setValue(self.settings.value('duplicate_min_score',type=int))
        self.spinbox.valueChanged.connect(self.changeDuplicateMinScore)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(label3)
        ha.addWidget(self.spinbox)

        va.addLayout(ha)
        va.addStretch()

        return scroll

    def changeAutoOpenLast(self,on):

        if on:
            self.new_values['file/auto_open_last']=1
        else:
            self.new_values['file/auto_open_last']=0

        print('# <changeAutoOpenLast>: Change auto open last to %s' %on)
        LOGGER.info('Change auto open last to %s' %on)
        return


    def changeRecentNumber(self,value):
        print('# <changeRecentNumber>: Change recent database number to %s' %value)
        LOGGER.info('Change recent database number to %s' %value)

        self.new_values['file/recent_open_num']=value
        return

    def changeDuplicateMinScore(self,value):
        print('# <changeDuplicateMinScore>: Change min duplicate score to %s' %value)
        LOGGER.info('Change min duplicate score to %s' %value)

        self.new_values['duplicate_min_score']=value
        return


def createFolderTree(folder_dict,parent):

    def addFolder(parent,folderid,folder_dict):

        foldername,parentid=folder_dict[folderid]
        fitem=QtWidgets.QTreeWidgetItem([foldername,str(folderid)])
        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        fitem.setIcon(0,diropen_icon)
        sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
        if parentid=='-1':
            fitem.setFlags(fitem.flags() | Qt.ItemIsTristate |\
                    Qt.ItemIsUserCheckable)
            fitem.setCheckState(0, Qt.Unchecked)
            parent.addTopLevelItem(fitem)
        else:
            fitem.setFlags(fitem.flags() | Qt.ItemIsUserCheckable)
            fitem.setCheckState(0, Qt.Unchecked)
            parent.addChild(fitem)
        if len(sub_ids)>0:
            for sii in sub_ids:
                addFolder(fitem,sii,folder_dict)

        return

    folder_tree=QtWidgets.QTreeWidget(parent)
    folder_tree.setColumnCount(2)
    folder_tree.setHeaderHidden(True)
    folder_tree.setColumnHidden(1,True)
    folder_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    folder_tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
    folder_tree.header().setStretchLastSection(False)
    folder_tree.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents)
    folder_tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

    #-------------Get all level 1 folders-------------
    folders1=[(vv[0],kk) for kk,vv in folder_dict.items() if\
            vv[1] in ['-1',]]
    folders1.sort()

    #------------Add folders to tree------------
    for fnameii,idii in folders1:
        addFolder(folder_tree,idii,folder_dict)

    return folder_tree


def iterTreeWidgetItems(treewidget, root=None):
    if root is None:
        root=treewidget.invisibleRootItem()

    stack = [root]
    while stack:
        parent = stack.pop(0)
        for row in range(parent.childCount()):
            child = parent.child(row)
            yield child
            if child.childCount()>0:
                stack.append(child)



class LabeledSlider(QtWidgets.QWidget):
    def __init__(self, minimum, maximum, interval=1, orientation=Qt.Horizontal,
            labels=None, parent=None):
        super(LabeledSlider, self).__init__(parent=parent)

        levels=range(minimum, maximum+interval, interval)
        if labels is not None:
            if not isinstance(labels, (tuple, list)):
                raise Exception("<labels> is a list or tuple.")
            if len(labels) != len(levels):
                raise Exception("Size of <labels> doesn't match levels.")
            self.levels=list(zip(levels,labels))
        else:
            self.levels=list(zip(levels,map(str,levels)))

        if orientation==Qt.Horizontal:
            self.layout=QtWidgets.QVBoxLayout(self)
        elif orientation==Qt.Vertical:
            self.layout=QtWidgets.QHBoxLayout(self)
        else:
            raise Exception("<orientation> wrong.")

        # gives some space to print labels
        self.left_margin=10
        self.top_margin=10
        self.right_margin=10
        self.bottom_margin=10

        self.layout.setContentsMargins(self.left_margin,self.top_margin,
                self.right_margin,self.bottom_margin)

        self.sl=QtWidgets.QSlider(orientation, self)
        self.sl.setMinimum(minimum)
        self.sl.setMaximum(maximum)
        self.sl.setValue(minimum)
        if orientation==Qt.Horizontal:
            self.sl.setTickPosition(QtWidgets.QSlider.TicksBelow)
            #self.sl.setMinimumWidth(300) # just to make it easier to read
        else:
            self.sl.setTickPosition(QtWidgets.QSlider.TicksLeft)
            #self.sl.setMinimumHeight(300) # just to make it easier to read
        self.sl.setTickInterval(interval)
        self.sl.setSingleStep(1)

        self.layout.addWidget(self.sl)

    def paintEvent(self, e):

        super(LabeledSlider,self).paintEvent(e)

        style=self.sl.style()
        painter=QPainter(self)
        st_slider=QStyleOptionSlider()
        st_slider.initFrom(self.sl)
        st_slider.orientation=self.sl.orientation()

        length=style.pixelMetric(QStyle.PM_SliderLength, st_slider, self.sl)
        available=style.pixelMetric(QStyle.PM_SliderSpaceAvailable, st_slider, self.sl)

        for v, v_str in self.levels:

            # get the size of the label
            rect=painter.drawText(QRect(), Qt.TextDontPrint, v_str)

            if self.sl.orientation()==Qt.Horizontal:
                # I assume the offset is half the length of slider, therefore
                # + length//2
                x_loc=QStyle.sliderPositionFromValue(self.sl.minimum(),
                        self.sl.maximum(), v, available)+length//2

                # left bound of the text = center - half of text width + L_margin
                left=x_loc-rect.width()//2+self.left_margin
                bottom=self.rect().bottom()

                # enlarge margins if clipping
                if v==self.sl.minimum():
                    if left<=0:
                        self.left_margin=rect.width()//2-x_loc
                    if self.bottom_margin<=rect.height():
                        self.bottom_margin=rect.height()

                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

                if v==self.sl.maximum() and rect.width()//2>=self.right_margin:
                    self.right_margin=rect.width()//2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            else:
                y_loc=QStyle.sliderPositionFromValue(self.sl.minimum(),
                        self.sl.maximum(), v, available, upsideDown=True)

                bottom=y_loc+length//2+rect.height()//2+self.top_margin-3
                # there is a 3 px offset that I can't attribute to any metric

                left=self.left_margin-rect.width()
                if left<=0:
                    self.left_margin=rect.width()+2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            pos=QPoint(left, bottom)
            painter.drawText(pos, v_str)

        return


class ExportDialog(QtWidgets.QDialog):
    def __init__(self,settings,parent):

        super(ExportDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(800,600)
        self.setWindowTitle('Bulk Export')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Choose Export Type')
        title_label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(title_label)

        v_layout.addLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        #self.list.setSizePolicy(getXMinYExpandSizePolicy())
        self.cate_list.setMaximumWidth(200)
        h_layout.addWidget(self.cate_list)

        #self.cate_list.setStyleSheet('''
            #QListWidget::item { border: 0px solid rgb(235,235,240);
            #font: 14px;
            #background-color: rgb(205,205,245);
            #color: rgb(100,10,13) };
            #background-color: rgb(230,234,235);
            #''')

        self.cate_list.addItems(['Copy Document Files', 'Export to bibtex',
            'Export to RIS', 'Export to Zotero'])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)



    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):

        item_text=item.text()
        print('# <cateSelected>: item.text()=%s' %item_text)

        if self.content_vlayout.count()>1:
            self.content_vlayout.removeWidget(self.content_frame)

        if item_text=='Copy Document Files':
            self.content_frame=self.loadCopyFileOptions()
        elif item_text=='Export to bibtex':
            self.content_frame=self.loadExportBibOptions()
        elif item_text=='Export to RIS':
            self.content_frame=self.loadExportRISOptions()
        elif item_text=='Export to Zotero':
            self.content_frame=self.loadExportZoteroOptions()

        self.content_vlayout.insertWidget(0,self.content_frame)

    def createFrame(self,title):

        frame=QtWidgets.QWidget(self)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        va=QtWidgets.QVBoxLayout()
        frame.setLayout(va)
        va.setSpacing(int(va.spacing()*2))

        label=QtWidgets.QLabel(title)
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        va.addWidget(label)
        va.addWidget(getHLine(self))

        return scroll, va


    def createOmitKeyGroup(self):

        grid=QtWidgets.QGridLayout()

        self.groupbox=QtWidgets.QGroupBox('Omit these fields in the exported bib entry.')
        self.groupbox.setCheckable(True)

        omittable_keys=[
            'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
            'lastName_l', 'pend_delete', 'folders_l', 'type', 'id',
            'abstract', 'advisor', 'month', 'language', 'confirmed',
            'deletionPending', 'note', 'publicLawNumber', 'sections',
            'reviewedArticle', 'userType', 'shortTitle', 'sourceType',
            'code', 'codeNumber', 'codeSection', 'codeVolume', 'citationKey',
            'day', 'dateAccessed', 'internationalAuthor', 'internationalUserType',
            'internationalTitle', 'internationalNumber', 'genre', 'lastUpdate',
            'legalStatus', 'length', 'medium'
            ]
        omittable_keys.sort()

        omit_keys=self.settings.value('export/bib/omit_fields', [], str)
        # likely something wrong with qt. When list is set empty by
        # settings.setValue('key',[]), on the NEXT load of the program,
        # settings.value('export/bib/omit_fields', [], str) gives ''
        if isinstance(omit_keys,str) and omit_keys=='':
            omit_keys=[]

        for ii,keyii in enumerate(omittable_keys):
            checkboxii=QtWidgets.QCheckBox(keyii,self.groupbox)
            if keyii in omit_keys:
                checkboxii.setChecked(True)
            checkboxii.stateChanged.connect(self.omitKeyChanged)
            grid.addWidget(checkboxii,int(ii/3),ii%3)

        self.groupbox.toggled.connect(lambda on: self.omitKeysGroupChanged(on,
            self.groupbox))

        self.groupbox.setLayout(grid)


        return self.groupbox



    def loadCopyFileOptions(self):

        scroll,va=self.createFrame('Copy Document Files')
        self.copyfile_settings={}


        #---------------Fold choice section---------------
        va.addWidget(getHLine())

        label=QtWidgets.QLabel('''
        Choose folders to export documents. <br/>
        This will copy documents (e.g. PDFs) from the
        <span style="font:bold;">"Collections"</span>
        folder to a separate folder under <span style="font:bold;">"%s"</span>
        ''' %self.settings.value('/saving/storage_folder',str))
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        va.addWidget(label)

        # create folder list
        if self.parent.is_loaded:
            # What if database if empty

            folder_dict=self.parent.main_frame.folder_dict
            self.folder_tree=createFolderTree(folder_dict,self)
            va.addWidget(self.folder_tree)

        va.addWidget(getHLine())

        do_button=QtWidgets.QPushButton('Export')
        do_button.clicked.connect(self.doExportFiles)

        va.addWidget(do_button,0, Qt.AlignLeft)

        return scroll



    def loadExportBibOptions(self):

        scroll,va=self.createFrame('Export to bibtex')
        self.bib_settings={}

        #--------------Export manner section--------------
        groupbox=QtWidgets.QGroupBox('Export documents')
        va2=QtWidgets.QVBoxLayout()
        groupbox.setLayout(va2)

        choices=['All in one', 'Per folder', 'Per document']
        for ii in choices:
            radioii=QtWidgets.QRadioButton(ii)
            if ii=='Per folder':
                radioii.setChecked(True)
            radioii.toggled.connect(lambda on: self.bibExportMannerChanged(on,groupbox))
            va2.addWidget(radioii)

        va.addWidget(groupbox)

        #----------------Omit keys section----------------
        self.groupbox=self.createOmitKeyGroup()
        va.addWidget(self.groupbox)

        va.addWidget(getHLine())

        do_button=QtWidgets.QPushButton('Export')
        do_button.clicked.connect(self.doBibExport)

        va.addWidget(do_button,0, Qt.AlignLeft)

        return scroll


    def bibExportMannerChanged(self,on,groupbox):

        for box in groupbox.findChildren(QtWidgets.QRadioButton):
            if box.isChecked():
                choice=box.text()
                break

        self.bib_settings['manner']=choice
        print('# <bibExportMannerChanged>: choice',choice,on,self.bib_settings)
        return


    def omitKeyChanged(self,on):
        self.bib_settings['omit_keys']=self.getOmitKeys()
        print('# <omitKeyChanged>: omit keys=',self.bib_settings['omit_keys'])
        return

    def omitKeysGroupChanged(self, on, groupbox):
        omit_keys=[]

        for box in groupbox.findChildren(QtWidgets.QCheckBox):
            box.stateChanged.disconnect()
            box.setChecked(on)
            box.setEnabled(True)
            box.stateChanged.connect(self.omitKeyChanged)
            if box.isChecked():
                omit_keys.append(box.text())

        self.bib_settings['omit_keys']=omit_keys
        print('# <omitKeyChanged>: omit keys=',self.bib_settings['omit_keys'])

        return

    def getOmitKeys(self):

        omit_keys=[]

        for box in self.groupbox.findChildren(QtWidgets.QCheckBox):
            if box.isChecked():
                omit_keys.append(box.text())

        return omit_keys



    def loadExportRISOptions(self):

        scroll,va=self.createFrame('Export to RIS')

        return scroll

    def loadExportZoteroOptions(self):

        scroll,va=self.createFrame('Export to Zotero')

        return scroll

    def doExportFiles(self):
        folder_dict=self.parent.main_frame.folder_dict
        folder_data=self.parent.main_frame.folder_data
        meta_dict=self.parent.main_frame.meta_dict
        storage_folder=self.settings.value('saving/storage_folder',str)

        if not os.path.exists(storage_folder):
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setWindowTitle('Critical Error!')
            msg.setText("Can not find storage folder.")
            msg.setInformativeText("I can't find the storage folder at %s. Data lost."\
                    %storage_folder)
            msg.exec_()
            return

        job_list=[] # (jobid, source_path, target_path)
        for item in iterTreeWidgetItems(self.folder_tree):
            if item.checkState(0):
                folderid=item.data(1,0)
                docids=folder_data[folderid]
                print('# <doExportFiles>: choose folder', item.data(0,0),
                        item.data(1,0))
                tree=sqlitedb.getFolderTree(folder_dict,folderid)[1]
                print('# <doExportFiles>: tree',tree)
                print('# <doExportFiles>: docids in folder', docids)

                folderii=os.path.join(storage_folder,tree)
                if not os.path.exists(folderii):
                    os.makedirs(folderii)
                    print('# <doExportFiles>: Create folder %s' %folderii)
                    LOGGER.info('Create folder %s' %folderii)

                for idii in docids:
                    if meta_dict[idii]['has_file']:
                        for fjj in meta_dict[idii]['files_l']:
                            filenamejj=sqlitedb.renameFile(fjj,meta_dict[idii])
                            newfjj=os.path.join(folderii,filenamejj)
                            job_list.append((len(job_list), fjj, newfjj))

        import time
        def copyFunc(jobid,s,t):
            try:
                #shutil.copy(s,t)
                rec=0
                result=None
            except:
                rec=1
                result=None
            
            time.sleep(0.5)
            return rec,jobid,result

        if len(job_list)>0:
            self.parent.main_frame.threadedFuncCall2(
                    copyFunc,job_list,'Exporting Files...')

        return



    def doBibExport(self):
        return


class Worker(QObject):

    worker_jobdone_signal=pyqtSignal(int) # jobid

    def __init__(self, id, func, jobqueue, outqueue):
        super(Worker,self).__init__()
        '''Worker used for separate thread.

        NOTE: args for func is assumed to have the format (jobid,jobargs)
        return of func is assumed to have the format (return_code, jobid,\
                other_results)
        '''

        self.id=id
        self.func=func
        self.jobqueue=jobqueue
        self.outqueue=outqueue
        self.abort=False

    @pyqtSlot()
    def processJob(self):
        while self.jobqueue.qsize():
            QtWidgets.QApplication.processEvents()
            if self.abort:
                return

            args=self.jobqueue.get()
            jobid=args[0]
            try:
                rec=self.func(*args)
                print('# <Worker>: Job %d done. Remaining queue size: %d.'\
                    %(jobid, self.jobqueue.qsize()))
            except:
                rec=(1,jobid,None)
                print('# <Worker>: Job %d failed. Remaining queue size: %d.'\
                    %(jobid, self.jobqueue.qsize()))
            self.jobqueue.task_done()
            self.outqueue.put(rec)
            self.worker_jobdone_signal.emit(jobid)

        return



class Master(QObject):

    all_done_signal=pyqtSignal()
    donejobs_count_signal=pyqtSignal(int) # NO. of finshed jobs

    def __init__(self, func, joblist, max_threads=4):
        super(Master,self).__init__()

        self.func=func
        self.joblist=joblist
        self.max_threads=max_threads
        self.all_done_signal.connect(self.onAllJobsDone)

    def run(self):

        self.threads=[]
        self.results=[]
        n_threads=min(self.max_threads,len(self.joblist))
        self.finished=0
        self.finished_jobs=[]

        self.jobqueue=Queue()
        self.outqueue=Queue()
        # populate job queue
        for ii,jobii in enumerate(self.joblist):
            self.jobqueue.put(jobii)

        # start worker threads
        for ii in range(n_threads):
            print('# <run>: create thread',ii)
            tii=QThread()
            wii=Worker(ii,self.func,self.jobqueue,self.outqueue)
            self.threads.append((tii,wii)) # need to keep record of both!

            wii.moveToThread(tii)
            wii.worker_jobdone_signal.connect(self.countJobDone)
            tii.started.connect(wii.processJob)
            tii.start()

        return


    @pyqtSlot(int)
    def countJobDone(self,jobid):
        self.finished+=1
        self.finished_jobs.append(jobid)
        self.donejobs_count_signal.emit(self.finished)
        while self.outqueue.qsize():
            resii=self.outqueue.get()
            self.results.append(resii)

        print('# <countJobDone>: Finished job id=%d. Finished jobs=%d'\
                %(jobid, self.finished))

        if self.finished==len(self.joblist):
            self.all_done_signal.emit()

        return


    @pyqtSlot()
    def onAllJobsDone(self):
        while self.outqueue.qsize():
            resii=self.outqueue.get()
            self.results.append(resii)

        for tii,wii in self.threads:
            tii.quit()
            tii.wait()
        return

    @pyqtSlot()
    def abortJobs(self):
        for tii,wii in self.threads:
            wii.abort=True
            tii.quit()
            tii.wait()



class ThreadRunDialog(QtWidgets.QDialog):

    def __init__(self,func,joblist,show_message='',max_threads=3,
            get_results=False,close_on_finish=True,parent=None):
        super(ThreadRunDialog,self).__init__(parent=parent)

        self.func=func
        self.joblist=joblist
        self.show_message=show_message
        self.max_threads=max_threads
        self.get_results=get_results
        self.close_on_finish=close_on_finish
        self.parent=parent

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle('Processing ...')
        self.resize(500,100)

        va=QtWidgets.QVBoxLayout(self)

        va.addWidget(QtWidgets.QLabel(show_message))

        self.progressbar=QtWidgets.QProgressBar(self)
        self.progressbar.setMaximum(len(joblist))
        self.progressbar.setValue(0)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)

        va.addWidget(self.progressbar)
        va.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.abortJobs)

        self.master=Master(func,joblist,self.max_threads)
        self.master.donejobs_count_signal.connect(self.updatePB)
        self.ok_button=self.buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        self.cancel_button=self.buttons.button(QDialogButtonBox.Cancel)
        self.master.all_done_signal.connect(self.allJobsDone)

        self.master.run()
        self.exec_()


    @pyqtSlot()
    def allJobsDone(self):
        self.cancel_button.setEnabled(False)
        self.ok_button.setEnabled(True)
        if self.close_on_finish:
            self.accept()
        return

    @pyqtSlot(int)
    def updatePB(self,value):
        self.progressbar.setValue(value)
        return

    @pyqtSlot()
    def abortJobs(self):
        self.master.abortJobs()
        if self.get_results:
            self.results=self.master.results
        self.reject()
        return

    @pyqtSlot()
    def accept(self):
        print('# <accept>: get result?',self.get_results)
        if self.get_results:
            self.results=self.master.results
            print('# <accept>: self.results',self.results)
        super(ThreadRunDialog,self).accept()
        return



class CheckDuplicateDialog(QtWidgets.QDialog):

    def __init__(self,settings,meta_dict,docids1,docid2=None,parent=None):
        super(CheckDuplicateDialog,self).__init__(parent=parent)

        self.settings=settings
        self.docids1=docids1
        self.docids1.sort()
        self.docid2=docid2
        self.meta_dict=meta_dict

        self.min_score=self.settings.value('duplicate_min_score',type=int)

        self.resize(900,600)
        self.setWindowTitle('Duplicate Check')
        self.setWindowModality(Qt.ApplicationModal)

        va=QtWidgets.QVBoxLayout(self)

        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(6)

        self.tree.setHeaderLabels(['Group', 'Authors', 'Title', 'Publication',
            'Year', 'Similarity'])
        self.tree.setColumnWidth(0, 55)
        self.tree.setColumnWidth(1, 250)
        self.tree.setColumnWidth(2, 300)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 50)
        self.tree.setColumnWidth(5, 20)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.noDupLabel=QtWidgets.QLabel('No duplicates found.')

        va.addWidget(self.noDupLabel)
        va.addWidget(self.tree)
        va.addWidget(self.buttons)

        self.scores_dict=self.checkDuplicates()

        self.addResultToTree()
        self.exec_()

    def checkDuplicates(self):

        n=len(self.docids1)

        scores=[]
        scores_dict={}
        if self.docid2 is None:
            #----------------Check among docds----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoresii=[]
                for jj in range(n):
                    if ii>=jj:
                        scoreij=0
                    else:
                        docjj=self.docids1[jj]
                        scoreij=fuzzyMatch(self.meta_dict[docii], self.meta_dict[docjj])
                        scores_dict[(docii,docjj)]=scoreij
                    scoresii.append(scoreij)
                scores.append(scoresii)

            print('# <checkDuplicates>: scores=')
            for ii in range(n):
                print(scores[ii])

        else:
            #-----------------1 to all compare-----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoreii=fuzzyMatch(self.meta_dict[docii],
                        self.meta_dict[self.docid2])
                scores_dict[docii]=scoreii
                scores.append(scoreii)

            print('# <checkDuplicates>: scores=', scores)

        return scores_dict

    def addResultToTree(self):

        if self.docid2 is None:
            #-------------------Build graph-------------------
            import networkx as nx

            g=nx.Graph()
            edges=[kk for kk,vv in self.scores_dict.items() if vv>=self.min_score]

            if len(edges)==0:
                self.resize(400,200)
                self.tree.setVisible(False)
                self.noDupLabel.setVisible(True)
                return

            self.resize(900,600)
            self.tree.setVisible(True)
            self.noDupLabel.setVisible(False)
            g.add_edges_from(edges)
            print('# <addResultToTree>: edges',edges,'g.edges',list(g.edges))

            #comps=list(nx.connected_components(g))
            comps=[list(cii) for cii in sorted(nx.connected_components(g), key=len,\
                    reverse=True)]
            print('# <addResultToTree>: comps=',comps)

            #--------------------Add items--------------------
            for ii,cii in enumerate(comps):
                cii.sort()
                #itemii=QtWidgets.QTreeWidgetItem([str(ii+1),])
                docjj=cii[0]
                metajj=self.meta_dict[docjj]
                itemii=QtWidgets.QTreeWidgetItem([str(ii+1),
                    ', '.join(metajj['authors_l']),
                    metajj['title'],
                    metajj['publication'],
                    str(metajj['year']),
                    ''])
                self.tree.addTopLevelItem(itemii)

                # sort by scores
                docs=cii[1:]
                scores=[self.scores_dict[(cii[0],dii)] for dii in docs]
                docs=[x for _,x in sorted(zip(scores,docs), reverse=True)]

                for docjj in docs:
                    metajj=self.meta_dict[docjj]
                    itemjj=QtWidgets.QTreeWidgetItem(['',
                        ', '.join(metajj['authors_l']),
                        metajj['title'],
                        metajj['publication'],
                        str(metajj['year']),
                        str(self.scores_dict[(cii[0],docjj)])
                        ])
                    itemii.addChild(itemjj)

            self.tree.expandAll()
        else:
            pass

        return 


class CheckDuplicateFrame(QtWidgets.QScrollArea):

    del_doc_from_folder_signal=pyqtSignal(list, str, str, bool)
    del_doc_from_lib_signal=pyqtSignal(list, bool)
    def __init__(self,settings,parent=None):
        super(CheckDuplicateFrame,self).__init__(parent=parent)

        self.settings=settings
        self.min_score=self.settings.value('duplicate_min_score',type=int)

        frame=QtWidgets.QWidget()
        self.setWidgetResizable(True)
        self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)

        #----------------Create clear frame----------------
        va.addWidget(self.createClearDuplicateFrame())

        #----------------Create treewidget----------------
        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(7)
        self.tree.setColumnHidden(6,True)

        self.tree.setHeaderLabels(['Group', 'Authors', 'Title',
            'Publication', 'Year', 'Similarity','id'])
        self.tree.setColumnWidth(0, 55)
        self.tree.setColumnWidth(1, 250)
        self.tree.setColumnWidth(2, 300)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 50)
        self.tree.setColumnWidth(5, 20)
        self.tree.setColumnWidth(6, 0)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.docTreeMenu)

        self.noDupLabel=QtWidgets.QLabel('No duplicates found.')
        va.addWidget(self.noDupLabel)
        va.addWidget(self.tree)

        frame.setLayout(va)

    def createClearDuplicateFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        ha=QtWidgets.QHBoxLayout()

        # del button
        self.del_duplicate_button=QtWidgets.QToolButton(self)
        self.del_duplicate_button.setText('Delete Selected')
        self.del_duplicate_button.clicked.connect(self.delDocs)

        # clear button
        self.clear_duplicate_button=QtWidgets.QToolButton(self)
        self.clear_duplicate_button.setText('Exit')

        self.clear_duplicate_label=QtWidgets.QLabel('Clear current filtering')
        ha.addWidget(self.clear_duplicate_label)
        tip_label=QtWidgets.QLabel()
        tip_icon=QIcon.fromTheme('help-about').pixmap(QSize(16,16))
        tip_label.setPixmap(tip_icon)
        tip_label.setToolTip('''Change "Mininimum Similary Score" in "Preferences" to change the filtering of matching results.''')
        ha.addWidget(tip_label)
        ha.addWidget(self.del_duplicate_button)
        ha.addWidget(self.clear_duplicate_button)

        frame.setLayout(ha)

        return frame



    def checkDuplicates(self,meta_dict,current_folder,docids1,docid2=None):

        self.tree.clear()

        self.meta_dict=meta_dict
        self.current_folder=current_folder # (name, id)
        self.docids1=docids1
        self.docids1.sort()
        self.docid2=docid2

        n=len(self.docids1)

        scores=[]
        self.scores_dict={}
        if self.docid2 is None:
            #----------------Check among docds----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoresii=[]
                for jj in range(n):
                    if ii>=jj:
                        scoreij=0
                    else:
                        docjj=self.docids1[jj]
                        scoreij=fuzzyMatch(self.meta_dict[docii], self.meta_dict[docjj])
                        self.scores_dict[(docii,docjj)]=scoreij
                    scoresii.append(scoreij)
                scores.append(scoresii)

            print('# <checkDuplicates>: scores=')
            for ii in range(n):
                print(scores[ii])

        else:
            #-----------------1 to all compare-----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoreii=fuzzyMatch(self.meta_dict[docii],
                        self.meta_dict[self.docid2])
                self.scores_dict[docii]=scoreii
                scores.append(scoreii)

            print('# <checkDuplicates>: scores=', scores)

        return

    def addResultToTree(self):

        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        if self.docid2 is None:
            #-------------------Build graph-------------------

            g=nx.Graph()
            edges=[kk for kk,vv in self.scores_dict.items() if vv>=self.min_score]

            if len(edges)==0:
                self.noDupLabel.setVisible(True)
                return

            self.noDupLabel.setVisible(False)
            g.add_edges_from(edges)
            print('# <addResultToTree>: edges',edges,'g.edges',list(g.edges))

            comps=[list(cii) for cii in sorted(nx.connected_components(g), key=len,\
                    reverse=True)]
            print('# <addResultToTree>: comps=',comps)

            #--------------------Add items--------------------
            for ii,cii in enumerate(comps):
                cii.sort()
                docjj=cii[0]
                metajj=self.meta_dict[docjj]
                itemii=QtWidgets.QTreeWidgetItem([
                    str(ii+1),
                    ', '.join(metajj['authors_l']),
                    metajj['title'],
                    metajj['publication'],
                    str(metajj['year']),
                    '',
                    str(docjj)
                    ])

                for jj in range(self.tree.columnCount()):
                    itemii.setBackground(jj, QBrush(QColor(230,230,249)))

                self.tree.addTopLevelItem(itemii)

                # sort by scores
                docs=cii[1:]
                scores=[self.scores_dict[(cii[0],dii)] for dii in docs]
                docs=[x for _,x in sorted(zip(scores,docs), reverse=True)]

                for docjj in docs:
                    metajj=self.meta_dict[docjj]
                    itemjj=QtWidgets.QTreeWidgetItem([
                        '',
                        ', '.join(metajj['authors_l']),
                        metajj['title'],
                        metajj['publication'],
                        str(metajj['year']),
                        str(self.scores_dict[(cii[0],docjj)]),
                        str(docjj)
                        ])
                    itemii.addChild(itemjj)

            self.tree.expandAll()
        else:
            pass

        return 


    def docTreeMenu(self,pos):

        menu=QtWidgets.QMenu()

        print('# <docTreeMenu>: current_folder=',self.current_folder)
        foldername,folderid=self.current_folder
        if folderid=='-1':
            menu.addAction('Delete From Library')
        else:
            menu.addAction('Delete From Current Folder')

        action=menu.exec_(QCursor.pos())

        if action:
            self.delDocs()

        return


    @pyqtSlot()
    def delDocs(self):

        print('# <docTreeMenu>: current_folder=',self.current_folder)
        foldername,folderid=self.current_folder
        sel_rows=self.tree.selectedItems()
        if len(sel_rows)>0:

            docids=[int(ii.data(6,0)) for ii in sel_rows]

            print('# <docTreeMenu>: Selected docids=%s.' %docids)
            LOGGER.info('Selected docids=%s.' %docids)

            if folderid=='-1':
                self.del_doc_from_lib_signal.emit(docids,False)
            else:
                self.del_doc_from_folder_signal.emit(docids, foldername,
                        folderid, False)

            for itemii in sel_rows:
                self.tree.invisibleRootItem().removeChild(itemii)

        return
