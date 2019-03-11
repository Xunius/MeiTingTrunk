import os
import logging
import logging.config
import sqlite3
import pathlib
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QIcon, QFont, QBrush, QColor

import _MainFrame
from lib import sqlitedb
from lib.widgets import PreferenceDialog, ExportDialog, Master, ThreadRunDialog
import resource

from main import __version__

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


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow,self).__init__()

        self.logger=logging.getLogger('default_logger')
        self.settings=self.loadSettings()
        self.is_loaded=False

        self.initUI()

        self.main_frame=_MainFrame.MainFrame(self.settings)
        self.setCentralWidget(self.main_frame)

        recent=self.settings.value('file/recent_open',[],str)
        if isinstance(recent,str) and recent=='':
            recent=[]
        if self.settings.value('file/auto_open_last',type=int) and len(recent)>0:
            # add a delay, otherwise splash won't show
            QTimer.singleShot(100, lambda: self._openDatabase(recent[-1]))

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
            settings.setValue('file/recent_open', [])
            settings.setValue('file/recent_open_num', 2)
            settings.setValue('file/auto_open_last', 1)

            storage_folder=os.path.join(str(pathlib.Path.home()),
                    'Documents/MeiTingTrunk')
            settings.setValue('saving/storage_folder', storage_folder)

            settings.setValue('saving/auto_save_min', 1),
            settings.setValue('saving/rename_files', 1)
            settings.setValue('saving/rename_file_replace_space', 1)

            settings.setValue('duplicate_min_score', 60)

            settings.setValue('import/default_add_action', 'Add PDF File')

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

            print('# <loadSettings>: Create folder %s' %storage_folder)
            self.logger.info('Create folder %s' %storage_folder)


        return settings

    def loadSettings(self):
        settings=self.initSettings()

        print('# <loadSettings>: settings.fielName()=%s' %settings.fileName())
        self.logger.info('settings.fielName()=%s' %settings.fileName())

        return settings


    def initUI(self):
        self.setWindowTitle('MEI-TING TRUNK %s' %__version__)
        self.setGeometry(100,100,1200,900)    #(x_left,y_top,w,h)
        #self.setWindowIcon(QIcon('img.png'))

        self.menu_bar=self.menuBar()

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
        print('# <initUI>: recent=',recent,type(recent))

        if recent and recent_num>0:
            for rii in recent:
                recentii=self.recent_open_menu.addAction(rii)
                recentii.triggered.connect(lambda x,t=rii: self._openDatabase(t))

        self.edit_menu=self.menu_bar.addMenu('&Edit')
        preference_action=QtWidgets.QAction('Preferences',self)
        preference_action.setIcon(QIcon.fromTheme('preferences-system'))
        self.edit_menu.addAction(preference_action)

        self.tool_menu=self.menu_bar.addMenu('&Tool')
        self.import_action=QtWidgets.QAction('Import', self)
        self.export_action=QtWidgets.QAction('Export', self)
        self.tool_menu.addAction(self.import_action)
        self.tool_menu.addAction(self.export_action)
        if not self.is_loaded:
            self.import_action.setEnabled(False)
            self.export_action.setEnabled(False)

        self.help_menu=self.menu_bar.addMenu('&Help')
        self.help_menu.addAction('Help')

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

        self.show()

    def closeEvent(self,event):
        print('# <closeEvent>: settings.sync()')
        self.logger.info('settings.sync()')
        self.settings.sync()



    #######################################################################
    #                           Menu bar actions                           #
    #######################################################################

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

            print('createDatabaseTriggered: database file:',fname)
            lib_folder=os.path.join(storage_folder,lib_name)
            if not os.path.exists(lib_folder):
                os.makedirs(lib_folder)

            print('# <loadSettings>: Create folder %s' %lib_folder)
            self.logger.info('Create folder %s' %lib_folder)

            def func(jobid,fname,storage_folder,rename_files):
                try:
                    result=sqlitedb.createNewDatabase(fname, lib_folder,
                            rename_files)
                    return 0,jobid,result
                except:
                    return 1,jobid,None

            ThreadRunDialog(func,
                [(0,fname,storage_folder,self.settings.value('saving/rename_files'))],
                show_message='Creating new database...',
                max_threads=1,
                get_results=False,
                close_on_finish=True,
                progressbar_style='busy',
                parent=None)

            #self.main_frame.status_bar.showMessage('Creating new database...')
            #sqlitedb.createNewDatabase(fname,storage_folder,
                #self.settings.value('saving/rename_files'))
            #self.main_frame.status_bar.clearMessage()

            self._openDatabase(fname)

        return



    def openDatabaseTriggered(self):

        # close current if loaded
        if self.is_loaded:
            do=self.closeDatabaseTriggered()
            if not do:
                return

        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a sqlite file',
     '',"sqlite files (*.sqlite);; All files (*)")[0]

        if fname:
            try:
                self._openDatabase(fname)
            except:
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText("Oopsi.")
                msg.setInformativeText("Failed to open database file\n    %s" %fname)
                msg.exec_()
            return

    def _openDatabase(self,fname):

        # close current if loaded. For open recent calls
        if self.is_loaded:
            do=self.closeDatabaseTriggered()
            if not do:
                return

        if not os.path.exists(fname):
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
                print('# <_openDatabase>: fname in recent')
                recent.remove(fname)
                self.settings.setValue('file/recent_open', recent)

                for actionii in self.recent_open_menu.findChildren(
                        QtWidgets.QAction):
                    if actionii.text()==fname:
                        self.recent_open_menu.removeAction(actionii)

            return

        self.main_frame.status_bar.showMessage('Opening database...')
        QtWidgets.QApplication.processEvents() # needed?
        # These won't work, the sqlitedb is in the same GUI thread.
        #self.main_frame.progressbar.setVisible(True)
        #self.main_frame.progressbar.setMaximum(0)
        db = sqlite3.connect(fname)

        print('# <openDatabaseTriggered>: Connected to database: %s' %fname)
        self.logger.info('Connected to database: %s' %fname)

        self.db=db
        meta_dict,folder_data,folder_dict=sqlitedb.readSqlite(db)
        self.main_frame.loadLibTree(db,meta_dict,folder_data,folder_dict)
        self.main_frame.status_bar.clearMessage()
        self.main_frame.progressbar.setVisible(False)

        self.is_loaded=True

        # store folder name
        lib_name=os.path.splitext(os.path.split(fname)[1])[0]
        storage_folder=self.settings.value('saving/storage_folder')
        self.current_lib=lib_name
        self.current_lib_folder=os.path.join(storage_folder,lib_name)
        self.settings.setValue('saving/current_lib_folder', self.current_lib_folder)

        print('# <_openDatabase>: current_lib=',self.current_lib)
        print('# <_openDatabase>: current_lib_folder=',self.current_lib_folder)

        self.main_frame.auto_save_timer.start()
        print('# <openDatabaseTriggered>: Start auto save timer.')
        self.logger.info('Start auto save timer.')

        self.import_action.setEnabled(True)
        self.export_action.setEnabled(True)

        recent=self.settings.value('file/recent_open',[],str)
        if isinstance(recent,str) and recent=='':
            recent=[]
        if fname not in recent:
            recent.append(fname)
            recentii=self.recent_open_menu.addAction(fname)
            recentii.triggered.connect(lambda x,t=fname: self._openDatabase(t))

        recent_open_num=self.settings.value('file/recent_open_num',type=int)
        if len(recent)>recent_open_num:
            recent.pop(0)

        self.settings.setValue('file/recent_open',recent)

        return

    def saveDatabaseTriggered(self):
        self.main_frame.saveToDatabase()
        return

    def closeDatabaseTriggered(self):

        choice=QtWidgets.QMessageBox.question(self, 'Confirm Close',
                'Save and close current library?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice==QtWidgets.QMessageBox.Yes:
            #self.main_frame.saveToDatabase()
            self.main_frame.clearData()
            self.is_loaded=False

            self.import_action.setEnabled(False)
            self.export_action.setEnabled(False)

            self.current_lib=None
            self.current_lib_folder=None
            self.settings.setValue('saving/current_lib_folder','')
            self.main_frame.auto_save_timer.stop()
            print('# <closeDatabaseTriggered>: Stop auto save timer.')
            self.logger.info('Stop auto save timer.')

            return True
        else:
            return False



    def helpMenuTriggered(self,action):
        print('# <helpMenuTriggered>: action=%s, action.text()=%s' %(action,action.text()))
        self.logger.info('action=%s, action.text()=%s' %(action,action.text()))
        return


    def preferenceTriggered(self):
        diag=PreferenceDialog(self.settings,parent=self)
        diag.exec_()

    def importTriggered(self):
        return

    def exportTriggered(self):
        diag=ExportDialog(self.settings,parent=self)
        diag.exec_()
        return


