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
# [y] create bib texts when clicking into the bibtex tab and changing doc
# [y] add icons to folders
# add a button to fold/unfold all fields in meta tab
# doc types, books, generic etc
# insert images to note?
# add folder functionality
# add add doc functionalities, by doi, bib, RIS
# import from Mendeley, zotero, Endnote?
# autosave, auto backup
# export to text (clipboard, styles), bibtex, ris.
# collapse side tab
# seperate libraries
# use resource file to load icons/images
# in note tab, add time stamps at left margin


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
                QFont('Serif', 14, QFont.Bold | QFont.Capitalize))
            settings.setValue('display/fonts/meta_authors',
                QFont('Serif', 11))
            settings.setValue('display/fonts/meta_keywords',
                QFont('Times', 11, QFont.StyleItalic))
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


        self.initUI()

        #--------------------Load data--------------------
        self.loadLibTree()


    def initUI(self):

        v_layout0=QtWidgets.QVBoxLayout(self)

        #-------------------Tool bar row-------------------
        h_layout0=QtWidgets.QHBoxLayout()
        v_layout0.addLayout(h_layout0)

        # Add button
        self.add_button=QtWidgets.QToolButton(self)
        self.add_button.setText('Add')
        self.add_button.setIcon(QIcon.fromTheme('edit-undo'))

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
        h_split.setCollapsible(2,True)
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
        frame=QtWidgets.QFrame()

        self.clear_filter_frame=QtWidgets.QFrame()
        h_la=QtWidgets.QHBoxLayout()
        h_la.addWidget(QtWidgets.QLabel('clear selection'))

        self.clear_filter_button=QtWidgets.QToolButton(self.clear_filter_frame)
        self.clear_filter_button.setText('Clear')
        self.clear_filter_button.clicked.connect(self.clearFilterButtonClicked)
        h_la.addWidget(self.clear_filter_button)

        self.clear_filter_frame.setLayout(h_la)
        self.clear_filter_frame.setVisible(False)

        v_la=QtWidgets.QVBoxLayout()
        v_la.addWidget(self.clear_filter_frame)

        self.doc_table=self.createDocTable()

        v_la.addWidget(self.doc_table)


        h_layout=QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0,0,0,0)
        h_layout.setSpacing(0)

        h_layout.addLayout(v_la)


        #--------------Add fold/unfold button--------------
        self.fold_tab_button=self.createFoldTabButton()

        #h_layout.addWidget(self.doc_table)
        h_layout.addWidget(self.fold_tab_button)
        frame.setLayout(h_layout)

        h_split.addWidget(frame)

        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()
        h_split.addWidget(self.tabs)

        #------------------Add status bar------------------
        self.status_bar=QtWidgets.QStatusBar()
        v_layout0.addWidget(self.status_bar)
        self.status_bar.showMessage('etest')

        h_split.setHandleWidth(4)
        w=h_split.size().width()
        h_split.setSizes([w*0.15,w*0.6,w*0.25])


        self.show()


    #######################################################################
    #                           Create widgets                            #
    #######################################################################



    def createLibTree(self):

        libtree=QtWidgets.QTreeWidget()
        libtree.setHeaderHidden(True)
        # column1: folder name, column2: folder id
        libtree.setColumnCount(2)
        libtree.hideColumn(1)
        libtree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        libtree.itemClicked.connect(self.clickSelFolder)
        libtree.selectionModel().selectionChanged.connect(self.selFolder)
        libtree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        libtree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        # make horziontal scroll bar appear
        libtree.header().setStretchLastSection(False)
        libtree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        return libtree



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
        self.filter_item_list.itemClicked.connect(self.filterItemClicked)

        v_layout.addWidget(self.filter_type_combbox)
        v_layout.addWidget(self.filter_item_list)

        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll



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

        header=['docid','favourite','read','has_file','author','title',
                'journal','year']
        tablemodel=TableModel(self,[],header)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True)

        tv.selectionModel().currentChanged.connect(self.selDoc)

        return tv


    def createFoldTabButton(self):
        button=QtWidgets.QToolButton(self)
        button.setArrowType(Qt.RightArrow)
        button.clicked.connect(self.foldTabButtonClicked)
        button.setFixedWidth(10)
        button.setFixedHeight(200)
        button.setStyleSheet(
                ''''border-radius: 0; border-width: 1px;
                border-style: solid; border-color:grey''')

        return button


    def createTabs(self):
        def _createPage():
            scroll=QtWidgets.QScrollArea(self)
            frame=QtWidgets.QWidget()
            v_layout=QtWidgets.QVBoxLayout()
            frame.setLayout(v_layout)
            scroll.setWidget(frame)
            return scroll

        tabs=QtWidgets.QTabWidget()
        self.t_notes=self.createNoteTab()
        self.t_bib=self.createBiBTab()
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
        self.bib_textedit.setReadOnly(True)
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




    #######################################################################
    #                        Load data to widgets                         #
    #######################################################################


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



    def loadDocTable(self,folder=None,docids=None):
        '''Load doc table given folder'''

        tablemodel=self.doc_table.model()
        #hh=self.doc_table.horizontalHeader()
        print('load tabel', folder)

        if docids is None:
            if folder is None:
                docids=self.meta_dict.keys()
                #data=prepareDocs(self.meta_dict,docids)
            else:
                folderid=folder[1]
                #if folderid in self.folder_data:
                docids=self.folder_data[folderid]
                #else:
                    #data=[]
            data=prepareDocs(self.meta_dict,docids)
        else:
            data=prepareDocs(self.meta_dict,docids)


        print('num in folder',len(docids))
        tablemodel.arraydata=data
        tablemodel.sort(4,Qt.AscendingOrder)
        self.tabledata=tablemodel.arraydata

        #------------Load meta data on 1st row------------
        if len(data)>0:
            self.doc_table.selectRow(0)
            current_row=self.doc_table.currentIndex().row()
            docid=self.tabledata[current_row][0]
            print('current_row',current_row, docid)
            print(self.tabledata[current_row])
            self.loadMetaTab(docid)
            self.enableMetaTab()
        else:
            # clear meta tab
            self.clearMetaTab()



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
            #self.t_meta.fields_dict[fii].setReadOnly(False)

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





    #######################################################################
    #                            Libtree slots                            #
    #######################################################################



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

        # Refresh filter list
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


    #######################################################################
    #                          Filter list slots                          #
    #######################################################################
    
    def filterItemClicked(self,item):

        print('filteritemclicked:, item:', item, item.text())
        filter_type=self.filter_type_combbox.currentText()
        filter_text=item.text()
        current_folder=self.libtree.selectedItems()
        if current_folder:
            folderid=current_folder[0].data(1,0)

            filter_docids=sqlitedb.filterDocs(self.meta_dict,self.folder_data,
                    filter_type,filter_text,folderid)

            if len(filter_docids)>0:
                self.loadDocTable(None,filter_docids)

            self.clear_filter_frame.setVisible(True)

        return

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
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'keywords',docids,
                        unique=True,sort=True)
            elif sel=='Filter by authors':
                firsts=sqlitedb.fetchMetaData(self.meta_dict,'firstNames',docids,
                        unique=False,sort=False)
                last=sqlitedb.fetchMetaData(self.meta_dict,'lastName',docids,
                        unique=False,sort=False)
                folderdata=['%s, %s' %(last[ii],firsts[ii]) for ii in range(len(firsts))]
                #folderdata=sqlitedb.getAuthors(self.meta_dict,docids)
            elif sel=='Filter by publications':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'publication',docids,
                        unique=True,sort=True)
            elif sel=='Filter by tags':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'tags',docids,
                        unique=True,sort=True)

        folderdata=list(set(folderdata))
        folderdata.sort()
        self.filter_item_list.clear()
        self.filter_item_list.addItems(folderdata)

        return




    #######################################################################
    #                           Doc table slots                           #
    #######################################################################
    

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






    #######################################################################
    #                            Meta tab slots                           #
    #######################################################################

    def clearMetaTab(self):
        for kk,vv in self.t_meta.fields_dict.items():
            vv.clear()
            vv.setReadOnly(True)

        for tii in [self.note_textedit, self.bib_textedit]:
            tii.clear()
            tii.setReadOnly(True)

        return

    def enableMetaTab(self):
        for kk,vv in self.t_meta.fields_dict.items():
            vv.setReadOnly(False)

        for tii in [self.note_textedit, ]:
            tii.setReadOnly(False)

        return



    
    #######################################################################
    #                             Other slots                             #
    #######################################################################
    

    def foldTabButtonClicked(self):
        #print('foldTabButtonClicked: is checked:', self.fold_tab_button.isChecked())
        #height=self.tabs.height()
        #self.tab_max_width=max(width,self.tab_max_width)
        #print('tabs width',width,'tab_max_width',self.tab_max_width)
        width=self.tabs.width()
        if width>0:
            #self.tabs.setMinimumWidth(0)
            #self.tabs.setMaximumWidth(0)
            #self.tabs.resize(0,height)
            self.tabs.setVisible(not self.tabs.isVisible())
            self.fold_tab_button.setArrowType(Qt.LeftArrow)
        else:
            #self.tabs.resize(self.tab_max_width,height)
            self.tabs.setVisible(not self.tabs.isVisible())
            self.fold_tab_button.setArrowType(Qt.RightArrow)
            #self.tabs.setMinimumWidth(self.tab_max_width)
            #self.tabs.setMaximumWidth(self.tab_max_width)
            #self.tabs.setFixedWidth(self.tab_max_width)
            #self.tabs.setFixedWidth(self.tabs.maximumWidth())
        return

    def clearFilterButtonClicked(self):

        self.clear_filter_frame.setVisible(False)

        current_folder=self.libtree.selectedItems()
        if current_folder:
            folderid=current_folder[0].data(1,0)
            folder=current_folder[0].data(0,0)

            if folder=='All' and folderid=='0':
                self.loadDocTable(None)
            else:
                self.loadDocTable((folder,folderid))

        return






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


def prepareDocs(meta_dict,docids):

    data=[]
    for ii in docids:
        entryii=meta_dict[ii]

        '''
        first=entryii['firstNames']
        last=entryii['lastName']
        if first is None or last is None:
            authors=''
        if type(first) is not list and type(last) is not list:
            authors='%s, %s' %(last, first)
        else:
            authors=['%s, %s' %(jj[0],jj[1]) for jj in zip(last,first)]
            authors=' and '.join(authors)
        '''

        aii=[ii,
            QtWidgets.QCheckBox(entryii['favourite']),
            QtWidgets.QCheckBox(entryii['read']),
            entryii['has_file'],
            entryii['authors'],
            entryii['title'],
            entryii['publication'],
            entryii['year']]
        data.append(aii)

    return data




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
