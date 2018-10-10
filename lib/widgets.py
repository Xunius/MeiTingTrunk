from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon, QFont
import operator
import resources
from .tools import getHLine

class TableModel(QAbstractTableModel):
    def __init__(self, parent, datain, headerdata):
        QAbstractTableModel.__init__(self, parent)

        self.ncol=len(headerdata)
        if datain is None:
            self.arraydata=[None]*self.ncol
        else:
            self.arraydata=datain
        self.headerdata=headerdata

        print('resources:', resources)

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
            if index.column() not in self.icon_sec_indices:
                return QVariant(self.arraydata[index.row()][index.column()])
            else:
                return
        if role==Qt.EditRole:
            return QVariant(self.arraydata[index.row()][index.column()])

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
    def __init__(self,parent=None):
        super(AdjustableTextEdit,self).__init__(parent)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self.resizeTextEdit)
        self.document().documentLayout().documentSizeChanged.connect(
                self.resizeTextEdit)



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
            border: 1px solid #555;
            border-radius: %dpx;
            }

        QPushButton:pressed {
            border-style: inset;
            } 
        ''' %(int(font_height/2)))

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
        return

    def unfoldText(self):
        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)
        self.is_fold=False
        self.fold_button.setText('-')
        return



class MetaTabScroll(QtWidgets.QScrollArea):

    def __init__(self,font_dict,parent=None):
        super(MetaTabScroll,self).__init__(parent)

        self.font_dict=font_dict

        label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        
        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        #scroll=QtWidgets.QScrollArea()
        self.setWidgetResizable(True)
        self.setWidget(frame)
        v_layout=QtWidgets.QVBoxLayout()

        fields_dict={}

        def createOneLineField(label,key,font_name,field_dict,grid_layout):
            lineii=AdjustableTextEdit()
            labelii=QtWidgets.QLabel(label)
            labelii.setStyleSheet(label_color)

            if font_name in self.font_dict:
                lineii.setFont(self.font_dict[font_name])

            rnow=grid_layout.rowCount()
            grid_layout.addWidget(labelii,rnow,0)
            grid_layout.addWidget(lineii,rnow,1)
            fields_dict[key]=lineii

            return

        def createMultiLineField(label,key,font_name,field_dict):
            lineii=AdjustableTextEditWithFold()
            lineii.setFrameStyle(QtWidgets.QFrame.NoFrame)
            lineii.setFont(self.font_dict[font_name])
            fields_dict[key]=lineii

            h_layout=QtWidgets.QHBoxLayout()

            labelii=QtWidgets.QLabel(label)
            labelii.setStyleSheet(label_color)
            labelii.setFont(QFont('Serif',12,QFont.Bold))
            h_layout.addWidget(labelii)
            h_layout.addWidget(lineii.fold_button)

            v_layout.addLayout(h_layout)
            v_layout.addWidget(lineii)

            return


        #--------------------Add title--------------------
        title_te=AdjustableTextEdit()
        title_te.setFrameStyle(QtWidgets.QFrame.NoFrame)
        title_te.setFont(self.font_dict['meta_title'])
        fields_dict['title']=title_te
        v_layout.addWidget(title_te)

        v_layout.addWidget(getHLine(self))

        #-------------------Add authors-------------------
        createMultiLineField('Authors','authors','meta_authors',fields_dict)

        #-----Add journal, year, volume, issue, pages-----
        grid_layout=QtWidgets.QGridLayout()

        for fii in ['publication','year','volume','issue','pages',
                'citationkey']:
            createOneLineField(fii,fii,'meta_keywords',fields_dict,grid_layout)

        v_layout.addLayout(grid_layout)

        #---------------------Add tags---------------------
        createMultiLineField('Tags','tags','meta_keywords',fields_dict)

        #-------------------Add abstract-------------------
        createMultiLineField('Abstract','abstract','meta_keywords',fields_dict)

        #-------------------Add keywords-------------------
        createMultiLineField('Keywords','keywords','meta_keywords',fields_dict)

        #-----------------Add catalog ids-----------------
        labelii=QtWidgets.QLabel('Catalog IDs')
        labelii.setStyleSheet(label_color)
        labelii.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(labelii)

        grid_layout=QtWidgets.QGridLayout()

        for fii in ['arxivId','doi','issn','pmid']:
            createOneLineField(fii,fii,'meta_keywords',fields_dict,grid_layout)

        v_layout.addLayout(grid_layout)

        #--------------------Add files--------------------
        createMultiLineField('Files','files','meta_keywords',fields_dict)

        v_layout.addStretch()
        frame.setLayout(v_layout)

        self.fields_dict=fields_dict



class MetaDataEntryDialog(QtWidgets.QDialog):

    def __init__(self,font_dict,parent=None):
        super(MetaDataEntryDialog,self).__init__(parent)

        self.resize(500,700)
        self.setWindowTitle('Add New Entry')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()

        scroll=MetaTabScroll(font_dict,self)

        self.return_value=scroll.fields_dict

        self.buttons=QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        v_layout.addWidget(scroll)
        v_layout.addWidget(self.buttons)

        self.setLayout(v_layout)



    def exec_(self):
        super(MetaDataEntryDialog,self).exec_()
        return self.return_value







