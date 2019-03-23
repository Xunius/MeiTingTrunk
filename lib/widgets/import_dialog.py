import os
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator
from PyQt5.QtWidgets import QDialogButtonBox
import resources
from .. import sqlitedb
from ..tools import getHLine
from .threadrun_dialog import ThreadRunDialog
from .fail_dialog import FailDialog

LOGGER=logging.getLogger(__name__)




class ImportDialog(QtWidgets.QDialog):
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
        self.export_button=self.buttons.addButton('Import',
                QDialogButtonBox.ApplyRole)

        self.export_button.clicked.connect(self.doImport)
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

        label=QtWidgets.QLabel('(Notice: Only Mendeley version < 1.9 can be imported. Later version of Mendeley encrypts the database file.)')
        label.setStyleSheet('Font: bold')
        label.setWordWrap(True)
        va.addWidget(label)

        #---------------------Lib name---------------------
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
        button.clicked.connect(lambda: self.fileChooseButtonClicked(
            self.mendeley_file_le))

        ha.addWidget(self.mendeley_file_le)
        ha.addWidget(button)

        va.addLayout(ha)

        #----------------------Notice----------------------

        va.addStretch()

        return scroll


    @pyqtSlot(QtWidgets.QLineEdit)
    def fileChooseButtonClicked(self, le):

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
            pass
        elif self.current_task=='zotero':
            pass
        elif self.current_task=='endnote':
            pass

        return


    def popUpChooseFolder(self):

        msg=QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Input Needed')
        msg.setText("Choose at least one folder to process.")
        msg.exec_()

        return

