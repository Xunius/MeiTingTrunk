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

from lib.widgets import TableModel, MyHeaderView, MyTextEdit

import _MainFrameLoadData
import _MainFrameSlots

__version__='v0.1'

FILE_IN='new.sqlite'


# TODO:
# show docs in sub folders?
# fold long fields in meta data tab?
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
# change meta dict key naming convention to distinguish string and list types:
#   e.g. authors -> authors_l, year -> year_s


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
            settings.setValue('display/fonts/statusbar',
                QFont('Serif', 10)),
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


class MainFrame(QtWidgets.QWidget,_MainFrameLoadData.MainFrameLoadData,\
        _MainFrameSlots.MainFrameSlots):

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
        self.add_button=self.createAddMoreButton()

        self.add_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        #self.add_button.clicked.connect(self.addDocButtonClicked)
        h_layout0.addWidget(self.add_button)

        #h_layout0.addWidget(self.add_more_button)

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
        h_split=QtWidgets.QSplitter(Qt.Horizontal)
        h_split.setSizePolicy(getXExpandYExpandSizePolicy())
        v_layout0.addWidget(h_split)

        v_split=QtWidgets.QSplitter(Qt.Vertical)

        v_la1=QtWidgets.QVBoxLayout()
        v_la1.setContentsMargins(0,0,0,0)
        v_la1.setSpacing(0)
        fr=QtWidgets.QFrame()

        self.libtree=self.createLibTree()
        v_la1.addWidget(self.libtree)

        #-----------Add fold filter list button-----------
        self.fold_filter_button=self.createFoldFilterButton()
        v_la1.addWidget(self.fold_filter_button)
        fr.setLayout(v_la1)

        #v_split.addWidget(self.libtree)
        v_split.addWidget(fr)

        #v_la1.addWidget(self.filter_list)

        #----------------Add filter window----------------
        self.filter_list=self.createFilterList()

        v_split.addWidget(self.filter_list)
        #v_split.addWidget(fr)
        h_split.addWidget(v_split)

        v_split.setSizes([3,1])
        h=v_split.size().height()
        v_split.setSizes([h*0.65,h*0.35])

        #------------Add clear filtering frame------------
        self.clear_filter_frame=self.createClearFilterFrame()
        
        #------------------Add doc table------------------
        frame=QtWidgets.QFrame()

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
        h_layout.addWidget(self.fold_tab_button)
        frame.setLayout(h_layout)

        h_split.addWidget(frame)

        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()
        h_split.addWidget(self.tabs)

        #------------------Add status bar------------------
        self.status_bar=QtWidgets.QStatusBar()
        self.status_bar.setFixedHeight(11)
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

        # create pupup menu
        menu=QtWidgets.QMenu()
        add_action1=menu.addAction('Add PDF file')
        add_action2=menu.addAction('Add BibTex file')
        add_action3=menu.addAction('Add Entry Manually')

        button.setDefaultAction(add_action1)

        # these has to happen after setDefaultAction()
        button.setText('Add')
        button.setIcon(QIcon.fromTheme('document-new'))

        menu.triggered.connect(self.addActionTriggered)
        button.triggered.connect(self.addActionTriggered)

        button.setMenu(menu)
        button.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        return button

    def addActionTriggered(self,action):
        print('addActionTriggered:', action)
        action_text=action.text()
        print(action.text())

        '''
        if action_text=='Add Entry Manually':
            dialog=QtWidgets.QDialog()
            dialog.setWindowModality(Qt.ApplicationModal)
            b_cancel=QtWidgets.QPushButton('Cancel', dialog)
            b_cancel.
        '''


        return








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
    #                            Libtree slots                            #
    #######################################################################









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
