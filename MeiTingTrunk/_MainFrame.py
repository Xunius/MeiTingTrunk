'''
This is the header of the MainFrame class definition. The entire class def
is split into a few files:

* _MainFrame.py             : the __init__(), and creation of various widgets.
* _MainFrameLoadData.py       load data into various widgets. This is major
                              entrance, in particular, its loadLibTree() call
                              loads in data read from sqlite and triggers all
                              subsequent data loading.
* _MainFrameLibTreeSlots.py : actions involving folders, including creation,
                              re-parenting, renaming, trashing, and restoring
                              from trash.
* _MainFrameDocTableSlots.py: actions involving documents, including selection,
                               right clicking menu, deletion, opening.
* _MainFrameToolBarSlots.py : slots to widgets in the tool bar, including adding
                              new doc, new folder, duplicate checking and searching.
* _MainFrameDataSlots.py    : handles data updating, including updates of the
                              in-memory data dictionary from editing the meta
                              data tabs, from DOI querying, adding docs to
                              folders, and saving the in-memory data to sqlite
                              database.
* _MainFrameFilterListSlots.py: actions in response to filterings in the bottom
                                left filtering widget.
* _MainFrameProperties.py: a few getters for easier access to the current states
                           in various widgets.
* _MainFrameMetaTabSlots.py: actions in the meta data tab.
* _MainFrameOtherSlots.py: some functions dealing with hide/show if widgets,
                           clipboard copying and clearing data of widgets.


MeiTing Trunk

An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''


import os
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QBrush, QColor
from PyQt5.QtWidgets import QStyle

from . import _MainFrameLoadData, _MainFrameDataSlots, _MainFrameToolBarSlots,\
        _MainFrameLibTreeSlots, _MainFrameFilterListSlots, _MainFrameDocTableSlots,\
        _MainFrameMetaTabSlots, _MainFrameOtherSlots, _MainFrameProperties
from .lib.tools import getMinSizePolicy, getXMinYExpandSizePolicy, \
        getXExpandYMinSizePolicy, getXExpandYExpandSizePolicy, getHLine,\
        hasXapian
from .lib.widgets import MyTreeWidget, TableModel,\
        MyHeaderView, MetaTabScroll, CheckDuplicateFrame, NoteTextEdit,\
        SearchResFrame, PDFPreviewer



class MainFrame(QtWidgets.QWidget,_MainFrameLoadData.MainFrameLoadData,
        _MainFrameDataSlots.MainFrameDataSlots,
        _MainFrameToolBarSlots.MainFrameToolBarSlots,
        _MainFrameLibTreeSlots.MainFrameLibTreeSlots,
        _MainFrameFilterListSlots.MainFrameFilterListSlots,
        _MainFrameDocTableSlots.MainFrameDocTableSlots,
        _MainFrameMetaTabSlots.MainFrameMetaTabSlots,
        _MainFrameOtherSlots.MainFrameOtherSlots,
        _MainFrameProperties.MainFrameProperties
        ):
    def __init__(self,settings, parent):
        super(MainFrame,self).__init__()

        self.settings=settings
        self.parent=parent
        self.logger=logging.getLogger(__name__)
        self.initUI()
        self.auto_save_timer=QTimer(self)
        tinter=self.settings.value('saving/auto_save_min', 1, int)*60*1000 # in msc
        self.auto_save_timer.setInterval(tinter)
        self.auto_save_timer.timeout.connect(self.saveToDatabase)


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
        self.search_bar.setPlaceholderText('Type to search')
        self.search_bar.setFixedWidth(300)
        self.search_bar.setSizePolicy(getMinSizePolicy())
        self.search_bar.returnPressed.connect(self.searchBarClicked)

        # search button
        self.search_button=self.createSearchButton()
        self.search_button.setEnabled(False)

        h_layout0.addWidget(self.search_bar)
        h_layout0.addWidget(self.search_button)

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

        #---------Add duplicate check result frame---------
        self.duplicate_result_frame=self.createDuplicateResultFrame()
        v_la.addWidget(self.duplicate_result_frame)

        #-------------Add search result frame-------------
        self.search_res_frame=self.createSearchResultFrame()
        v_la.addWidget(self.search_res_frame)

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
        frame.setSizePolicy(getXExpandYExpandSizePolicy())
        h_split.addWidget(frame)

        #------------------Add right pane------------------
        self.tab_pane=QtWidgets.QFrame()
        v_la2=QtWidgets.QVBoxLayout()
        self.tab_pane.setLayout(v_la2)

        #-------------Add confirm review frame-------------
        self.confirm_review_frame=self.createConfirmReviewFrame()
        v_la2.addWidget(self.confirm_review_frame)

        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()
        v_la2.addWidget(self.tabs)

        h_split.addWidget(self.tab_pane)

        #------------------Add status bar------------------
        self.status_bar=QtWidgets.QStatusBar()
        #self.status_bar.setFixedHeight(12)
        self.status_bar.setFont(self.settings.value('display/fonts/statusbar',QFont))
        v_layout0.addWidget(self.status_bar)
        self.status_bar.showMessage('Welcome')

        self.progressbar=QtWidgets.QProgressBar(self)
        self.progressbar.setSizePolicy(getXExpandYMinSizePolicy())
        self.progressbar.setMaximum(1)
        self.progressbar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progressbar)

        # search_res_frame created before status bar
        self.search_res_frame.search_done_sig.connect(self.status_bar.clearMessage)

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        if 'Toggle Status bar' not in show_widgets:
            self.status_bar.setVisible(False)

        h_split.setHandleWidth(4)
        w=h_split.size().width()
        h_split.setCollapsible(2,True)
        h_split.setSizes([w*0.15,w*0.6,w*0.25])

        self.logger.info('Main frame UI inited.')

        self.show()


    #######################################################################
    #                           Create widgets                            #
    #######################################################################


    def createAddMoreButton(self):

        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        @pyqtSlot(QtWidgets.QAction)
        def changeDefaultAction(action):
            '''Change the default action'''

            action_data=action.data()
            for aii, (addii, cdii) in add_buttons.items():
                if aii==action_data:
                    addii.setShortcut('Ctrl+n')
                    cdii.setChecked(True)
                    button.setDefaultAction(addii)
                    button.setText('Add')
                    button.setIcon(QIcon.fromTheme('document-new',
                        self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
                    self.settings.setValue('import/default_add_action',aii)
                else:
                    addii.setShortcut('')
                    cdii.setChecked(False)

        #-------Add the default action to the button-------
        add_buttons={}
        menu=QtWidgets.QMenu()
        choose_default_menu=QtWidgets.QMenu('Choose Default Action',menu)
        default_act=self.settings.value('import/default_add_action',type=str)

        for aii in ['Add PDF File', 'Add Bibtex File', 'Add RIS File',
                'Add Entry Manually']:

            add_actionii=menu.addAction(aii)
            cd_actionii=choose_default_menu.addAction(aii)
            cd_actionii.setData(aii)
            cd_actionii.setCheckable(True)

            if aii==default_act:
                add_actionii.setShortcut('Ctrl+n')
                cd_actionii.setChecked(True)
            else:
                add_actionii.setShortcut('')
                cd_actionii.setChecked(False)
            add_buttons[aii]=[add_actionii, cd_actionii]

        choose_default_menu.triggered.connect(changeDefaultAction)
        menu.addMenu(choose_default_menu)

        button.setDefaultAction(add_buttons[default_act][0])

        # these has to happen after setDefaultAction()
        button.setText('Add')
        button.setIcon(QIcon.fromTheme('document-new',
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        menu.triggered.connect(self.addActionTriggered)

        return button


    def createAddFolderButton(self):

        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        menu=QtWidgets.QMenu()
        self.create_folder_action=menu.addAction('Create Folder')
        self.create_subfolder_action=menu.addAction('Create Sub Folder')

        button.setDefaultAction(self.create_folder_action)

        button.setText('Create Folder')
        button.setIcon(QIcon.fromTheme('folder-new',
            self.style().standardIcon(QStyle.SP_FileDialogNewFolder)))
        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        menu.triggered.connect(self.addFolderButtonClicked)

        return button


    def createDuplicateCheckButton(self):

        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setText('Check Duplicates')
        button.setIcon(QIcon.fromTheme('scanner',
            self.style().standardIcon(QStyle.SP_FileDialogContentsView)))
        button.clicked.connect(self.checkDuplicateClicked)

        return button


    def createSearchButton(self):

        button=QtWidgets.QToolButton(self)
        menu=QtWidgets.QMenu()

        search_fields=self.settings.value('search/search_fields',[],str)
        if isinstance(search_fields,str) and search_fields=='':
            search_fields=[]

        # add search fields menu
        lib_xapian_folder=os.path.join(self.settings.value(
            'saving/current_lib_folder', type=str), '_xapian_db')
        if hasXapian() and os.path.exists(lib_xapian_folder):
            has_pdf=True
        else:
            has_pdf=False

        for fieldii in ['Authors', 'Title', 'Abstract', 'Keywords', 'Tags',
                'Notes', 'Publication', 'PDF', 'Citationkey']:
            cbii=QtWidgets.QCheckBox(fieldii, menu)
            aii=QtWidgets.QWidgetAction(menu)
            if fieldii in search_fields:
                cbii.setChecked(True)
            if fieldii=='PDF':
                # keep a reference
                self.pdf_search_action=aii
                self.pdf_search_checkbox=cbii
                if not has_pdf:
                    cbii.setChecked(False)
                    aii.setEnabled(False)
            cbii.stateChanged.connect(aii.trigger)
            aii.setDefaultWidget(cbii)
            aii.setText(fieldii)
            menu.addAction(aii)

        menu.addSeparator()

        # add desend into subfolders option
        cbii=QtWidgets.QCheckBox('Include sub-folders', menu)
        if self.settings.value('search/desend_folder',bool):
            cbii.setChecked(True)
        aii=QtWidgets.QWidgetAction(menu)
        cbii.stateChanged.connect(aii.trigger)
        aii.setDefaultWidget(cbii)
        aii.setText('Include sub-folders')
        menu.addAction(aii)

        button.setIcon(QIcon.fromTheme('edit-find',
            self.style().standardIcon(QStyle.SP_FileDialogContentsView)))
        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        button.clicked.connect(self.searchBarClicked)

        return button


    def createLibTree(self):

        libtree=MyTreeWidget(self)

        libtree.customContextMenuRequested.connect(self.libTreeMenu)
        libtree.folder_move_signal.connect(self.changeFolderParent)
        libtree.folder_del_signal.connect(self.trashFolder)
        libtree.itemDoubleClicked.connect(self.renameFolder)
        libtree.add_doc_to_folder_signal.connect(self.addDocToFolder)
        libtree.selectionModel().selectionChanged.connect(self.selFolder)

        return libtree


    def createFoldFilterButton(self):

        button=QtWidgets.QToolButton(self)
        button.setArrowType(Qt.DownArrow)
        button.clicked.connect(self.foldFilterButtonClicked)
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

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        if 'Toggle Filter List' not in show_widgets:
            scroll.setVisible(False)

        return scroll


    def createDuplicateResultFrame(self):

        frame=CheckDuplicateFrame(self.settings,self)
        frame.tree.currentItemChanged.connect(self.duplicateResultCurrentChange)
        frame.del_doc_from_folder_signal.connect(self.delFromFolder)
        frame.del_doc_from_lib_signal.connect(self.delDoc)
        frame.clear_duplicate_button.clicked.connect(
                self.clearDuplicateButtonClicked)
        frame.merge_frame.add_new_doc_sig.connect(self.addDocFromDuplicateMerge)
        frame.merge_frame.del_doc_sig.connect(self.delDoc)
        frame.setVisible(False)

        return frame


    def createSearchResultFrame(self):

        frame=SearchResFrame(self.settings,self)
        frame.tree.currentItemChanged.connect(self.searchResultCurrentChange)
        frame.clear_searchres_button.clicked.connect(self.clearSearchResButtonClicked)
        frame.create_folder_sig.connect(self.createFolderFromSearch)
        #frame.hide_doc_sig.connect(self.hideDocTable)
        frame.setVisible(False)

        return frame


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
        frame.setVisible(False)

        return frame


    def createDocTable(self):

        tv=QtWidgets.QTableView(self)

        hh=MyHeaderView(self)

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
        tv.setColumnHidden(0,True) # doc id column, hide
        tv.setColumnHidden(9,True) # needs review column, shown as bold/normal

        tv.selectionModel().currentChanged.connect(self.selDoc)
        tv.clicked.connect(self.docTableClicked)
        #tablemodel.rowsInserted.connect(self.model_insert_row)
        tv.setContextMenuPolicy(Qt.CustomContextMenu)
        tv.customContextMenuRequested.connect(self.docTableMenu)

        tv.doubleClicked.connect(self.docDoubleClicked)
        tv.setAlternatingRowColors(True)

        # NOTE: this seems to be change somewhere between PyQt5.6.0 and
        # PyQt5.12.1 that the latter default to setWordWrap(True)
        tv.setWordWrap(False)

        tv.setStyleSheet('''alternate-background-color: rgb(230,230,249);
                background-color: none''')

        # add a short cut for pdf preview
        QtWidgets.QShortcut(Qt.Key_Space, tv, activated=self.openPDFViewer)

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

        self.t_notes=self.createNoteTab()
        self.t_bib=self.createBiBTab()
        self.t_scratchpad=self.createScratchTab()
        self.t_pdf=self.createPDFTab()
        self.t_meta=MetaTabScroll(self.settings,self)
        self.t_meta.meta_edited.connect(lambda field_list: self.updateTableData(\
            self._current_doc,self.t_meta._meta_dict,field_list))
        self.t_meta.update_by_doi_signal.connect(self.updateByDOI)

        # tab_dict is used for visibility control
        self.tab_dict={'Toggle Meta Tab': [self.t_meta, 'Meta Data'],
                'Toggle Notes Tab': [self.t_notes, 'Notes'],
                'Toggle BibTex Tab': [self.t_bib, 'BibTex'],
                'Toggle Scratch Pad Tab': [self.t_scratchpad, 'Scratch Pad'],
                'Toggle PDF Tab': [self.t_pdf, 'PDF preview']
                }

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        # add tabs that are toggled on in view menu
        for tii in show_widgets:
            if tii in self.tab_dict:
                tabs.addTab(*self.tab_dict[tii])

        for tii in list(set(self.tab_dict.keys()).difference(show_widgets)):
            self.tab_dict[tii][0].setVisible(False)

        tabs.currentChanged.connect(self.currentTabChange)

        return tabs


    def createNoteTab(self):

        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        frame=QtWidgets.QFrame()
        v_layout=QtWidgets.QVBoxLayout()

        button=QtWidgets.QToolButton(self)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setText('Open Editor')

        menu=QtWidgets.QMenu()
        self.open_editor_action=menu.addAction('Open Editor')
        self.choose_editor_action=menu.addAction('Choose Editor')
        button.setDefaultAction(self.open_editor_action)

        button.setIcon(QIcon.fromTheme('insert-text',
            self.style().standardIcon(QStyle.SP_FileDialogNewFolder)))
        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        menu.triggered.connect(self.openEditorTriggered)
        v_layout.addWidget(button, 0, Qt.AlignLeft)

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
        self.scratchpad_textedit.setFont(self.settings.value(
            '/display/fonts/scratch_pad',QFont))
        self.scratchpad_textedit.setSizePolicy(getXExpandYExpandSizePolicy())

        v_layout.addWidget(self.scratchpad_textedit)
        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll


    def createPDFTab(self):

        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        frame=QtWidgets.QFrame()
        v_layout=QtWidgets.QVBoxLayout()
        self.pdf_viewer=PDFPreviewer(self)
        v_layout.addWidget(self.pdf_viewer)
        frame.setLayout(v_layout)
        scroll.setWidget(frame)

        return scroll



    def createBiBTab(self):

        frame=QtWidgets.QWidget()
        scroll=QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        v_layout=QtWidgets.QVBoxLayout()

        self.copy_bib_button=QtWidgets.QToolButton(self)
        self.copy_bib_button.setText('Copy')
        self.copy_bib_button.setIcon(QIcon.fromTheme('edit-copy',
                self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
        self.copy_bib_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        h_layout=QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.copy_bib_button)
        h_layout.addStretch()

        self.bib_textedit=QtWidgets.QTextEdit(self)
        self.bib_textedit.setReadOnly(True)
        self.bib_textedit.setFont(self.settings.value('/display/fonts/bibtex',QFont))
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.bib_textedit)
        frame.setLayout(v_layout)
        self.copy_bib_button.clicked.connect(self.copyBibButtonClicked)

        return scroll

