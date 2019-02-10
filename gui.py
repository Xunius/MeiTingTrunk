import sys,os
#import operator
import sqlite3
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QVariant, QSettings
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor, QFontMetrics,\
        QCursor
from lib import sqlitedb
from lib.tools import getMinSizePolicy, getXMinYExpandSizePolicy,\
        getXExpandYMinSizePolicy, getXExpandYExpandSizePolicy, getHSpacer, \
        getVSpacer, getHLine, getVLine

from lib.widgets import TableModel, MyHeaderView, AdjustableTextEdit,\
        MetaTabScroll, TreeWidgetDelegate, MyTreeWidget, PreferenceDialog,\
        NoteTextEdit

import _MainFrameLoadData
import _MainFrameSlots

__version__='v0.1'

FILE_IN='new4.sqlite'
OMIT_KEYS=[
        'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
        'lastName_l', 'pend_delete', 'folders_l', 'type', 'id'
        ]


# TODO:
# show docs in sub folders?
# [y] fold long fields in meta data tab?
# [y] create bib texts when clicking into the bibtex tab and changing doc
# [y] add icons to folders
# doc types, books, generic etc
# insert images to note?
# add add folder functionality
# add add doc functionalities, by doi, bib, RIS
# import from Mendeley, zotero, Endnote?
# autosave, auto backup
# export to text (clipboard, styles), bibtex, ris.
# [y] collapse side tab
# seperate libraries
# [y] use resource file to load icons/images
# in note tab, add time stamps at left margin
# [y] change meta dict key naming convention to distinguish string and list types:
#   e.g. authors -> authors_l, year -> year_s
# possible issue with local time with added time
# add logger
# get all bib entries for multiple selected docs?
# right click menus
# option menu
# RIS
# import/export menu
# [y] add trash can
# sqlite text search: https://stackoverflow.com/questions/35020797/how-to-use-full-text-search-in-sqlite3-database-in-django 


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow,self).__init__()

        #self.db=db
        #meta_dict,folder_data,folder_dict=sqlitedb.readSqlite(db)
        self.settings=self.loadSettings()
        self.is_loaded=False

        self.initUI()

        self.main_frame=MainFrame(self.settings)
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
            settings.setValue('display/fonts/statusbar',
                QFont('Serif', 10)),
            settings.setValue('display/folder/highlight_color_br',
                    QBrush(QColor(200,200,255)))
            settings.setValue('export/bib/omit_fields', OMIT_KEYS)
            settings.setValue('saving/storage_folder', folder_name)

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

        aa=settings.value('export/bib/omit_fields', [], str)
        print('omit_fields',aa)

        storage_folder=settings.value('saving/storage_folder')
        print('storage_folder',storage_folder)

        #---------------Create output folder---------------
        storage_folder=os.path.expanduser(storage_folder)
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)
            print("Create folder %s" %storage_folder)


        return settings


    def initUI(self):
        self.setWindowTitle('Reference manager %s' %__version__)
        self.setGeometry(100,100,1200,900)    #(x_left,y_top,w,h)
        #self.setWindowIcon(QIcon('img.png'))

        self.menu_bar=self.menuBar()

        self.file_menu=self.menu_bar.addMenu('&File')

        create_database_action=QtWidgets.QAction('Create New Database',self)
        open_database_action=QtWidgets.QAction('Open Database',self)
        close_database_action=QtWidgets.QAction('Close Database',self)
        import_action=QtWidgets.QAction('Import',self)
        export_action=QtWidgets.QAction('Export',self)
        create_backup_action=QtWidgets.QAction('Create Backup',self)
        quit_action=QtWidgets.QAction('Quit',self)

        create_database_action.setShortcut('Ctrl+n')
        open_database_action.setShortcut('Ctrl+o')
        close_database_action.setShortcut('Ctrl+w')
        quit_action.setShortcut('Ctrl+q')

        self.file_menu.addAction(create_database_action)
        self.file_menu.addAction(open_database_action)
        self.file_menu.addAction(close_database_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(import_action)
        self.file_menu.addAction(export_action)
        self.file_menu.addAction(create_backup_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(quit_action)


        self.edit_menu=self.menu_bar.addMenu('&Edit')
        preference_action=QtWidgets.QAction('Preferences',self)
        self.edit_menu.addAction(preference_action)

        self.tool_menu=self.menu_bar.addMenu('&Tool')
        self.help_menu=self.menu_bar.addMenu('&Help')
        self.help_menu.addAction('Help')


        #-----------------Connect signals-----------------
        open_database_action.triggered.connect(self.openDatabaseTriggered)
        close_database_action.triggered.connect(self.closeDatabaseTriggered)
        preference_action.triggered.connect(self.preferenceTriggered)
        self.help_menu.triggered.connect(self.helpMenuTriggered)
        quit_action.triggered.connect(self.close)

        self.show()

    def closeEvent(self,event):
        print('settings sync')
        self.settings.sync()



    #######################################################################
    #                           Menu bar actions                           #
    #######################################################################

    def createDatabaseTriggered(self):

        fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Create a sqlite file',
     '',"sqlite files (*.sqlite);; All files (*)")[0]

        if fname:
            print('createDatabaseTriggered: database file:',fname)

        return


    def openDatabaseTriggered(self):

        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a sqlite file',
     '',"sqlite files (*.sqlite);; All files (*)")[0]

        if fname:

            # close current if loaded
            if self.is_loaded:
                self.closeDatabaseTriggered()

            self.main_frame.status_bar.showMessage('Opening database...')
            db = sqlite3.connect(fname)
            print('Connected to database:')
            self.db=db
            meta_dict,folder_data,folder_dict=sqlitedb.readSqlite(db)
            self.main_frame.loadLibTree(db,meta_dict,folder_data,folder_dict)
            self.main_frame.status_bar.clearMessage()
            self.is_loaded=True

        return

    def closeDatabaseTriggered(self):

        choice=QtWidgets.QMessageBox.question(self, 'Confirm Close',
                'Save and close current database?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice==QtWidgets.QMessageBox.Yes:
            self.main_frame.clearData()
            self.is_loaded=False







    def helpMenuTriggered(self,action):
        print('helpMenuTriggered: action:',action,action.text())
        return


    def preferenceTriggered(self):
        diag=PreferenceDialog(self.settings,parent=self)
        diag.exec_()
    




class MainFrame(QtWidgets.QWidget,_MainFrameLoadData.MainFrameLoadData,\
        _MainFrameSlots.MainFrameSlots):

    def __init__(self,settings):
        super(MainFrame,self).__init__()

        #self.db=db
        #self.meta_dict=meta_dict
        #self.folder_data=folder_data
        #self.folder_dict=folder_dict
        #if isinstance(self.folder_dict,dict):
            #self.inv_folder_dict={v[0]:k for k,v in self.folder_dict.items()}
        self.settings=settings

        # get font configs
        self.font_dict={
            'meta_title': self.settings.value('display/fonts/meta_title',QFont),
            'meta_authors': self.settings.value('display/fonts/meta_authors',QFont),
            'meta_keywords': self.settings.value('display/fonts/meta_keywords',QFont)
            }


        self.initUI()

        #--------------------Load data--------------------
        #self.loadLibTree()


    def initUI(self):

        v_layout0=QtWidgets.QVBoxLayout(self)
        v_layout0.setContentsMargins(2,5,2,1)

        #-------------------Tool bar row-------------------
        h_layout0=QtWidgets.QHBoxLayout()
        v_layout0.addLayout(h_layout0)

        # Add button
        self.add_button=self.createAddMoreButton()
        self.add_folder_button=self.createAddFolderButton()
        self.duplicate_check_button=self.createDuplicateCheckButton()

        h_layout0.addWidget(self.add_button)
        h_layout0.addWidget(self.add_folder_button)
        h_layout0.addWidget(self.duplicate_check_button)

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

        #---------------------H split---------------------
        h_split=QtWidgets.QSplitter(Qt.Horizontal)
        h_split.setSizePolicy(getXExpandYExpandSizePolicy())
        v_layout0.addWidget(h_split)

        #---------------------V split---------------------
        v_split=QtWidgets.QSplitter(Qt.Vertical)
        v_la1=QtWidgets.QVBoxLayout()
        v_la1.setContentsMargins(0,0,0,0)
        v_la1.setSpacing(0)
        fr=QtWidgets.QFrame()

        #-------------------Add lib tree-------------------
        self.libtree=self.createLibTree()
        v_la1.addWidget(self.libtree)

        #-----------Add fold filter list button-----------
        self.fold_filter_button=self.createFoldFilterButton()
        v_la1.addWidget(self.fold_filter_button)

        fr.setLayout(v_la1)
        v_split.addWidget(fr)

        #----------------Add filter list----------------
        self.filter_list=self.createFilterList()

        v_split.addWidget(self.filter_list)
        h_split.addWidget(v_split)

        v_split.setSizes([3,1])
        h=v_split.size().height()
        v_split.setSizes([h*0.65,h*0.35])

        #------------Add clear filtering frame------------
        self.clear_filter_frame=self.createClearFilterFrame()

        frame=QtWidgets.QFrame()
        v_la=QtWidgets.QVBoxLayout()
        v_la.addWidget(self.clear_filter_frame)

        #------------------Add doc table------------------
        self.doc_table=self.createDocTable()
        v_la.addWidget(self.doc_table)

        h_layout=QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0,0,0,0)
        h_layout.setSpacing(0)
        h_layout.addLayout(v_la)

        #--------------Add fold/unfold button--------------
        self.fold_tab_button=self.createFoldTabButton()
        h_layout.addWidget(self.fold_tab_button)
        frame.setLayout(h_layout)
        h_split.addWidget(frame)

        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()
        h_split.addWidget(self.tabs)

        #------------------Add status bar------------------
        self.status_bar=QtWidgets.QStatusBar()
        #self.status_bar.setFixedHeight(12)
        self.status_bar.setFont(self.settings.value('display/fonts/statusbar',QFont))
        v_layout0.addWidget(self.status_bar)
        self.status_bar.showMessage('etest')

        h_split.setHandleWidth(4)
        w=h_split.size().width()
        h_split.setCollapsible(2,True)
        h_split.setSizes([w*0.15,w*0.6,w*0.25])


        self.show()


    #######################################################################
    #                           Create widgets                            #
    #######################################################################


    def createAddMoreButton(self):

        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        # create popup menu
        menu=QtWidgets.QMenu()
        add_action1=menu.addAction('Add PDF File')
        add_action2=menu.addAction('Add BibTex File')
        add_action3=menu.addAction('Add Entry Manually')

        button.setDefaultAction(add_action1)

        # these has to happen after setDefaultAction()
        button.setText('Add')
        button.setIcon(QIcon.fromTheme('document-new'))
        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        menu.triggered.connect(self.addActionTriggered)

        return button

    def createAddFolderButton(self):

        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        menu=QtWidgets.QMenu()
        self.create_folder_action=menu.addAction('Create Folder')
        self.create_subfolder_action=menu.addAction('Create Sub Folder')

        button.setDefaultAction(self.create_folder_action)

        button.setText('Create Folder')
        button.setIcon(QIcon.fromTheme('folder-new'))
        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        menu.triggered.connect(self.addFolderButtonClicked)

        return button

    def createDuplicateCheckButton(self):
        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setText('Check Duplicates')
        button.setIcon(QIcon.fromTheme('scanner'))

        return button


    def createLibTree(self):

        #libtree=QtWidgets.QTreeWidget()
        libtree=MyTreeWidget()
        libtree.setHeaderHidden(True)
        # column1: folder name, column2: folder id
        libtree.setColumnCount(2)
        libtree.hideColumn(1)
        libtree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        #libtree.itemClicked.connect(self.clickSelFolder)
        libtree.selectionModel().selectionChanged.connect(self.selFolder)
        libtree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        libtree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        # make horziontal scroll bar appear
        libtree.header().setStretchLastSection(False)
        libtree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        libtree.setContextMenuPolicy(Qt.CustomContextMenu)
        libtree.customContextMenuRequested.connect(self.libTreeMenu)
        delegate=TreeWidgetDelegate()
        libtree.setItemDelegate(delegate)

        libtree.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        libtree.folder_move_signal.connect(self.changeFolderParent)
        libtree.folder_del_signal.connect(self.trashFolder)

        return libtree

    def createFoldFilterButton(self):
        button=QtWidgets.QToolButton(self)
        button.setArrowType(Qt.DownArrow)
        button.clicked.connect(self.foldFilterButtonClicked)
        #button.setFixedWidth(50)
        button.setSizePolicy(getXExpandYMinSizePolicy())
        button.setFixedHeight(10)
        #button.setStyleSheet(
                #''''border-radius: 0; border-width: 1px;
                #border-style: solid; border-color:grey''')

        return button


    def createFilterList(self):
        frame=QtWidgets.QFrame()
        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        v_layout=QtWidgets.QVBoxLayout()
        v_layout.setContentsMargins(0,0,0,0)

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


    def createClearFilterFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        h_la=QtWidgets.QHBoxLayout()

        # clear fitlering button
        self.clear_filter_button=QtWidgets.QToolButton(self)
        self.clear_filter_button.setText('Clear')
        self.clear_filter_button.clicked.connect(self.clearFilterButtonClicked)

        self.clear_filter_label=QtWidgets.QLabel('  Clear current filtering')
        h_la.addWidget(self.clear_filter_label)
        h_la.addWidget(self.clear_filter_button)

        frame.setLayout(h_la)

        # Start up as hidden
        frame.setVisible(False)

        return frame


    def createDocTable(self):

        tv=QtWidgets.QTableView(self)

        hh=MyHeaderView(self)
        hh.setSectionsClickable(True)
        hh.setHighlightSections(True)
        hh.sectionResized.connect(hh.myresize)
        hh.setStretchLastSection(False)
        hh.setSectionsMovable(True)

        tv.setHorizontalHeader(hh)
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        tv.setSortingEnabled(True)

        header=['docid','favourite','read','has_file','author','title',
                'journal','year','added']
        tablemodel=TableModel(self,[],header)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True)

        tv.selectionModel().currentChanged.connect(self.selDoc)
        tv.clicked.connect(self.docTableClicked)
        #tablemodel.rowsInserted.connect(self.model_insert_row)
        tv.setContextMenuPolicy(Qt.CustomContextMenu)
        tv.customContextMenuRequested.connect(self.docTableMenu)

        tv.doubleClicked.connect(self.docDoubleClicked)

        return tv



    def createFoldTabButton(self):
        button=QtWidgets.QToolButton(self)
        button.setArrowType(Qt.RightArrow)
        button.clicked.connect(self.foldTabButtonClicked)
        button.setFixedWidth(10)
        button.setFixedHeight(200)
        #button.setStyleSheet(
                #''''border-radius: 0; border-width: 1px;
                #border-style: solid; border-color:grey''')

        return button


    def createTabs(self):

        tabs=QtWidgets.QTabWidget()
        #tabs.setMinimumWidth(250)
        self.t_notes=self.createNoteTab()
        self.t_bib=self.createBiBTab()
        self.t_scratchpad=self.createScratchTab()
        self.t_meta=MetaTabScroll(self.font_dict,self)
        #self.t_meta.meta_edited.connect(lambda: self.updateTabelData(
            #self._current_doc,self.t_meta._meta_dict))
        self.t_meta.meta_edited.connect(lambda field_list: self.updateTabelData(\
            self._current_doc,self.t_meta._meta_dict,field_list))

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

        #self.note_textedit=QtWidgets.QTextEdit(self)
        #self.note_textedit.setFont(self.font_dict['meta_keywords'])
        #self.note_textedit.setSizePolicy(getXExpandYExpandSizePolicy())
        self.note_textedit=NoteTextEdit(self.font_dict['meta_keywords'])
        self.note_textedit.note_edited_signal.connect(lambda: self.updateNotes(
            self._current_doc,self.note_textedit.toPlainText()))

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





if __name__=='__main__':

    '''
    abpath_in=os.path.abspath(FILE_IN)
    try:
        dbin = sqlite3.connect(abpath_in)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')
    '''

    app=QtWidgets.QApplication(sys.argv)
    mainwindow=MainWindow()
    sys.exit(app.exec_())
