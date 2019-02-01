import os
from datetime import datetime
import operator
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon, QFont, QFontMetrics,\
        QCursor, QRegExpValidator
import resources
from lib import sqlitedb
from .tools import getHLine, getXExpandYMinSizePolicy




class TreeWidgetDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None):
        QtWidgets.QItemDelegate.__init__(self, parent=parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        reg=QtCore.QRegExp('[A-z0-9\[\]_-\s]+')
        vd=QRegExpValidator(reg)
        editor.setValidator(vd)
        return editor



class MyTreeWidget(QtWidgets.QTreeWidget):

    folder_move_signal=pyqtSignal(tuple)
    folder_del_signal=pyqtSignal((QtWidgets.QTreeWidgetItem,bool))

    def __init__(self,parent=None):
        super(MyTreeWidget,self).__init__(parent=parent)

        self._trashed_folders=[]


    def startDrag(self,actions):
        print('startDrag:, actions:', actions)

        move_item=self.selectedItems()[0]
        print('startDrag: move_item:',move_item.data(0,0),move_item.data(1,0))
        self._move_item=move_item

        super(MyTreeWidget,self).startDrag(actions)

    def dropEvent(self,event):
        print('MyTreeWidget.dropevent:',event)

        pos=event.pos()
        newparent=self.itemAt(pos)
        parentidx=self.indexFromItem(newparent)
        indicatorpos=self.dropIndicatorPosition()
        print('dropEvent, parentidx',parentidx,parentidx.row(),self.indexAt(pos).row())
        print('dropEvent: newparent=',newparent,newparent.data(0,0))
        print('dropEvent: proposedAction=',event.proposedAction())
        print('dropEvent, dropIndicatorPosition',indicatorpos)

        # on item
        if indicatorpos==0:

            # get children
            children=[newparent.child(ii) for ii in range(newparent.childCount())]
            children_names=[ii.data(0,0) for ii in children]
            print('dropEvent:, children:',children)
            print('dropEvent:, children_names:',children_names)

            print('dropevent, check target folder',\
                    self._trashed_folders, newparent.data(1,0))

            if newparent.data(0,0) in ['All', 'Needs Review']:
                event.ignore()
                return

            elif newparent.data(1,0) in ['-3']+self._trashed_folders:
                choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                        'Deleting a folder will delete all sub-folders and documents inside.\n\nConfirm?',
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

                if choice==QtWidgets.QMessageBox.Yes:
                    self._trashed_folders.append(self._move_item.data(1,0))
                    print('dropEvent: add folder id to trashed_folders',self._trashed_folders)
                    self.folder_del_signal.emit(self._move_item,False)
                    super(MyTreeWidget,self).dropEvent(event)
                    return
                else:
                    event.ignore()
                    return

            if self._move_item.data(0,0) in children_names:
                print('dropEvent: name conflict')
                event.ignore()
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle('Name conflict')
                msg.setText('Move cancelled due to name conflict.')
                msg.setInformativeText('Folder name\n\t%s\nconflicts with another folder in the target folder.\nPlease rename before moving.' %self._move_item)
                msg.exec_()
                return
            else:
                self.folder_move_signal.emit((self._move_item.data(1,0),\
                        newparent.data(1,0)))
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
    def __init__(self, parent, datain, headerdata):
        QAbstractTableModel.__init__(self, parent)

        self.ncol=len(headerdata)
        if datain is None:
            self.arraydata=[None]*self.ncol
        else:
            self.arraydata=datain
        self.headerdata=headerdata

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
                    | QtCore.Qt.ItemIsUserCheckable
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


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


class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)

        self.colSizes={'docid':0, 'favourite': 20, 'read': 20, 'has_file': 20,
            'author': 200, 'title': 500, 'journal':100,'year':50,'added':50}

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
        print('resize', total_w, total_w2)
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

    edited_signal=pyqtSignal()
    def __init__(self,parent=None):
        super(AdjustableTextEdit,self).__init__(parent)

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
            self.edited_signal.emit()
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
    def __init__(self,parent=None):
        super(AdjustableTextEditWithFold,self).__init__(parent)

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

    meta_edited=pyqtSignal()
    def __init__(self,font_dict,parent=None):
        super(MetaTabScroll,self).__init__(parent)

        self.font_dict=font_dict
        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.label_font=QFont('Serif',12,QFont.Bold)

        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        self.setWidgetResizable(True)
        self.setWidget(frame)
        self.fields_dict={}  # key: field name, value: textedit or lineedit

        #-------------------Add widgets-------------------
        self.v_layout=QtWidgets.QVBoxLayout()

        #--------------------Add title--------------------
        title_te=AdjustableTextEdit()
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
        self.createMultiLineField('Keywords','keywords_l','meta_keywords')

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
        print('MetaTabScroll: number of widgets in v_layout',self.v_layout.count())

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


    def fieldEdited(self):
        print('fieldedited')
        print(self._meta_dict)
        self.meta_edited.emit()

    def createLabel(self,label):
        qlabel=QtWidgets.QLabel(label)
        qlabel.setStyleSheet(self.label_color)
        qlabel.setFont(self.label_font)
        return qlabel


    def createOneLineField(self,label,key,font_name,grid_layout):
        te=AdjustableTextEdit()
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
        te=AdjustableTextEditWithFold()
        te.setFrameStyle(QtWidgets.QFrame.NoFrame)

        if font_name in self.font_dict:
            te.setFont(self.font_dict[font_name])

        if key=='authors_l':
            te.label_enabled=True
            te.tooltip_text='firstname, lastname\nfirstname, lastname\n...'
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

        return

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

        print('createFileField: insert at',self.file_insert_idx)
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
                print('delFileField',leii,self.file_insert_idx)
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
            print('addFileButtonClicked: new file', fname)
            self.createFileField(fname)
            self.fieldEdited()

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

        def parseAuthors(textlist):
            firstnames=[]
            lastnames=[]
            for nii in textlist:
                nii=nii.split(',',1)
                firstnames.append(nii[0] if len(nii)>1 else '')
                lastnames.append(nii[1] if len(nii)>1 else nii[0])
            authors=sqlitedb.zipAuthors(firstnames,lastnames)

            return firstnames,lastnames,authors



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
            print('MetaDataEntryDialog.showEvent:, enabled')
        else:
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
            print('MetaDataEntryDialog.showEvent:, disabled')

    def showEvent(self,e):
        if not self.initialized:
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
            print('MetaDataEntryDialog.showEvent:, disabled')
            self.initialized=True

        self.scroll.fields_dict['title'].setFocus()
        super(MetaDataEntryDialog,self).showEvent(e)
        return

    def exec_(self):
        ret=super(MetaDataEntryDialog,self).exec_()
        return ret, self.scroll._meta_dict







