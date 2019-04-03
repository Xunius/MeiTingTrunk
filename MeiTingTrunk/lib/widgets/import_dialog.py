'''
Import dialog.

MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import shutil
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialogButtonBox, QStyle
from ..tools import getHLine
from .threadrun_dialog import ThreadRunDialog
#from import_mendeley import importMendeley
from .. import import_mendeley

LOGGER=logging.getLogger(__name__)


class ResultDialog(QtWidgets.QDialog):

    def __init__(self,main_text='',info_text='',detailed_text='',parent=None):
        super(self.__class__,self).__init__(parent=parent)

        self.main_text=main_text
        self.info_text=info_text
        self.detailed_text=detailed_text

        self.setWindowTitle('Import Result')
        self.resize(450,250)
        self.grid=QtWidgets.QGridLayout(self)

        icon=self.style().standardIcon(QStyle.SP_MessageBoxInformation)
        icon_label=QtWidgets.QLabel()
        icon_label.setPixmap(icon.pixmap(QSize(32,32)))
        self.grid.addWidget(icon_label,0,0)

        self.main_text_label=QtWidgets.QLabel(main_text)
        label_font=QFont('Serif',12,QFont.Bold)
        self.main_text_label.setFont(label_font)
        self.grid.addWidget(self.main_text_label,0,1)

        self.info_text_label=QtWidgets.QLabel(info_text)
        self.info_text_label.setTextFormat(Qt.RichText)
        self.info_text_label.setWordWrap(True)
        self.grid.addWidget(self.info_text_label,1,1,1,2)

        self.open_lib_checkbox=QtWidgets.QCheckBox('Open Imported Library?')
        self.open_lib_checkbox.setChecked(True)
        self.grid.addWidget(self.open_lib_checkbox,2,0)

        self.buttons=QDialogButtonBox(self)

        self.ok_button=QtWidgets.QPushButton('Ok')
        self.ok_button.setDefault(True)
        self.ok_button.setAutoDefault(True)

        self.detail_button=QtWidgets.QPushButton('Show Details')
        self.detail_button.setDefault(False)
        self.detail_button.setAutoDefault(False)
        self.detail_button.clicked.connect(self.detailButtonClicked)

        #self.create_folder_button=QtWidgets.QPushButton('Show Failed Docs')
        #self.create_folder_button.setDefault(False)
        #self.create_folder_button.setAutoDefault(False)
        #self.create_folder_button.clicked.connect(self.createFailList)

        self.buttons.addButton(self.ok_button,QDialogButtonBox.AcceptRole)
        self.buttons.addButton(self.detail_button,QDialogButtonBox.ActionRole)
        #self.buttons.addButton(self.create_folder_button,
                #QDialogButtonBox.ActionRole)

        self.grid.addWidget(self.buttons,3,2)

        self.text_edit=QtWidgets.QTextEdit(self)
        self.text_edit.setText(detailed_text)
        self.text_edit.setVisible(False)

        self.grid.addWidget(self.text_edit,4,0,1,3)

        self.buttons.accepted.connect(self.accept)

        #self.exec_()

    def setText(self,text):
        self.main_text=text
        self.main_text_label.setText(text)
        return

    def setInformativeText(self,text):
        self.info_text=text
        self.info_text_label.setText(text)
        return

    def setDetailedText(self,text):
        self.detailed_text=text
        self.text_edit.setText(text)
        return


    def detailButtonClicked(self):
        if self.detailed_text=='':
            return

        if self.text_edit.isVisible():
            self.detail_button.setText('Show Details')
            self.text_edit.setVisible(False)
        else:
            self.detail_button.setText('Hide Details')
            self.text_edit.setVisible(True)

        return

    #def createFailList(self):
        #self.create_fail_summary.emit()
        #return

    def accept(self):
        if self.open_lib_checkbox.isChecked():
            #print('# <accept>: open lib')
            #self.open_lib_signal.emit()
            super(self.__class__, self).accept()
        else:
            super(self.__class__, self).reject()



class ImportDialog(QtWidgets.QDialog):

    open_lib_signal=pyqtSignal(str)  # sqlite file name

    def __init__(self,settings,parent):
        '''
        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''

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
        '''Load widgets for a selected category

        Args:
            item (QListWidgetItem): selected category item.
        '''

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


    def createFrame(self, title):
        '''Create a template frame for a category page

        Args:
            title (str): title of the category

        Returns:
            scroll (QScrollArea): a scroll area.
            va (QVBoxLayout): the vertical box layout used in scroll.
        '''

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
        '''Load Mendeley import category page'''

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
        label.setWordWrap(True)
        va.addWidget(label)

        self.mendeley_file_le=QtWidgets.QLineEdit()
        button=QtWidgets.QPushButton(self)
        button.setText('Open')
        button.clicked.connect(lambda: self.importFileChooseButtonClicked(
            self.mendeley_file_le))

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.mendeley_file_le)
        ha.addWidget(button)

        va.addLayout(ha)

        #----------------------Notice----------------------
        va.addWidget(getHLine())
        va.addStretch()

        label=QtWidgets.QLabel('''Notice: Import will try to export the annotations (highlights, notes) you made in the Mendeley library. <br/>
                "Cananical" documents (those don't belong to any folder) will be put to the "Default" folder.''')
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        va.addWidget(label)


        return scroll


    @pyqtSlot(QtWidgets.QLineEdit)
    def outFileChooseButtonClicked(self, le):
        '''Prompt to select output sqlite file name and set it to lineedit'''

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
        '''Prompt to select input sqlite file name and set it to lineedit'''

        fname = QtWidgets.QFileDialog.getOpenFileName(self,
                'Select your Mendeley sqlite database file',
                '',
                "sqlite Files (*.sqlite);; All files (*)")[0]

        if fname:
            LOGGER.info('Choose file name %s' %fname)
            le.setText(fname)

        return


    def loadImportZotero(self):
        '''Load Zotero import category page'''

        scroll,va=self.createFrame('Import From Zotero')
        self.current_task='zotero'

        return scroll


    def loadImportEndNote(self):
        '''Load EndNote import category page'''

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
        '''Do Mendeley import, part 1

        This part is responsible for collecting arguments from widgets, and
        feed into importMendeleyPreprocess(). See import_mendeley.py for more
        details.
        '''

        #-----------Get output sqlite file name-----------
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

        #------------Get input sqlite file name------------
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

        self.thread_run_dialog1.master.all_done_signal.connect(
                self.doMendeleyImport2)
        self.thread_run_dialog1.exec_()

        return


    def doMendeleyImport2(self):
        '''Do Mendeley import, part 2

        After connecting to both sqlite databases, this part is responsible for
        copying document data over, and copying attachment files.
        See import_mendeley.importMendeleyCopyData() for more details.
        '''

        #-------------Get results from part 1-------------
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

            #----------------Remove sqlite file----------------
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
        self.job_list=[]
        for ii, docii in enumerate(docids):
            self.job_list.append((ii, dbin, dbout, lib_name, lib_folder,
                rename_files, ii, docii))

        # this last job signals a sqlite commit
        self.job_list.append((-1, dbin, dbout, lib_name, lib_folder,
            rename_files, ii, None))

        #------------------Run in thread------------------
        self.thread_run_dialog2=ThreadRunDialog(
                import_mendeley.importMendeleyCopyData,
                self.job_list,
                show_message='Transfering data...',
                max_threads=1,
                get_results=False,
                close_on_finish=False,
                progressbar_style='classic',
                post_process_func=None,
                parent=self)

        self.thread_run_dialog2.master.all_done_signal.connect(
                lambda: self.postImport(file_out_name))
        self.thread_run_dialog2.exec_()

        return


    @pyqtSlot()
    def postImport(self, file_name):
        '''Show feedbacks after Mendeley import

        Args:
            file_name (str): output sqlite file path.
        '''

        #-------------Get results from part 2-------------
        step2_results=self.thread_run_dialog2.master.results
        rec=step2_results[-1][0]  # last step rec
        LOGGER.info('return code of importMendeleyCopyData: %s' %rec)

        #---------Succeeded in committing database---------
        if rec==0:
            fail_list=[]
            pdf_fail_list=[]

            for recii, jobii, fail_fileii in step2_results[:-1]:
                if recii==1:
                    docii=self.job_list[jobii][7]
                    entryii='* docid = %s' %docii
                    LOGGER.warning('Failed to import doc id = %s' %docii)
                    fail_list.append(entryii)
                elif recii==2:
                    entryii='* PDF file(s) = %s' %fail_fileii
                    LOGGER.warning('Failed to export annotated pdf(s) %s'\
                            %fail_fileii)
                    pdf_fail_list.append(entryii)

            #-----------------Show failed jobs-----------------
            if len(fail_list)>0 or len(pdf_fail_list)>0:

                msg=ResultDialog()
                msg.setText('Errors encountered.')

                # only doc transfer failures
                if len(fail_list)>0 and len(pdf_fail_list)==0:
                    msg.setInformativeText('Failed to import some documents.')
                    fail_str='\n'.join(fail_list)
                    msg.setDetailedText(fail_str)

                # only pdf annotation export failures
                elif len(fail_list)==0 and len(pdf_fail_list)>0:
                    msg.setInformativeText('Failed to export annotations in some PDFs.')
                    fail_str='\n'.join(pdf_fail_list)
                    msg.setDetailedText(fail_str)

                # both doc transfer and pdf annotation export failures
                elif len(fail_list)>0 and len(pdf_fail_list)>0:
                    msg.setInformativeText('''
                    Failed to import some documents. <br/>
                    Failed to export annotations in some PDFs.''')
                    fail_str1='\n'.join(fail_list)
                    fail_str2='\n'.join(pdf_fail_list)
                    msg.setDetailedText('Failed documents:\n%s\n\nFailed PDFs:\n%s'\
                            %(fail_str1, fail_str2))

                choice=msg.exec_()

                # open new library
                if choice==1:
                    LOGGER.info('Emitting open lib signal. File = %s' %file_name)
                    self.thread_run_dialog2.accept()
                    self.reject()
                    self.open_lib_signal.emit(file_name)

            #------------------No failed jobs------------------
            else:
                choice=QtWidgets.QMessageBox.question(self, 'Import completed',
                        'Open new library?',
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

                # open new library
                if choice==QtWidgets.QMessageBox.Yes:
                    LOGGER.info('Emitting open lib signal. File = %s' %file_name)
                    self.thread_run_dialog2.accept()
                    self.reject()
                    self.open_lib_signal.emit(file_name)


        #------------Failed to commit database------------
        elif rec==1:
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Oopsie')
            msg.setText("Failed to write output database file.")
            msg.exec_()

            LOGGER.warning('Failed to commit output sqlite.')
            dirname,fname=os.path.split(file_name)
            lib_folder=os.path.join(dirname,os.path.splitext(fname)[0])

            #----------------Remove sqlite file----------------
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

