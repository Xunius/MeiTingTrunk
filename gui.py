import sys,os
import operator
import sqlite3
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, QSettings
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor
#import tempfile
#import subprocess
import json
from lib import sqlitedb

__version__='v0.1'

FILE_IN='new.sqlite'






def dirFind(string,obj,num=10,verbose=True):
    '''Fuzzy search dir(obj)

    <string>: string, keyword to search.
    <obj>: python obj other than None.
    <num>: int, number of best matches to display.

    Function takes the keyword and compares it with the strings in dir(obj).
    Comparison is done using Levenshtein distance algorithm implemented in
    the fuzzywuzzy module.

    Usage:

    To show all get functions of an instance:
        dirFind('get',inst)

    Update time: 2016-02-11 13:09:14.
    '''

    import numpy
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        from fuzzywuzzy import fuzz

    dirlist=numpy.array(dir(obj))
    scores=numpy.array([fuzz.partial_ratio(string,ii) for ii in dirlist])
    idx=numpy.argsort(scores)[::-1]
    dirlist=dirlist[idx]
    scores=numpy.sort(scores)[::-1]

    #----Make sure all highly matched are included----
    high=numpy.where(scores>=90)[0]

    num=max([num,len(high)])

    print('\n# <dirFind>: %-20.40s    %s' %('<obj> element:','Score:'))
    print('-'*70)
    for ii in range(num):
        print('# <dirFind>: %-20.40s    %d' %(dirlist[ii],scores[ii]))

    return

def getMinSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum)
    return sizePolicy

def getXMinYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy

def getXExpandYMinSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum)
    return sizePolicy

def getXExpandYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy

def getHSpacer():
    h_spacer = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum)
    return h_spacer

def getVSpacer():
    v_spacer = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
    return v_spacer

def getVLine(parent):
    v_line = QtWidgets.QFrame(parent)
    v_line.setFrameShape(QtWidgets.QFrame.VLine)
    v_line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return v_line

def getHLine(parent):
    h_line = QtWidgets.QFrame(parent)
    h_line.setFrameShape(QtWidgets.QFrame.HLine)
    h_line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return h_line


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
                'favourite': QPixmap('./bf.jpg'),
                'read': QPixmap('./read.jpg')
                }
        self.icon_sec_indices=[self.headerdata.index(kk) for kk
                in self.icon_section.keys()]
        print('icon sec',self.icon_sec_indices)

    def rowCount(self,p):
        return len(self.arraydata)

    def columnCount(self,p):
        #if len(self.arraydata)>0:
            #return len(self.arraydata[0])
        #return 0
        return self.ncol

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        if role == Qt.BackgroundRole:
            if index.row()%2==0:
                return QBrush(QColor(230,230,249))
        if role==Qt.DisplayRole:
            return QVariant(self.arraydata[index.row()][index.column()])
        if role==Qt.EditRole:
            return QVariant(self.arraydata[index.row()][index.column()])

        if index.column() in self.icon_sec_indices and role==Qt.CheckStateRole:
            if self.arraydata[index.row()][index.column()].isChecked():
                return Qt.Checked
            else:
                return Qt.Unchecked

        if role != Qt.DisplayRole:
            return QVariant()

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if index.column() in self.icon_sec_indices and role==Qt.CheckStateRole:
            if value == Qt.Checked:
                self.arraydata[index.row()][index.column()].setChecked(True)
            else:
                self.arraydata[index.row()][index.column()].setChecked(False)

        self.dataChanged.emit(index,index)
        return True

    def flags(self, index):
        if index.column() in self.icon_sec_indices:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable\
                    | QtCore.Qt.ItemIsUserCheckable
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


    def headerData(self, col, orientation, role):

        if col in self.icon_sec_indices:
            label=self.headerdata[col]
            if orientation==Qt.Horizontal and role==Qt.DecorationRole:
                return self.icon_section[label]
        else:
            if orientation==Qt.Horizontal and role==Qt.DisplayRole:
                return self.headerdata[col]
        return None

    def sort(self,col,order):
        self.layoutAboutToBeChanged.emit()
        self.arraydata=sorted(self.arraydata,key=operator.itemgetter(col))
        if order==Qt.DescendingOrder:
            self.arraydata.reverse()
        self.layoutChanged.emit()

class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)

        self.colSizes={'docid':0, 'favourite': 20, 'read': 20, 'author': 200, 'title': 500,
                'journal':100,'year':50}


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
                if lii in ['favourite','read']:
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
            if lii in ['favourite','read']:
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

class MyTextEdit(QtWidgets.QTextEdit):
    def __init__(self,parent=None):
        super(MyTextEdit,self).__init__(parent)

        self.textChanged.connect(self.resizeTextEdit)

    #def sizeHint(self):
        #h=self.document().size().height()
        #w=self.document().size().width()
        #print 'sizehint', w,h
        #return QtCore.QSize(w,h)

    #def resizeEvent(self,event):
        #self.updateGeometry()
        #super(QtWidgets.QTextEdit,self).resizeEvent(event)

    def resizeTextEdit(self):
        #h=self.sizeHint()
        docheight=self.document().size().height()+10
        #print sender.toPlainText()
        self.setMinimumHeight(docheight)
        self.setMaximumHeight(docheight+10)
        #self.resize(self.width(),docheight)
        print('hei',docheight)
        print('h',self.height())
        #super(QtWidgets.QHeaderView, self).resizeEvent(event)
        #self.updateGeometry()

class MainFrame(QtWidgets.QWidget):

    def __init__(self,db,meta,folder_data,folder_dict,settings):
        super(MainFrame,self).__init__()

        self.db=db
        self.meta=meta
        self.folder_data=folder_data
        self.folder_dict=folder_dict
        self.inv_folder_dict={v[0]:k for k,v in self.folder_dict.items()}
        self.settings=settings

        # get font configs
        self.font_dict={
            'meta_title': self.settings.value('display/fonts/meta_title',QFont),
            'meta_authors': self.settings.value('display/fonts/meta_authors',QFont),
            'meta_publication': self.settings.value('display/fonts/meta_publication',QFont),
            'meta_keywords': self.settings.value('display/fonts/meta_keywords',QFont)
            }



        #self.thumbnail_meta_list=thumbnail_meta_list
        #self.thumbnail_btn_dict={}    # buttons for preset icons

        #-----Try load previous session and favorites-----
        #self.loadHistory()

        #-------------------Button holders-------------------
        #self.history_btn_dict={}
        #self.history_btn_list=[]
        #self.favorite_btn_dict={}
        #self.favorite_btn_list=[]
        #self.tab_btn_dict={}

        self.initUI()

        #--------------------Load data--------------------
        self.loadLibTree()
        self.loadDocTable(None)

        self.show()


    def initUI(self):

        v_layout0=QtWidgets.QVBoxLayout(self)

        #-------------------Tool bar row-------------------
        h_layout0=QtWidgets.QHBoxLayout()
        v_layout0.addLayout(h_layout0)

        # Add button
        self.add_button=QtWidgets.QToolButton(self)
        self.add_button.setText('Add')
        self.add_button.setIcon(QIcon.fromTheme('list-add'))
        #self.add_button.setIcon(QIcon.fromTheme('edit-undo'))
        self.add_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.add_button.clicked.connect(self.add_button_clicked)
        h_layout0.addWidget(self.add_button)

        h_layout0.addStretch()

        # seach bar
        self.search_bar=QtWidgets.QLineEdit(self)
        self.search_bar.setText('Type to search')

        self.search_bar.setFixedWidth(280)
        self.search_bar.setSizePolicy(getMinSizePolicy())
        self.search_bar.returnPressed.connect(self.search_bar_pressed)

        h_layout0.addWidget(self.search_bar)

        #-------------Add hline below tool bar-------------
        v_layout0.addWidget(getHLine(self))

        #-------------------Add lib tree-------------------
        self.libtree=self.addLibTree()

        h_split=QtWidgets.QSplitter(Qt.Horizontal)
        h_split.setSizePolicy(getXExpandYExpandSizePolicy())
        v_split=QtWidgets.QSplitter(Qt.Vertical)
        v_split.addWidget(self.libtree)
        v_layout0.addWidget(h_split)

        #----------------Add filter window----------------
        self.filter_list=QtWidgets.QTextEdit(self)
        v_split.addWidget(self.filter_list)
        h_split.addWidget(v_split)

        v_split.setSizes([3,1])

        #------------------Add doc table------------------
        self.doc_table=self.createDocTable()
        h_split.addWidget(self.doc_table)

        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()
        h_split.addWidget(self.tabs)

        #------------------Add status bar------------------
        self.status_bar=QtWidgets.QStatusBar()
        v_layout0.addWidget(self.status_bar)
        self.status_bar.showMessage('etest')

        h_split.setHandleWidth(10)
        w=h_split.size().width()
        h_split.setSizes([w*0.15,w*0.6,w*0.25])

        self.show()


    def createDocTable(self):

        tv=QtWidgets.QTableView(self)

        hh=MyHeaderView(self)
        hh.setSectionsClickable(True)
        hh.setHighlightSections(True)
        hh.sectionResized.connect(hh.myresize)
        hh.setStretchLastSection(False)

        tv.setHorizontalHeader(hh)
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        tv.setSortingEnabled(True)
        hh.setSectionsMovable(True)

        header=['docid', 'favourite','read','author', 'title','journal','year']
        tablemodel=TableModel(self,[],header)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True)

        #tv.itemSelectionChanged.connect
        tv.selectionModel().currentChanged.connect(self.selDoc)

        return tv


    def selDoc(self,current,previous):
        rowid=current.row()
        docid=self.tabledata[rowid][0]
        self.loadMetaTab(docid)






    def addLibTree(self):

        libtree=QtWidgets.QTreeWidget()
        libtree.setHeaderHidden(True)
        libtree.setColumnCount(1)
        libtree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        libtree.itemClicked.connect(self.clickSelFolder)
        libtree.selectionModel().selectionChanged.connect(self.selFolder)

        return libtree

    def loadLibTree(self):
        #-------------Get all level 1 folders-------------
        folders1=[(vv[0],kk) for kk,vv in self.folder_dict.items() if vv[1]<=0]
        folders1.sort()

        allitem=QtWidgets.QTreeWidgetItem(['All'])
        self.libtree.addTopLevelItem(allitem)

        for fnameii,idii in folders1:
            self.addFolder(self.libtree,idii,self.folder_dict)
        
        #self.libtree.setCurrentItem(allitem)
        return 

    def addFolder(self,parent,folderid,folder_dict):

        foldername,parentid=folder_dict[folderid]
        fitem=QtWidgets.QTreeWidgetItem([foldername])
        sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
        if parentid<=0:
            parent.addTopLevelItem(fitem)
        else:
            parent.addChild(fitem)
        if len(sub_ids)>0:
            for sii in sub_ids:
                self.addFolder(fitem,sii,folder_dict)

        return

    def clickSelFolder(self,item,column):
        '''Select folder by clicking'''
        folder=item.text(column)
        self.status_bar.showMessage('Select folder %s' %folder)
        if folder=='All':
            folder=None
        self.loadDocTable(folder)


    def selFolder(self,selected,deselected):
        '''Select folder by changing current'''
        item=self.libtree.selectedItems()
        if item:
            item=item[0]
            print('item', item)
            print(item.data(0,0))
            column=selected.indexes()[0].column()
            self.clickSelFolder(item,column)


    def createTabs(self):
        def _createPage():
            scroll=QtWidgets.QScrollArea(self)
            frame=QtWidgets.QWidget()
            v_layout=QtWidgets.QVBoxLayout()
            frame.setLayout(v_layout)
            scroll.setWidget(frame)
            return scroll

        tabs=QtWidgets.QTabWidget()
        #self.t_meta=_createPage()
        self.t_notes=_createPage()
        self.t_topics=_createPage()
        self.t_scratchpad=_createPage()

        self.t_meta=self.createMetaTab()

        tabs.addTab(self.t_meta,'Meta Data')
        tabs.addTab(self.t_notes,'Notes')
        tabs.addTab(self.t_topics,'Topics')
        tabs.addTab(self.t_scratchpad,'Strach Pad')


        return tabs

    def createMetaTab(self):
        
        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        v_layout=QtWidgets.QVBoxLayout()

        fields_dict={}

        #--------------------Add title--------------------
        lineii=QtWidgets.QTextEdit()
        lineii.setFrameStyle(QtWidgets.QFrame.NoFrame)
        lineii.textChanged.connect(self.resizeTextEdit)
        lineii.setFont(self.font_dict['meta_title'])
        fields_dict['title']=lineii
        v_layout.addWidget(lineii)

        #-------------------Add authors-------------------
        lineii=QtWidgets.QTextEdit()
        lineii.setFrameStyle(QtWidgets.QFrame.NoFrame)
        lineii.textChanged.connect(self.resizeTextEdit)
        lineii.setFont(self.font_dict['meta_authors'])
        fields_dict['authors']=lineii

        hlayout=QtWidgets.QHBoxLayout()
        labelii=QtWidgets.QLabel('Authors')
        hlayout.addWidget(labelii)
        hlayout.addWidget(lineii)
        v_layout.addLayout(hlayout)

        #-----Add journal, year, volume, issue, pages-----
        for fii in ['publication','year','volume','issue','pages']:
            hlayout=QtWidgets.QHBoxLayout()
            lineii=QtWidgets.QTextEdit()
            labelii=QtWidgets.QLabel(fii)
            lineii.textChanged.connect(self.resizeTextEdit)

            if 'meta_%s' %fii in self.font_dict:
                lineii.setFont(self.font_dict['meta_%s' %fii])

            hlayout.addWidget(labelii)
            hlayout.addWidget(lineii)
            v_layout.addLayout(hlayout)
            fields_dict[fii]=lineii

        #-------------------Add keywords-------------------
        lineii=QtWidgets.QTextEdit()
        lineii.setFrameStyle(QtWidgets.QFrame.NoFrame)
        lineii.textChanged.connect(self.resizeTextEdit)
        lineii.setFont(self.font_dict['meta_keywords'])
        fields_dict['keywords']=lineii

        labelii=QtWidgets.QLabel('Keywords')
        labelii.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(labelii)
        v_layout.addWidget(lineii)

        v_layout.addStretch()
        frame.setLayout(v_layout)
        scroll.fields_dict=fields_dict

        return scroll


    def resizeTextEdit(self):
        sender=self.sender()
        sender.update()
        docheight=sender.document().size().height()+3
        docheight2=sender.sizeHint().height()+10
        sender.setMinimumHeight(docheight)
        sender.setMaximumHeight(docheight+1)
        print('sender',sender,'docheight',docheight,'sizehint',docheight2, sender.height())
        #print sender.toPlainText()
        #sender.updateGeometry()


    def loadMetaTab(self,docid=None):
        print('loadMetaTab',docid)
        if docid is None:
            return

        #fields=['title','authors','publication','year','month','keywords']
        fields=['title','authors','publication','year','volume','issue',
                'pages','keywords']

        metaii=self.meta[docid]
        def deu(text):
            #if isinstance(text,(str,unicode)):
            if isinstance(text,(str)):
                return text
            else:
                return str(text)

        for fii in fields:
            tii=metaii[fii]
            if tii is None:
                continue
            if isinstance(tii,(list,tuple)):
                tii=u'; '.join(tii)
            self.t_meta.fields_dict[fii].setText(deu(tii))

        return 





    def loadDocTable(self,folder=None):
        '''Load doc table given folder'''

        tablemodel=self.doc_table.model()
        #hh=self.doc_table.horizontalHeader()
        print('load tabel', folder)

        def prepareDocs(docids):
            data=[]
            for ii in docids:
                entryii=self.meta[ii]

                first=entryii['firstNames']
                last=entryii['lastName']
                if first is None or last is None:
                    authors=''
                if type(first) is not list and type(last) is not list:
                    authors='%s, %s' %(last, first)
                else:
                    authors=['%s, %s' %(jj[0],jj[1]) for jj in zip(last,first)]
                    authors=' and '.join(authors)

                aii=[ii,
                    QtWidgets.QCheckBox(entryii['favourite']),
                    QtWidgets.QCheckBox(entryii['read']),
                    authors,
                    entryii['title'],
                    entryii['publication'],
                    entryii['year']]
                data.append(aii)

            return data

        if folder is None:
            docids=self.meta.keys()
            data=prepareDocs(docids)
        else:
            folderid=self.inv_folder_dict[folder]
            if folderid in self.folder_data:
                docids=self.folder_data[folderid]
                data=prepareDocs(docids)
            else:
                data=[]


        if len(data)==0:
            return

        print('num in folder',len(docids))
        tablemodel.arraydata=data
        tablemodel.sort(4,Qt.AscendingOrder)
        self.tabledata=tablemodel.arraydata

        self.doc_table.selectRow(0)
        current_row=self.doc_table.currentIndex().row()
        docid=self.tabledata[current_row][0]
        print('current_row',current_row, docid)
        print(self.tabledata[current_row])
        self.loadMetaTab(docid)




    def add_button_clicked(self):
        print('add')

    def search_bar_pressed(self):
        print('search term:', self.search_bar.text())

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self,db):
        super(MainWindow,self).__init__()

        self.db=db
        meta,folder_data,folder_dict=sqlitedb.readSqlite(db)
        self.settings=self.loadSettings()

        self.initUI()

        self.main_frame=MainFrame(db,meta,folder_data,folder_dict,self.settings)
        self.setCentralWidget(self.main_frame)

    def initSettings(self):
        folder_name=os.path.dirname(os.path.abspath(__file__))
        settings_path=os.path.join(folder_name,'settings.ini')

        if not os.path.exists(settings_path):
            settings=QSettings(settings_path,QSettings.IniFormat)

            settings.setValue('display/fonts/meta_title',
                QFont('Times', 14, QFont.Bold | QFont.Capitalize))
            settings.setValue('display/fonts/meta_authors',
                QFont('Serif', 12))
            settings.setValue('display/fonts/meta_publication',
                QFont('Times', 10, QFont.StyleItalic))
            settings.setValue('display/fonts/meta_keywords',
                QFont('Times', 10, QFont.StyleItalic))

            settings.sync()

        else:
            settings=QSettings(settings_path,QSettings.IniFormat)

        return settings

    def loadSettings(self):
        settings=self.initSettings()
        print(settings.fileName())

        aa=settings.value('display/fonts/meta_title')
        print('settings',settings)
        print('fonat',aa)

        return settings


    def initUI(self):
        self.setWindowTitle('Reference manager %s' %__version__)
        self.setGeometry(100,100,1200,900)    #(x_left,y_top,w,h)
        #self.setWindowIcon(QIcon('img.png'))
        self.menu_bar=self.menuBar()
        self.file_manu=self.menu_bar.addMenu('File')
        self.edit_manu=self.menu_bar.addMenu('Edit')
        self.view_manu=self.menu_bar.addMenu('View')
        self.tool_manu=self.menu_bar.addMenu('Tool')
        self.help_manu=self.menu_bar.addMenu('Help')

        self.show()

    def closeEvent(self,event):
        self.settings.sync()




if __name__=='__main__':

    abpath_in=os.path.abspath(FILE_IN)
    try:
        dbin = sqlite3.connect(abpath_in)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    app=QtWidgets.QApplication(sys.argv)
    mainwindow=MainWindow(dbin)
    sys.exit(app.exec_())
