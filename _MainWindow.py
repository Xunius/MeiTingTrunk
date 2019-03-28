'''
MeiTing Trunk

An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.


Defines the main window GUI including the title bar, and database
controls (creation, opening, saving, closing and switching).
Also defines default settings and loading of settings.
'''

import os
import logging
import logging.config
import sqlite3
import pathlib
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QBrush, QColor
import _MainFrame
from lib import sqlitedb
from lib.widgets import PreferenceDialog, ExportDialog, ThreadRunDialog,\
        ImportDialog

from main import __version__


# default setting for bibtex export
OMIT_KEYS=[
    'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
    'lastName_l', 'deletionPending', 'folders_l', 'type', 'id',
    'abstract', 'advisor', 'month', 'language', 'confirmed',
    'deletionPending', 'note', 'publicLawNumber', 'sections',
    'reviewedArticle', 'userType', 'shortTitle', 'sourceType',
    'code', 'codeNumber', 'codeSection', 'codeVolume', 'citationKey',
    'day', 'dateAccessed', 'internationalAuthor', 'internationalUserType',
    'internationalTitle', 'internationalNumber', 'genre', 'lastUpdate',
    'legalStatus', 'length', 'medium'
    ]


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow,self).__init__()

        self.logger=logging.getLogger(__name__)
        self.logger.info('''
##############################################
New session started
##############################################
        ''')
        self.settings=self.initSettings()
        self.is_loaded=False  # is any database opended

        self.main_frame=_MainFrame.MainFrame(self.settings)
        self.main_frame.view_change_sig.connect(self.viewChangeResponse)
        self.setCentralWidget(self.main_frame)

        # put initUI() after main_frame as it's referencing widgets in main_frame
        self.initUI()

        # auto open recent lib
        recent=self.settings.value('file/recent_open',[],str)
        if isinstance(recent,str) and recent=='':
            recent=[]

        self.logger.debug('Recent open list = %s' %recent)

        if self.settings.value('file/auto_open_last',type=int) and len(recent)>0:
            # add a delay, otherwise splash won't show
            QTimer.singleShot(100, lambda: self._openDatabase(recent[-1]))


    def initSettings(self):
        """Load settings file if exists, create new otherwise
        """

        folder_name=os.path.dirname(os.path.abspath(__file__))
        settings_path=os.path.join(folder_name,'settings.ini')

        if not os.path.exists(settings_path):
            settings=QSettings(settings_path,QSettings.IniFormat)

            # fonts for various fields
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

            # highlight folder containing a doc
            settings.setValue('display/folder/highlight_color_br',
                    QBrush(QColor(200,200,255)))

            settings.setValue('export/bib/omit_fields', OMIT_KEYS)
            settings.setValue('export/bib/path_type', 'absolute')
            settings.setValue('export/ris/path_type', 'absolute')

            # storage recently opened database
            settings.setValue('file/recent_open', [])
            settings.setValue('file/recent_open_num', 2)
            settings.setValue('file/auto_open_last', 1)

            # default storage folder
            storage_folder=os.path.join(str(pathlib.Path.home()),
                    'Documents/MeiTingTrunk')
            settings.setValue('saving/storage_folder', storage_folder)

            # auto save
            settings.setValue('saving/auto_save_min', 5),

            # rename pdf files in storage
            settings.setValue('saving/rename_files', 1)
            settings.setValue('saving/rename_file_replace_space', 1)

            # min score to flag a duplication
            settings.setValue('duplicate_min_score', 60)

            settings.setValue('import/default_add_action', 'Add PDF File')

            # search fields
            settings.setValue('search/search_fields', ['Authors', 'Title',
                'Abstract', 'Keywords', 'Tags', 'Notes', 'Publication'])
            settings.setValue('search/desend_folder', True)

            # view control
            settings.setValue('view/show_widgets', ['Toggle Filter List',
                'Toggle Tab Pane', 'Toggle Meta Tab', 'Toggle Notes Tab',
                'Toggle BibTex Tab', 'Toggle Scratch Pad Tab',
                'Toggle Status bar'])

            settings.sync()
        else:
            settings=QSettings(settings_path,QSettings.IniFormat)

        #---------------Make sure output folder exists---------------
        storage_folder=settings.value('saving/storage_folder')
        self.logger.info('storage_folder=%s' %storage_folder)

        storage_folder=os.path.expanduser(storage_folder)
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)

            self.logger.info('Create folder %s' %storage_folder)

        return settings


    def initUI(self):
        """Create menu bar
        """

        self.setWindowTitle('MEI-TING TRUNK %s' %__version__)
        self.setGeometry(100,100,1200,900)    #(x_left,y_top,w,h)
        #self.setWindowIcon(QIcon('img.png'))

        self.menu_bar=self.menuBar()

        #--------------------Files menu--------------------
        self.file_menu=self.menu_bar.addMenu('&File')

        create_database_action=self.file_menu.addAction('Create New Library')
        open_database_action=self.file_menu.addAction('Open Library')
        self.recent_open_menu=self.file_menu.addMenu('Open Recent')
        save_database_action=self.file_menu.addAction('Save Library')
        close_database_action=self.file_menu.addAction('Close Library')
        self.file_menu.addSeparator()
        create_backup_action=self.file_menu.addAction('Create Backup')
        quit_action=self.file_menu.addAction('Quit')

        create_database_action.setIcon(QIcon.fromTheme('document-new'))
        open_database_action.setIcon(QIcon.fromTheme('document-open'))
        self.recent_open_menu.setIcon(QIcon.fromTheme('document-open-recent'))
        save_database_action.setIcon(QIcon.fromTheme('document-save'))
        close_database_action.setIcon(QIcon.fromTheme('call-stop'))
        create_backup_action.setIcon(QIcon.fromTheme('document-send'))
        quit_action.setIcon(QIcon.fromTheme('window-close'))

        create_database_action.setShortcut('Ctrl+Shift+n')
        open_database_action.setShortcut('Ctrl+o')
        save_database_action.setShortcut('Ctrl+s')
        close_database_action.setShortcut('Ctrl+w')
        quit_action.setShortcut('Ctrl+q')

        #---------------Populate open recent---------------
        recent=self.settings.value('file/recent_open',[],str)
        if isinstance(recent,str) and recent=='':
            recent=[]
        recent_num=self.settings.value('file/recent_open_num',type=int)

        if recent and recent_num>0:
            for rii in recent:
                recentii=self.recent_open_menu.addAction(rii)
                recentii.triggered.connect(lambda x,t=rii: self._openDatabase(t))

        #--------------------Edit menu--------------------
        self.edit_menu=self.menu_bar.addMenu('&Edit')
        preference_action=QtWidgets.QAction('Preferences',self)
        preference_action.setIcon(QIcon.fromTheme('preferences-system'))
        preference_action.setShortcut('Ctrl+p')
        self.edit_menu.addAction(preference_action)

        #--------------------View menu--------------------
        self.view_menu=self.menu_bar.addMenu('&View')

        self.view_action_dict={}
        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        for tii in ['Toggle Filter List', None, 'Toggle Tab Pane',
                'Toggle Meta Tab', 'Toggle Notes Tab', 'Toggle BibTex Tab',
                'Toggle Scratch Pad Tab', None, 'Toggle Status bar']:
            if tii is None:
                self.view_menu.addSeparator()
            elif tii=='Toggle Status bar':
                # Status bar is kind of necessary
                continue
            else:
                tii_view_action=self.view_menu.addAction(tii)
                tii_view_action.setCheckable(True)
                if tii in show_widgets:
                    tii_view_action.setChecked(True)
                else:
                    tii_view_action.setChecked(False)
                self.view_action_dict[tii]=tii_view_action

        # remove the box of checkboxes
        self.menu_bar.setStyleSheet('''
        QMenu::indicator {
        }
        ''')

        #--------------------Tools menu--------------------
        self.tool_menu=self.menu_bar.addMenu('&Tools')
        self.import_action=QtWidgets.QAction('&Import', self)
        self.export_action=QtWidgets.QAction('&Export', self)
        self.tool_menu.addAction(self.import_action)
        self.tool_menu.addAction(self.export_action)
        if not self.is_loaded:
            self.export_action.setEnabled(False)

        #--------------------Help menu--------------------
        self.help_menu=self.menu_bar.addMenu('&Help')
        self.help_menu.addAction('&Help')

        #-----------------Connect signals-----------------
        create_database_action.triggered.connect(self.createDatabaseTriggered)
        open_database_action.triggered.connect(self.openDatabaseTriggered)
        save_database_action.triggered.connect(self.saveDatabaseTriggered)
        close_database_action.triggered.connect(self.closeDatabaseTriggered)
        preference_action.triggered.connect(self.preferenceTriggered)
        self.import_action.triggered.connect(self.importTriggered)
        self.export_action.triggered.connect(self.exportTriggered)
        self.help_menu.triggered.connect(self.helpMenuTriggered)
        quit_action.triggered.connect(self.close)
        self.view_menu.triggered.connect(self.viewChangeTriggered)

        self.logger.info('Main window UI inited.')

        self.show()

        return


    def closeEvent(self,event):

        if self.is_loaded:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm Close',
                    'Save and close?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)

        if choice==QtWidgets.QMessageBox.Yes:
            self.saveDatabaseTriggered()
            self.closeDatabaseTriggered(ask=False)

            self.logger.info('settings.sync()')
            self.settings.sync()
            event.accept()
        elif choice==QtWidgets.QMessageBox.Cancel:
            event.ignore()

        return


    #######################################################################
    #                           Menu bar actions                           #
    #######################################################################

    @pyqtSlot()
    def createDatabaseTriggered(self):

        # close current if loaded
        if self.is_loaded:
            do=self.closeDatabaseTriggered()
            if not do:
                return

        storage_folder=self.settings.value('saving/storage_folder')
        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Create a sqlite file',
                storage_folder,
                "sqlite files (*.sqlite);; All files (*)")[0]

        if fname:

            # make sure has .sqlite ext
            dirname,filename=os.path.split(fname)
            lib_name,ext=os.path.splitext(filename)
            if ext=='':
                filename='%s.sqlite' %lib_name
                fname=os.path.join(dirname,filename)

            def func(jobid,fname):
                try:
                    result=sqlitedb.createNewDatabase(fname)
                    return 0,jobid,result
                except Exception:
                    self.logger.exception('Failed to create new database file')
                    return 1,jobid,None

            # run in separate thread
            td=ThreadRunDialog(func,
                [(0,fname)],
                show_message='Creating new database...',
                max_threads=1,
                get_results=False,
                close_on_finish=True,
                progressbar_style='busy',
                parent=None)

            td.master.all_done_signal.connect(lambda: self._openDatabase(fname))
            td.exec_()


        return


    @pyqtSlot()
    def openDatabaseTriggered(self):

        # close current if loaded
        if self.is_loaded:
            do=self.closeDatabaseTriggered()
            if not do:
                return

        fname = QtWidgets.QFileDialog.getOpenFileName(self,
                'Choose a sqlite file',
                self.settings.value('saving/storage_folder',str),
                "sqlite files (*.sqlite);; All files (*)")[0]

        if fname:
            try:
                self._openDatabase(fname)
            except Exception as e:
                self.logger.exception('Exception in _openDatabase(): %s' %e)

                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText("Oopsi.")
                msg.setInformativeText("Failed to open database file\n    %s" %fname)
                msg.exec_()

            return


    @pyqtSlot(str)
    def _openDatabase(self, fname):
        """Open a sqlite database

        Args:
            fname (str): abs file path to sqlite data file

        """

        # close current if loaded. For open recent calls
        if self.is_loaded:
            do=self.closeDatabaseTriggered()
            if not do:
                return

        if not os.path.exists(fname):
            self.logger.info('Cant find database file %s' %fname)

            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Can not find file')
            msg.setText("Can not find target database file.")
            msg.setInformativeText("The requested database file\n    %s\nmay have be deleted, renamed or removed."\
                    %fname)
            msg.exec_()

            # if this is recent, remove it from recent
            recent=self.settings.value('file/recent_open',[],str)
            if isinstance(recent,str) and recent=='':
                recent=[]

            if fname in recent:
                recent.remove(fname)
                self.settings.setValue('file/recent_open', recent)

                self.logger.info('Remove non-exist database file from recent list: %s' %fname)

                for actionii in self.recent_open_menu.findChildren(
                        QtWidgets.QAction):
                    if actionii.text()==fname:
                        self.recent_open_menu.removeAction(actionii)

            return

        self.main_frame.status_bar.showMessage('Opening database...')
        QtWidgets.QApplication.processEvents() # needed?
        # progressbar won't work atm, as the sqlitedb is in the same GUI thread.
        #self.main_frame.progressbar.setVisible(True)
        #self.main_frame.progressbar.setMaximum(0)
        try:
            db = sqlite3.connect(fname)
            self.logger.info('Connected to database: %s' %fname)
        except:
            self.logger.warning('Failed to connect to database %s' %fname)
            return

        self.db=db
        # read and parse data
        meta_dict,folder_data,folder_dict=sqlitedb.readSqlite(db)
        # load data into GUI
        self.main_frame.loadLibTree(db,meta_dict,folder_data,folder_dict)
        #self.main_frame.progressbar.setVisible(False)

        self.is_loaded=True

        # get sqlite file name without ext as library name
        storage_folder,filename=os.path.split(fname)
        lib_name=os.path.splitext(filename)[0]
        lib_folder=os.path.join(storage_folder,lib_name)

        self.current_lib=lib_name
        self.current_lib_folder=lib_folder
        self.settings.setValue('saving/current_lib_folder', self.current_lib_folder)
        self.setWindowTitle('MEI-TING TRUNK %s: %s' %(__version__, lib_name))

        self.logger.info('Get current_lib = %s' %lib_name)
        self.logger.info('Get current_lib_folder = %s' %self.current_lib_folder)

        #-----------Make sure lib folder exists-----------
        if not os.path.exists(self.current_lib_folder):

            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Can not find folder')
            msg.setText("Can not find library folder.")
            msg.setInformativeText("The library folder\n    %s\nmay have be deleted, renamed or removed. \nA new folder is created, but the PDF files are missing."\
                    %self.current_lib_folder)
            msg.exec_()

            os.makedirs(self.current_lib_folder)
            self.logger.info('Create lib folder: %s' %self.current_lib_folder)

        lib_collection_folder=os.path.join(self.current_lib_folder,'_collections')
        if not os.path.exists(lib_collection_folder):

            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Can not find folder')
            msg.setText("Can not find library folder.")
            msg.setInformativeText("The library folder\n    %s\nmay have be deleted, renamed or removed. \nA new folder is created, but the PDF files are missing."\
                    %lib_collection_folder)
            msg.exec_()
            os.makedirs(lib_collection_folder)
            self.logger.info('Create lib collection folder: %s' %lib_collection_folder)

        self.main_frame.auto_save_timer.start()

        self.logger.info('Start auto save timer.')

        self.import_action.setEnabled(True)
        self.export_action.setEnabled(True)

        # add to recent list
        recent=self.settings.value('file/recent_open',[],str)
        if isinstance(recent,str) and recent=='':
            recent=[]

        if fname in recent:
            recent.remove(fname)

        recent.append(fname)
        recentii=self.recent_open_menu.addAction(fname)
        recentii.triggered.connect(lambda x,t=fname: self._openDatabase(t))

        # pop 1st from recent list if exceeding limit
        recent_open_num=self.settings.value('file/recent_open_num',type=int)
        if len(recent)>recent_open_num:
            recent.pop(0)

        self.settings.setValue('file/recent_open',recent)

        return


    @pyqtSlot()
    def saveDatabaseTriggered(self):
        self.main_frame.saveToDatabase()
        return


    @pyqtSlot()
    def closeDatabaseTriggered(self,ask=True):

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm Close',
                    'Save and close current library?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):
            self.main_frame.clearData()
            self.is_loaded=False

            self.import_action.setEnabled(False)
            self.export_action.setEnabled(False)

            self.current_lib=None
            self.current_lib_folder=None
            self.settings.setValue('saving/current_lib_folder','')
            self.setWindowTitle('MEI-TING TRUNK %s' %__version__)
            self.main_frame.auto_save_timer.stop()

            self.logger.info('Stop auto save timer.')
            self.logger.info('Database closed.')

            return True
        else:
            return False


    @pyqtSlot()
    def helpMenuTriggered(self,action):
        self.logger.info('action=%s, action.text()=%s' %(action,action.text()))
        return


    @pyqtSlot()
    def preferenceTriggered(self):

        diag=PreferenceDialog(self.settings,parent=self)
        diag.exec_()

        return


    @pyqtSlot()
    def importTriggered(self):

        diag=ImportDialog(self.settings,parent=self)
        # for open newly imported database
        diag.open_lib_signal.connect(self._openDatabase)
        diag.exec_()

        return


    @pyqtSlot()
    def exportTriggered(self):

        diag=ExportDialog(self.settings,parent=self)
        diag.exec_()

        return


    @pyqtSlot(QtWidgets.QAction)
    def viewChangeTriggered(self, action):
        """Change widget visibility in response to View menu actions

        Args:
            action (QAction): QAction in View menu
        """

        action_text=action.text()

        self.logger.info('View change action = %s' %action_text)

        if action_text=='Toggle Filter List':
            self.main_frame.foldFilterButtonClicked()
        elif action_text=='Toggle Tab Pane':
            self.main_frame.foldTabButtonClicked()
        elif action_text=='Toggle Status bar':
            self.main_frame.statusbarViewChange()
        else:
            self.main_frame.metaTabViewChange(action_text)

        return


    @pyqtSlot(str,bool)
    def viewChangeResponse(self, view_name, state):
        """Store widget visibility states in response to hide/show buttons

        Args:
            view_name (str): name of a widget view action, also the key
                             in view_action_dict. See the View menu creation
                             section in initUI().

            state (bool): Visibility state of a widget.
        """

        self.view_action_dict[view_name].setChecked(state)

