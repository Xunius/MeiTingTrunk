import sys,os
import operator
import sqlite3
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QVariant, QSettings
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor, QFontMetrics
from lib import sqlitedb
from lib import export2bib
from lib.tools import getMinSizePolicy, getXMinYExpandSizePolicy,\
        getXExpandYMinSizePolicy, getXExpandYExpandSizePolicy, getHSpacer, \
        getVSpacer, getHLine, getVLine

from lib.widgets import TableModel, MyHeaderView, MyTextEdit


__version__='v0.1'

FILE_IN='new.sqlite'


# TODO:
# show docs in sub folders?
# fold long fields in meta data tab?
# create bib texts when clicking into the bibtex tab and changing doc
# add icons to folders


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self,db):
        super(MainWindow,self).__init__()

        self.db=db
        meta_dict,folder_data,folder_dict=sqlitedb.readSqlite(db)
        self.settings=self.loadSettings()

        self.initUI()

        self.main_frame=MainFrame(db,meta_dict,folder_data,folder_dict,self.settings)
        self.setCentralWidget(self.main_frame)

    def initSettings(self):
        folder_name=os.path.dirname(os.path.abspath(__file__))
        settings_path=os.path.join(folder_name,'settings.ini')

        if not os.path.exists(settings_path):
            settings=QSettings(settings_path,QSettings.IniFormat)

            settings.setValue('display/fonts/meta_title',
                QFont('Serif', 15, QFont.Bold | QFont.Capitalize))
            settings.setValue('display/fonts/meta_authors',
                QFont('Serif', 12))
            settings.setValue('display/fonts/meta_keywords',
                QFont('Times', 12, QFont.StyleItalic))
            settings.setValue('display/folder/highlight_color_br',
                    QBrush(QColor(200,200,255)))

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


class MainFrame(QtWidgets.QWidget):

    def __init__(self,db,meta_dict,folder_data,folder_dict,settings):
        super(MainFrame,self).__init__()

        self.db=db
        self.meta_dict=meta_dict
        self.folder_data=folder_data
        self.folder_dict=folder_dict
        self.inv_folder_dict={v[0]:k for k,v in self.folder_dict.items()}
        self.settings=settings

        # get font configs
        self.font_dict={
            'meta_title': self.settings.value('display/fonts/meta_title',QFont),
            'meta_authors': self.settings.value('display/fonts/meta_authors',QFont),
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
        #self.loadDocTable(None)


    def initUI(self):

        v_layout0=QtWidgets.QVBoxLayout(self)

        #-------------------Tool bar row-------------------
        h_layout0=QtWidgets.QHBoxLayout()
        v_layout0.addLayout(h_layout0)

        # Add button
        self.add_button=QtWidgets.QToolButton(self)
        self.add_button.setText('Add')
        self.add_button.setIcon(QIcon.fromTheme('edit-undo'))

        for pp in QIcon.themeSearchPaths():
            print('pp',pp,QIcon.themeName())

        #self.add_button.setIcon(QtWidgets.QApplication.style().standardIcon(
            #QtWidgets.QStyle.SP_FileIcon))
        self.add_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.add_button.clicked.connect(self.addDocButtonClicked)
        h_layout0.addWidget(self.add_button)

        h_layout0.addStretch()

        # seach bar
        self.search_bar=QtWidgets.QLineEdit(self)
        self.search_bar.setText('Type to search')

        self.search_bar.setFixedWidth(280)
        self.search_bar.setSizePolicy(getMinSizePolicy())
        self.search_bar.returnPressed.connect(self.searchBarClicked)

        h_layout0.addWidget(self.search_bar)

        #-------------Add hline below tool bar-------------
        v_layout0.addWidget(getHLine(self))

        #-------------------Add lib tree-------------------
        self.libtree=self.createLibTree()

        h_split=QtWidgets.QSplitter(Qt.Horizontal)
        h_split.setSizePolicy(getXExpandYExpandSizePolicy())
        v_split=QtWidgets.QSplitter(Qt.Vertical)
        v_split.addWidget(self.libtree)
        v_layout0.addWidget(h_split)

        #----------------Add filter window----------------
        #self.filter_list=QtWidgets.QTextEdit(self)
        filter_scroll=self.createFilterList()
        v_split.addWidget(filter_scroll)
        h_split.addWidget(v_split)

        v_split.setSizes([3,1])
        h=v_split.size().height()
        v_split.setSizes([h*0.65,h*0.35])

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


    def createFilterList(self):
        frame=QtWidgets.QFrame()
        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        v_layout=QtWidgets.QVBoxLayout()

        self.filter_type_combbox=QtWidgets.QComboBox(self)
        self.filter_type_combbox.addItem('Filter by authors')
        self.filter_type_combbox.addItem('Filter by keywords')
        self.filter_type_combbox.addItem('Filter by publications')
        self.filter_type_combbox.addItem('Filter by tags')
        self.filter_type_combbox.currentIndexChanged.connect(
                self.filterTypeCombboxChange)
        self.filter_type_combbox.setSizeAdjustPolicy(
                QtWidgets.QComboBox.AdjustToMinimumContentsLength)

        self.filter_item_list=QtWidgets.QListWidget(self)

        v_layout.addWidget(self.filter_type_combbox)
        v_layout.addWidget(self.filter_item_list)

        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll

    def filterTypeCombboxChange(self,item):
        sel=self.filter_type_combbox.currentText()
        current_folder=self.libtree.selectedItems()
        print('filter type cb select:',sel)
        if current_folder:
            current_folder=current_folder[0]
            print('filtertypecombochange: currentfolder:',\
                    current_folder.data(0,0), current_folder.data(1,0))

            #---------------Get items in folder---------------
            foldername=current_folder.data(0,0)
            folderid=current_folder.data(1,0)
            if foldername=='All' and folderid=='0':
                docids=list(self.meta_dict.keys())
            else:
                docids=self.folder_data[current_folder.data(1,0)]

            if sel=='Filter by keywords':
                folderdata=fetchMetaData(self.meta_dict,'keywords',docids,
                        unique=True,sort=True)
            elif sel=='Filter by authors':
                firsts=fetchMetaData(self.meta_dict,'firstNames',docids,
                        unique=False,sort=False)
                last=fetchMetaData(self.meta_dict,'lastName',docids,
                        unique=False,sort=False)
                folderdata=['%s, %s' %(last[ii],firsts[ii]) for ii in range(len(firsts))]
                folderdata.sort()
            elif sel=='Filter by publications':
                folderdata=fetchMetaData(self.meta_dict,'publication',docids,
                        unique=True,sort=True)
            elif sel=='Filter by tags':
                folderdata=fetchMetaData(self.meta_dict,'tags',docids,
                        unique=True,sort=True)

            print('filterTypeCombboxChange: folderdata',folderdata)

        self.filter_item_list.clear()
        self.filter_item_list.addItems(folderdata)

        return






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
        '''Actions on selecting a document in doc table
        '''
        rowid=current.row()
        docid=self.tabledata[rowid][0]
        self.loadMetaTab(docid)
        self.loadBibTab(docid)

        #-------------------Get folders-------------------
        metaii=self.meta_dict[docid]
        folders=metaii['folder']
        folders=[fii[1] for fii in folders]
        print('folders of docid', folders, docid)

        def iterItems(treewidget, root):
            if root is not None:
                stack = [root]
                while stack:
                    parent = stack.pop(0)
                    for row in range(parent.childCount()):
                        child = parent.child(row)
                        yield child
                        if child.childCount()>0:
                            stack.append(child)

        #------------Remove highlights for all------------
        ori_color=QBrush(QColor(255,255,255))
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        root=self.libtree.invisibleRootItem()
        for item in iterItems(self.libtree, root):
            item.setBackground(0, ori_color)

        #------------Search folders in libtree------------
        for fii in folders:
            mii=self.libtree.findItems(fii, Qt.MatchExactly | Qt.MatchRecursive)
            if len(mii)>0:
                for mjj in mii:
                    mjj.setBackground(0, hi_color)



    def createLibTree(self):

        libtree=QtWidgets.QTreeWidget()
        libtree.setHeaderHidden(True)
        # column1: folder name, column2: folder id
        libtree.setColumnCount(2)
        libtree.hideColumn(1)
        libtree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        libtree.itemClicked.connect(self.clickSelFolder)
        libtree.selectionModel().selectionChanged.connect(self.selFolder)

        return libtree

    def loadLibTree(self):

        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)

        #-------------Get all level 1 folders-------------
        folders1=[(vv[0],kk) for kk,vv in self.folder_dict.items() if\
                vv[1]=='0' or vv[1]=='-1']
        folders1.sort()

        allitem=QtWidgets.QTreeWidgetItem(['All','0'])
        allitem.setIcon(0,diropen_icon)
        self.libtree.addTopLevelItem(allitem)

        for fnameii,idii in folders1:
            addFolder(self.libtree,idii,self.folder_dict)
        
        self.libtree.setCurrentItem(allitem)
        return 


    def clickSelFolder(self,item,column):
        '''Select folder by clicking'''
        folder=item.data(0,0)
        folderid=item.data(1,0)
        #folder=item.text(column)
        #print('clickSelfolder:', 'item.data', item.data(0,0), item.data(1,0), 'colunm', column)
        self.status_bar.showMessage('Select folder %s, id: %s' %(folder, folderid))
        if folder=='All' and folderid=='0':
            #folder=None
            self.loadDocTable(None)
        else:
            self.loadDocTable((folder,folderid))

        self.filterTypeCombboxChange(item)


    def selFolder(self,selected,deselected):
        '''Select folder by changing current'''
        item=self.libtree.selectedItems()
        if item:
            item=item[0]
            #print('selFolder:','item', item)
            #column=selected.indexes()[0].column()
            column=0
            #print('selFolder:',item.data(0,0), item.data(1,0))
            print('selFolder:','selected column', column)
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
        #self.t_notes=_createPage()
        self.t_notes=self.createNoteTab()
        #self.t_bib=_createPage()
        self.t_bib=self.createBiBTab()
        #self.t_scratchpad=_createPage()
        self.t_scratchpad=self.createScratchTab()

        self.t_meta=self.createMetaTab()

        tabs.addTab(self.t_meta,'Meta Data')
        tabs.addTab(self.t_notes,'Notes')
        tabs.addTab(self.t_bib,'Bibtex')
        tabs.addTab(self.t_scratchpad,'Strach Pad')


        return tabs


    def createNoteTab(self):

        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        frame=QtWidgets.QFrame()
        v_layout=QtWidgets.QVBoxLayout()

        '''
        label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        label=QtWidgets.QLabel('Notes associated with document')
        label.setStyleSheet(label_color)
        label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(label)
        '''

        self.note_textedit=QtWidgets.QTextEdit(self)
        self.note_textedit.setFont(self.font_dict['meta_keywords'])
        self.note_textedit.setSizePolicy(getXExpandYExpandSizePolicy())

        v_layout.addWidget(self.note_textedit)
        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll

    def createScratchTab(self):

        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        frame=QtWidgets.QFrame()
        v_layout=QtWidgets.QVBoxLayout()

        '''
        label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        label=QtWidgets.QLabel('Notes associated with document')
        label.setStyleSheet(label_color)
        label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(label)
        '''

        self.scratchpad_textedit=QtWidgets.QTextEdit(self)
        self.scratchpad_textedit.setFont(self.font_dict['meta_keywords'])
        self.scratchpad_textedit.setSizePolicy(getXExpandYExpandSizePolicy())

        v_layout.addWidget(self.scratchpad_textedit)
        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll



    def createBiBTab(self):

        frame=QtWidgets.QWidget()
        #frame.setStyleSheet('background-color:white')
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        v_layout=QtWidgets.QVBoxLayout()

        # buttons
        h_layout=QtWidgets.QHBoxLayout()

        self.copy_bib_button=QtWidgets.QToolButton(self)
        self.copy_bib_button.setText('Copy')
        self.copy_bib_button.setIcon(QIcon.fromTheme('edit-copy'))
        self.copy_bib_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        h_layout.addWidget(self.copy_bib_button)
        h_layout.addStretch()

        self.bib_textedit=QtWidgets.QTextEdit(self)
        self.bib_textedit.setFont(self.font_dict['meta_keywords'])
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.bib_textedit)
        frame.setLayout(v_layout)
        self.copy_bib_button.clicked.connect(self.copyBibButtonClicked)

        return scroll






    def createMetaTab(self):

        label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        
        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        v_layout=QtWidgets.QVBoxLayout()

        fields_dict={}

        def createOneLineField(label,key,font_name,field_dict):
            #hlayout=QtWidgets.QHBoxLayout()
            #lineii=QtWidgets.QTextEdit()
            lineii=MyTextEdit()
            labelii=QtWidgets.QLabel(label)
            labelii.setStyleSheet(label_color)
            #lineii.textChanged.connect(self.resizeTextEdit)

            if font_name in self.font_dict:
                lineii.setFont(self.font_dict[font_name])

            #hlayout.addWidget(labelii)
            #hlayout.addWidget(lineii)
            rnow=grid_layout.rowCount()
            grid_layout.addWidget(labelii,rnow,0)
            grid_layout.addWidget(lineii,rnow,1)
            #v_layout.addLayout(hlayout)
            fields_dict[key]=lineii

            return

        def createMultiLineField(label,key,font_name,field_dict):
            #lineii=QtWidgets.QTextEdit()
            lineii=MyTextEdit()
            lineii.setFrameStyle(QtWidgets.QFrame.NoFrame)
            #lineii.textChanged.connect(self.resizeTextEdit)
            lineii.setFont(self.font_dict[font_name])
            fields_dict[key]=lineii

            if len(label)>0:
                labelii=QtWidgets.QLabel(label)
                labelii.setStyleSheet(label_color)
                labelii.setFont(QFont('Serif',12,QFont.Bold))
                v_layout.addWidget(labelii)
            v_layout.addWidget(lineii)

            return


        #--------------------Add title--------------------
        createMultiLineField('','title','meta_title',fields_dict)
        v_layout.addWidget(getHLine(self))

        #-------------------Add authors-------------------
        createMultiLineField('Authors','authors','meta_authors',fields_dict)

        #-----Add journal, year, volume, issue, pages-----
        grid_layout=QtWidgets.QGridLayout()

        for fii in ['publication','year','volume','issue','pages','publisher',
                'citationkey']:
            createOneLineField(fii,fii,'meta_keywords',fields_dict)

        v_layout.addLayout(grid_layout)

        #---------------------Add tags---------------------
        createMultiLineField('Tags','tags','meta_keywords',fields_dict)
        createMultiLineField('Abstract','abstract','meta_keywords',fields_dict)
        createMultiLineField('Keywords','keywords','meta_keywords',fields_dict)
        createMultiLineField('Files','files','meta_keywords',fields_dict)

        v_layout.addStretch()
        frame.setLayout(v_layout)
        scroll.fields_dict=fields_dict

        return scroll




    def loadMetaTab(self,docid=None):
        print('loadMetaTab',docid)
        if docid is None:
            return

        #fields=['title','authors','publication','year','month','keywords']
        fields=['title','authors','publication','year','volume','issue',
                'pages','abstract','tags','keywords','citationkey','publisher',
                'files'
                ]

        metaii=self.meta_dict[docid]
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


    def loadBibTab(self,docid=None):
        print('loadBibTab',docid)
        if docid is None:
            return

        metaii=self.meta_dict[docid]
        #import bibtexparser
        #bb=bibtexparser.bibdatabase.BibDatabase()

        text=export2bib.parseMeta(metaii,'',metaii['folder'],True,False,
                True)

        self.bib_textedit.setText(text)

        return 







    def loadDocTable(self,folder=None):
        '''Load doc table given folder'''

        tablemodel=self.doc_table.model()
        #hh=self.doc_table.horizontalHeader()
        print('load tabel', folder)

        def prepareDocs(docids):
            data=[]
            for ii in docids:
                entryii=self.meta_dict[ii]

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
            docids=self.meta_dict.keys()
            data=prepareDocs(docids)
        else:
            folderid=self.inv_folder_dict[folder[0]]
            folderid2=folder[1]
            print('2 ways to get folder id, folderid = ',folderid, 'folderid2=',folderid2)
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




    def addDocButtonClicked(self):
        print('add')

    def searchBarClicked(self):
        print('search term:', self.search_bar.text())

    def copyBibButtonClicked(self):
        self.bib_textedit.selectAll()
        self.bib_textedit.copy()


def addFolder(parent,folderid,folder_dict):

    foldername,parentid=folder_dict[folderid]
    fitem=QtWidgets.QTreeWidgetItem([foldername,str(folderid)])
    style=QtWidgets.QApplication.style()
    diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
    fitem.setIcon(0,diropen_icon)
    sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
    if parentid=='0' or parentid=='-1':
        parent.addTopLevelItem(fitem)
    else:
        parent.addChild(fitem)
    if len(sub_ids)>0:
        for sii in sub_ids:
            addFolder(fitem,sii,folder_dict)

    return



def fetchMetaData(meta_dict,key,docids,unique,sort):
    if not isinstance(docids, (tuple,list)):
        docids=[docids,]

    result=[]
    for idii in docids:
        vv=meta_dict[idii].get(key,None)
        if vv:
            if isinstance(vv, (tuple,list)):
                result.extend(vv)
            else:
                result.append(vv)

    if unique:
        result=list(set(result))
    if sort:
        result.sort()

    return result



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
