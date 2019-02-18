import os
from datetime import datetime
import operator
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, pyqtSignal, QPoint,\
        pyqtSlot, QMimeData, QByteArray, QEvent
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon, QFont, QFontMetrics,\
        QCursor, QRegExpValidator
import resources
from lib import sqlitedb
from .tools import getHLine, getXExpandYMinSizePolicy, getXMinYExpandSizePolicy,\
    parseAuthors, getXExpandYExpandSizePolicy, getMinSizePolicy


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
                'has_file': QIcon(':/has_file.png')
                }
        self.check_section={
                'favourite': QPixmap(':/bf.jpg'),
                'read': QPixmap(':/read.jpg')
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

        LOGGER=logging.getLogger('default_logger')
        self.settings=settings
        self.font_dict={
            'meta_title': self.settings.value('display/fonts/meta_title',QFont),
            'meta_authors': self.settings.value('display/fonts/meta_authors',QFont),
            'meta_keywords': self.settings.value('display/fonts/meta_keywords',QFont)
            }
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
        title_te.setFont(self.font_dict['meta_title'])
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

        if font_name in self.font_dict:
            te.setFont(self.font_dict[font_name])

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

        if font_name in self.font_dict:
            te.setFont(self.font_dict[font_name])

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

        if font_name in self.font_dict:
            le.setFont(self.font_dict[font_name])

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
        button.clicked.connect(lambda: self.delFileField(
            self.fields_dict['files_l'].index(le)))

        le.del_button=button
        h_layout.addWidget(le)
        h_layout.addWidget(button)

        print('# <createFileField>: Insert at %s' %self.file_insert_idx)
        LOGGER.info('Insert at %s' %self)

        self.v_layout.insertLayout(self.file_insert_idx,h_layout)
        self.file_insert_idx+=1

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
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a PDF file',
         '',"PDF files (*.pdf);; All files (*)")[0]

        if fname:

            print('# <addFileButtonClicked>: New file=%s' %fname)
            LOGGER.info('New file=%s' %fname)

            self.createFileField(fname)
            self.fieldEdited()

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

    def __init__(self,font_dict,parent=None):
        super(MetaDataEntryDialog,self).__init__(parent)

        self.resize(500,700)
        self.setWindowTitle('Add New Entry')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()

        self.scroll=MetaTabScroll(font_dict,self)

        self.buttons=QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
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
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def showEvent(self,e):
        if not self.initialized:
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
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

        self.font_dict=OrderedDict([
            ('Meta Tab -> Title'      , 'display/fonts/meta_title')    ,
            ('Meta Tab -> Authors'    , 'display/fonts/meta_authors')  ,
            ('Meta Tab -> Keywords'   , 'display/fonts/meta_keywords') ,
            ('Document Table Entries' , 'display/fonts/doc_table')     ,
            ('Bibtex Tab'             , 'display/fonts/bibtex')        ,
            ('Notes Tab'              , 'display/fonts/notes')         ,
            ('Scratch Pad Tab'        , 'display/fonts/scratch_pad')
            ])

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.label_font=QFont('Serif',12,QFont.Bold)

        self.resize(800,600)
        self.setWindowTitle('Preferences')
        self.setWindowModality(Qt.ApplicationModal)

        h_layout=QtWidgets.QHBoxLayout()
        self.setLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        #self.list.setSizePolicy(getXMinYExpandSizePolicy())
        self.cate_list.setMaximumWidth(150)
        h_layout.addWidget(self.cate_list)

        self.categories=['Display', 'Export', 'Citation Style', 'Savings']
        self.cate_list.addItems(self.categories)

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        '''
        frame=QtWidgets.QWidget()
        self.dummy_scroll=QtWidgets.QScrollArea(self)
        self.dummy_scroll.setWidgetResizable(True)
        self.dummy_scroll.setWidget(frame)

        self.content_vlayout.addWidget(self.dummy_scroll)
        '''

        self.buttons=QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
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

        if item_text=='Display':
            self.content_frame=self.loadDisplayOptions('Select Fonts')
        elif item_text=='Export':
            self.content_frame=self.loadExportOptions('Export Settings')
        elif item_text=='Citation Style':
            self.content_frame=self.loadCitationStyleOptions('Citation Styles')
        elif item_text=='Savings':
            self.content_frame=self.loadSavingsOptions('Choose Storage Folder')

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
        label.setFont(self.label_font)
        va.addWidget(label)
        va.addWidget(getHLine(self))

        return scroll, va


    def loadDisplayOptions(self,title):

        scroll,va=self.createFrame(title)

        ha=QtWidgets.QHBoxLayout()
        ha.addStretch()

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
            self.settings.setValue(font_setting_name, new_font)
            newf=self.settings.value(font_setting_name, QFont)
            print('# <chooseFont>: Font after change:', newf)

        return



    def loadSavingsOptions(self,title):

        scroll, va=self.createFrame(title)

        label2=QtWidgets.QLabel('Select folder to save document files and database file.')
        va.addWidget(label2)

        ha=QtWidgets.QHBoxLayout()
        ha.addStretch()

        storage_folder=self.settings.value('saving/storage_folder')
        le=QtWidgets.QLineEdit()
        le.setText(storage_folder)

        va.addWidget(le)
        va.addLayout(ha)
        va.addStretch()
        button=QtWidgets.QPushButton(self)
        button.setText('Choose')

        button.clicked.connect(self.chooseSaveFolder)
        ha.addWidget(button)


        return scroll


    def chooseSaveFolder(self):
        fname=QtWidgets.QFileDialog.getExistingDirectory(self,
            'Choose a folder to save documents and database')
        print('# <chooseSaveFolder>: fname=',fname)

        if fname:
            newf=self.settings.value('saving/storage_folder')
            print('# <chooseFont>: Folder after change:', newf)

        # TODO: apply change to database and meta_dict

        return


    def loadExportOptions(self,title):

        scroll, va=self.createFrame(title)

        return scroll

    def loadCitationStyleOptions(self,title):

        scroll, va=self.createFrame(title)

        return scroll







