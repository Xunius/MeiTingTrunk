import os
import shutil
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialogButtonBox
from ..tools import getHLine
from .threadrun_dialog import ThreadRunDialog
#from import_mendeley import importMendeley
import import_mendeley

LOGGER=logging.getLogger(__name__)




class ImportDialog(QtWidgets.QDialog):

    open_lib_signal=pyqtSignal(str)

    def __init__(self,settings,parent):

        super(ImportDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(900,600)
        self.setWindowTitle('Bulk Import')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Choose Import Type')
        title_label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(title_label)

        v_layout.addLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        #self.list.setSizePolicy(getXMinYExpandSizePolicy())
        self.cate_list.setMaximumWidth(200)
        h_layout.addWidget(self.cate_list)

        #self.cate_list.setStyleSheet('''
            #QListWidget::item { border: 0px solid rgb(235,235,240);
            #font: 14px;
            #background-color: rgb(205,205,245);
            #color: rgb(100,10,13) };
            #background-color: rgb(230,234,235);
            #''')

        self.cate_list.addItems(['Import From Mendeley', 'Import From Zotero',
            'Import From EndNote'])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Close,
            Qt.Horizontal, self)
        self.import_button=self.buttons.addButton('Import',
                QDialogButtonBox.ApplyRole)

        self.import_button.clicked.connect(self.doImport)
        self.buttons.rejected.connect(self.reject)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)



    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):

        item_text=item.text()
        LOGGER.debug('item.text() = %s' %item_text)

        if self.content_vlayout.count()>1:
            self.content_vlayout.removeWidget(self.content_frame)

        if item_text=='Import From Mendeley':
            self.content_frame=self.loadImportMendeley()
        elif item_text=='Import From Zotero':
            self.content_frame=self.loadImportZotero()
        elif item_text=='Import From EndNote':
            self.content_frame=self.loadImportEndNote()

        self.content_vlayout.insertWidget(0,self.content_frame)

        return


    def createFrame(self,title):

        frame=QtWidgets.QWidget(self)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        va=QtWidgets.QVBoxLayout()
        frame.setLayout(va)
        va.setSpacing(int(va.spacing()*2))

        label=QtWidgets.QLabel(title)
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        va.addWidget(label)
        #va.addWidget(getHLine(self))

        return scroll, va


    def loadImportMendeley(self):

        scroll,va=self.createFrame('Import From Mendeley')
        self.current_task='mendeley'

        label=QtWidgets.QLabel('(Notice: Only Mendeley version < 1.19 can be imported. Later version of Mendeley encrypts the database file.)')
        label.setStyleSheet('Font: bold')
        label.setWordWrap(True)
        va.addWidget(label)

        #---------------------Lib name---------------------
        '''
        label=QtWidgets.QLabel('Name your library')
        va.addWidget(label)

        self.lib_name_le=QtWidgets.QLineEdit()
        regex=QRegExp("[a-z-A-Z_\d]+")
        validator = QRegExpValidator(regex)
        self.lib_name_le.setValidator(validator)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.lib_name_le)

        label=QtWidgets.QLabel('(Only alphanumeric characters and "-", "_" are allowed)')
        ha.addWidget(label)
        va.addLayout(ha)
        '''
        #-----------------New sqlite file-----------------
        label=QtWidgets.QLabel('Name your library')
        va.addWidget(label)

        self.lib_name_le=QtWidgets.QLineEdit()
        button=QtWidgets.QPushButton(self)
        button.setText('Open')
        button.clicked.connect(lambda: self.outFileChooseButtonClicked(
            self.lib_name_le))
        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.lib_name_le)
        ha.addWidget(button)
        va.addLayout(ha)

        va.addWidget(getHLine())

        #-----------------Sqlite file sel-----------------
        label=QtWidgets.QLabel('''Select the sqlite database file <br/>
        Default location: <br/>
        <br/>
        * Linux: ~/.local/share/data/Mendeley Ltd./Mendeley Desktop/<your_email@www.mendeley.com.sqlite. <br/>
        '''
        )
        label.setTextFormat(Qt.RichText)
        va.addWidget(label)

        ha=QtWidgets.QHBoxLayout()

        self.mendeley_file_le=QtWidgets.QLineEdit()

        button=QtWidgets.QPushButton(self)
        button.setText('Open')
        button.clicked.connect(lambda: self.importFileChooseButtonClicked(
            self.mendeley_file_le))

        ha.addWidget(self.mendeley_file_le)
        ha.addWidget(button)

        va.addLayout(ha)

        #----------------------Notice----------------------

        va.addStretch()

        return scroll


    @pyqtSlot(QtWidgets.QLineEdit)
    def outFileChooseButtonClicked(self, le):

        storage_folder=self.settings.value('saving/storage_folder',str)
        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Name your sqlite database file',
                storage_folder,
                "sqlite Files (*.sqlite);; All files (*)")[0]

        if fname:
            # make sure has .sqlite ext
            dirname,filename=os.path.split(fname)
            lib_name,ext=os.path.splitext(filename)
            if ext=='':
                filename='%s.sqlite' %lib_name
                fname=os.path.join(dirname,filename)

            LOGGER.info('Choose file name %s' %fname)
            le.setText(fname)

        return


    @pyqtSlot(QtWidgets.QLineEdit)
    def importFileChooseButtonClicked(self, le):

        fname = QtWidgets.QFileDialog.getOpenFileName(self,
                'Select your Mendeley sqlite database file',
                '',
                "sqlite Files (*.sqlite);; All files (*)")[0]

        if fname:
            LOGGER.info('Choose file name %s' %fname)
            le.setText(fname)

        return


    def loadImportZotero(self):

        scroll,va=self.createFrame('Import From Zotero')
        self.current_task='zotero'

        return scroll


    def loadImportEndNote(self):

        scroll,va=self.createFrame('Import From EndNote')
        self.current_task='endnote'

        return scroll


    def doImport(self):

        LOGGER.info('task = %s' %self.current_task)

        if self.current_task=='mendeley':
            self.doMendeleyImport1()
        elif self.current_task=='zotero':
            pass
        elif self.current_task=='endnote':
            pass

        return


    def doMendeleyImport1(self):

        file_out_name=self.lib_name_le.text()
        if file_out_name=='':
            self.popUpGiveName()
            return

        if os.path.exists(file_out_name):
            choice=QtWidgets.QMessageBox.question(self, 'sqlite file already exists',
                    'Overwrite the file %s?' %file_out_name,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

            if choice==QtWidgets.QMessageBox.Yes:
                os.remove(file_out_name)
            if choice==QtWidgets.QMessageBox.No:
                return

        file_in_name=self.mendeley_file_le.text()
        if file_in_name=='':
            self.popUpGiveFile()
            return

        if not os.path.exists(file_in_name):
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('File not found')
            msg.setText("Can't find input file %s" %file_in_name)
            msg.exec_()
            return

        LOGGER.debug('file_in_name = %s' %file_in_name)
        LOGGER.debug('file_out_name = %s' %file_out_name)
        LOGGER.debug('Launching thread...')

        '''
        self.master1=Master(import_mendeley.importMendeleyPreprocess,
                [(0, file_in_name, file_out_name)],
                1, self.parent.main_frame.progressbar,
                'busy', self.parent.main_frame.status_bar,
                'Connecting databases...')

        self.master1.all_done_signal.connect(self.doMendeleyImport2)
        self.master1.run()
        '''
        #------------------Run in thread------------------
        self.thread_run_dialog1=ThreadRunDialog(
                import_mendeley.importMendeleyPreprocess,
                [(0, file_in_name, file_out_name)],
                show_message='Connecting database...',
                max_threads=1,
                get_results=True,
                close_on_finish=True,
                progressbar_style='busy',
                post_process_func=None,
                parent=self)

        self.thread_run_dialog1.master.all_done_signal.connect(self.doMendeleyImport2)
        self.thread_run_dialog1.exec_()

        return


    def doMendeleyImport2(self):

        file_out_name=self.lib_name_le.text()
        step1_results=self.thread_run_dialog1.results[0]
        rec, _, dbin, dbout, docids,lib_folder,lib_name=step1_results
        LOGGER.info('return code of importMendeleyPreprocess: %s' %rec)

        if rec==1:
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Error)
            msg.setWindowTitle('Oopsie')
            msg.setText("Failed to process database files.         ")
            msg.exec_()
            LOGGER.warning('Failed to run importMendeleyPreprocess().')

            if os.path.exists(file_out_name):
                os.remove(file_out_name)
                LOGGER.info('Remove sqlite database file %s' %file_out_name)
            if os.path.exists(lib_folder):
                shutil.rmtree(lib_folder)
                LOGGER.info('Remove lib folder %s' %lib_folder)

            return

        rename_files=self.settings.value('saving/rename_files', 1)

        LOGGER.debug('rename_files = %s' %rename_files)

        #-----------------Prepare job list-----------------
        job_list=[]
        for ii, docii in enumerate(docids):
            job_list.append((ii, dbin, dbout, lib_name, lib_folder,
                rename_files, ii, docii))

        job_list.append((-1, dbin, dbout, lib_name, lib_folder,
            rename_files, ii, None))

        #------------------Run in thread------------------
        self.thread_run_dialog2=ThreadRunDialog(import_mendeley.importMendeleyCopyData,
                job_list,
                show_message='Transfering data...',
                max_threads=1,
                get_results=False,
                close_on_finish=False,
                progressbar_style='classic',
                post_process_func=None,
                parent=self)

        self.thread_run_dialog2.master.all_done_signal.connect(lambda: self.postImport(
            file_out_name))

        self.thread_run_dialog2.exec_()

        return


    @pyqtSlot()
    def postImport(self, file_name):

        step2_results=self.thread_run_dialog2.master.results[-1]
        rec,_=step2_results
        LOGGER.info('return code of importMendeleyCopyData: %s' %rec)

        if rec==0:
            choice=QtWidgets.QMessageBox.question(self,
                    'Open newly imported library?',
                    'Open newly imported library?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

            if choice==QtWidgets.QMessageBox.Yes:
                LOGGER.info('Emitting open lib signal. File = %s' %file_name)
                self.thread_run_dialog2.accept()
                self.reject()

                self.open_lib_signal.emit(file_name)

        elif rec==1:
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Oopsie')
            msg.setText("Failed to import Mendeley database files.")
            msg.exec_()

            LOGGER.warning('Failed to run importMendeleyCopyData().')
            dirname,fname=os.path.split(file_name)
            lib_folder=os.path.join(dirname,os.path.splitext(fname)[0])

            if os.path.exists(file_name):
                os.remove(file_name)
                LOGGER.info('Remove sqlite database file %s' %file_name)
            if os.path.exists(lib_folder):
                shutil.rmtree(lib_folder)
                LOGGER.info('Remove lib folder %s' %lib_folder)

            self.thread_run_dialog2.accept()

            return

        return



    def popUpGiveName(self):

        msg=QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Input Needed')
        msg.setText("Give a name to the library.")
        msg.exec_()

        return


    def popUpGiveFile(self):

        msg=QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Input Needed')
        msg.setText("Choose file to be imported.")
        msg.exec_()

        return

