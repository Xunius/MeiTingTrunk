import sys,os
import logging
import logging.config
#import operator
import sqlite3
import pathlib
from PyQt5 import QtWidgets, QtCore, QtSvg
from PyQt5.QtCore import Qt, QVariant, QSettings, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor, QFontMetrics,\
        QCursor, QImage, QPainter
from lib import sqlitedb
from lib.tools import getMinSizePolicy, getXMinYExpandSizePolicy,\
        getXExpandYMinSizePolicy, getXExpandYExpandSizePolicy, getHSpacer, \
        getVSpacer, getHLine, getVLine

from lib.widgets import TableModel, MyHeaderView, AdjustableTextEdit,\
        MetaTabScroll, TreeWidgetDelegate, MyTreeWidget, PreferenceDialog,\
        NoteTextEdit

import _MainFrameLoadData
import _MainFrameSlots

import resource

__version__='v0.1'

OMIT_KEYS=[
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


LOG_CONFIG={
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '<%(filename)s-%(funcName)s()>: %(asctime)s,%(levelname)s: %(message)s'},
            },
        'handlers': {
            'default': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'formatter': 'standard',
                'filename': 'MTT.log',
                },
            },
        'loggers': {
            'default_logger': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': True
                }
            }
        }



# TODO:
# [NO] show docs in sub folders?
# [y] fold long fields in meta data tab?
# [y] create bib texts when clicking into the bibtex tab and changing doc
# [y] add icons to folders
# doc types, books, generic etc
# [NO] insert images to note?
# [y] add add folder functionality
# add add doc functionalities, by doi
# [y] add add doc functionalities, by bib
# add add doc functionalities, by RIS
# import from Mendeley, zotero, Endnote?
# autosave, auto backup
# export to text (clipboard, styles), bibtex, ris. citation styles things.
# [y] collapse side tab
# [y] seperate libraries
# [y] use resource file to load icons/images
# in note tab, add time stamps at left margin?
# [y] change meta dict key naming convention to distinguish string and list types:
#   e.g. authors -> authors_l, year -> year_s
# possible issue with local time with added time
# [y] add logger
# get all bib entries for multiple selected docs?
# [y] right click menus
# [y] option menu
# RIS
# import/export menu
# [y] add trash can
# sqlite text search: https://stackoverflow.com/questions/35020797/how-to-use-full-text-search-in-sqlite3-database-in-django 
# PDF preview
# add doc strings!!
# make long actions threaded
# [y] need to deal with folder changes in sqlite
# [y] add doc drag drop to folders
# [y] change needs review states.
# choose pdf viewer software.
# add doi lookup button
# add option to set autosave and auto backup
# add some actions to Edit menu


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow,self).__init__()

        self.logger=logging.getLogger('default_logger')
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
            settings.setValue('display/fonts/doc_table',
                QFont('Serif', 10)),
            settings.setValue('display/fonts/bibtex',
                QFont('Serif', 10)),
            settings.setValue('display/fonts/notes',
                QFont('Serif', 10)),
            settings.setValue('display/fonts/scratch_pad',
                QFont('Serif', 10)),

            settings.setValue('display/folder/highlight_color_br',
                    QBrush(QColor(200,200,255)))
            settings.setValue('export/bib/omit_fields', OMIT_KEYS)

            storage_folder=os.path.join(str(pathlib.Path.home()), 'Documents/MMT')
            settings.setValue('saving/storage_folder', storage_folder)

            settings.sync()

        else:
            settings=QSettings(settings_path,QSettings.IniFormat)

        #---------------Make sure output folder exists---------------
        storage_folder=settings.value('saving/storage_folder')
        print('# <loadSettings>: storage_folder=%s' %storage_folder)
        self.logger.info('storage_folder=%s' %storage_folder)

        storage_folder=os.path.expanduser(storage_folder)
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)
            os.makedirs(os.path.join(storage_folder,'Collections'))

            print('# <loadSettings>: Create folder %s' %storage_folder)
            self.logger.info('Create folder %s' %storage_folder)


        return settings

    def loadSettings(self):
        settings=self.initSettings()

        print('# <loadSettings>: settings.fielName()=%s' %settings.fileName())
        self.logger.info('settings.fielName()=%s' %settings.fileName())



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
        #organize_folder_action=QtWidgets.QAction('Organize Folders', self)
        #self.tool_menu.addAction(organize_folder_action)
        #if not self.is_loaded:
            #organize_folder_action.isEnabled(False)

        self.help_menu=self.menu_bar.addMenu('&Help')
        self.help_menu.addAction('Help')


        #-----------------Connect signals-----------------
        create_database_action.triggered.connect(self.createDatabaseTriggered)
        open_database_action.triggered.connect(self.openDatabaseTriggered)
        close_database_action.triggered.connect(self.closeDatabaseTriggered)
        preference_action.triggered.connect(self.preferenceTriggered)
        self.help_menu.triggered.connect(self.helpMenuTriggered)
        quit_action.triggered.connect(self.close)

        self.show()

    def closeEvent(self,event):
        print('# <closeEvent>: settings.sync()')
        self.logger.info('settings.sync()')
        self.settings.sync()



    #######################################################################
    #                           Menu bar actions                           #
    #######################################################################

    def createDatabaseTriggered(self):

        fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Create a sqlite file',
     '',"sqlite files (*.sqlite);; All files (*)")[0]

        if fname:
            print('createDatabaseTriggered: database file:',fname)

            storage_folder=self.settings.value('saving/storage_folder')
            db=sqlitedb.createNewDatabase(fname,storage_folder)

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

            print('# <openDatabaseTriggered>: Connected to database: %s' %fname)
            self.logger.info('Connected to database: %s' %fname)

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
        print('# <helpMenuTriggered>: action=%s, action.text()=%s' %(action,action.text()))
        self.logger.info('action=%s, action.text()=%s' %(action,action.text()))
        return


    def preferenceTriggered(self):
        diag=PreferenceDialog(self.settings,parent=self)
        diag.exec_()
    




class MainFrame(QtWidgets.QWidget,_MainFrameLoadData.MainFrameLoadData,\
        _MainFrameSlots.MainFrameSlots):

    def __init__(self,settings):
        super(MainFrame,self).__init__()

        self.settings=settings
        self.logger=logging.getLogger('default_logger')
        self.initUI()

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

        self.add_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.duplicate_check_button.setEnabled(False)

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

        #------------------Add right pane------------------
        fr1=QtWidgets.QFrame()
        v_la2=QtWidgets.QVBoxLayout()
        fr1.setLayout(v_la2)

        #-------------Add confirm review frame-------------
        self.confirm_review_frame=self.createConfirmReviewFrame()
        v_la2.addWidget(self.confirm_review_frame)

        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()
        v_la2.addWidget(self.tabs)

        h_split.addWidget(fr1)

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
        libtree=MyTreeWidget(self)
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

        libtree.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
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

    def createConfirmReviewFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        h_la=QtWidgets.QHBoxLayout()

        # confirm button
        self.confirm_review_button=QtWidgets.QToolButton(self)
        self.confirm_review_button.setText('Confirm')
        self.confirm_review_button.clicked.connect(self.confirmReviewButtonClicked)

        label=QtWidgets.QLabel('Meta data is correct?')
        h_la.addWidget(label)
        h_la.addWidget(self.confirm_review_button)

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

        tv.setDragEnabled(True)
        #tv.setSectionsMovable(True)
        tv.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        header=['docid','favourite','read','has_file','author','title',
                'journal','year','added','confirmed']
        tablemodel=TableModel(self,[],header,self.settings)
        tablemodel.dataChanged.connect(self.modelDataChanged)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True)
        tv.setColumnHidden(9,True)

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
        self.t_meta=MetaTabScroll(self.settings,self)
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
        #self.note_textedit=NoteTextEdit(self.font_dict['meta_keywords'])
        self.note_textedit=NoteTextEdit(self.settings)
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
        #self.scratchpad_textedit.setFont(self.font_dict['meta_keywords'])
        self.scratchpad_textedit.setFont(self.settings.value(
            '/display/fonts/scratch_pad',QFont))
        self.scratchpad_textedit.setSizePolicy(getXExpandYExpandSizePolicy())

        v_layout.addWidget(self.scratchpad_textedit)
        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll



    def createBiBTab(self):

        frame=QtWidgets.QWidget()
        #frame.setStyleSheet('background-color:white')
        scroll=QtWidgets.QScrollArea(self)
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
        #self.bib_textedit.setFont(self.font_dict['meta_keywords'])
        self.bib_textedit.setFont(self.settings.value('/display/fonts/bibtex',QFont))
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.bib_textedit)
        frame.setLayout(v_layout)
        self.copy_bib_button.clicked.connect(self.copyBibButtonClicked)

        return scroll





if __name__=='__main__':


    logging.config.dictConfig(LOG_CONFIG)
    app=QtWidgets.QApplication(sys.argv)

    '''
    splash_pic=QPixmap(':/logo.jpg')
    print('# <__init__>: splash_pic', splash_pic)
    splash=QtWidgets.QSplashScreen(splash_pic, Qt.WindowStaysOnTopHint)
    splash.show()
    splash.showMessage('Loading ...')

    QTimer.singleShot(2000, splash.close)

    app.processEvents()
    '''
    '''
    svgrenderer=QtSvg.QSvgRenderer('./recaman/recaman_box_n_33_fillline.svg.svg')
    qimage=QImage(522,305, QImage.Format_ARGB32)
    painter=QPainter(qimage)
    svgrenderer.render(painter)

    splash_pic=QPixmap.fromImage(qimage)
    print('# <__init__>: splash_pic', splash_pic)
    splash=QtWidgets.QSplashScreen(splash_pic, Qt.WindowStaysOnTopHint)
    splash.show()
    #splash.showMessage('Loading ...')

    QTimer.singleShot(3000, splash.close)

    app.processEvents()
    '''

    mainwindow=MainWindow()
    sys.exit(app.exec_())
