import os
import shutil
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QRegExp
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtGui import QFont, QRegExpValidator
from .. import sqlitedb
from .. import bibparse
from .. import risparse
from ..tools import getHLine, createFolderTree, iterTreeWidgetItems, autoRename
from .threadrun_dialog import ThreadRunDialog
from .fail_dialog import FailDialog

LOGGER=logging.getLogger(__name__)




class CreateNewLibDialog(QtWidgets.QDialog):
    def __init__(self,settings,parent):

        super(CreateNewLibDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.resize(500,250)
        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',10,QFont.Bold)
        self.setWindowTitle('Create New Library')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout(self)

        #---------------------Lib name---------------------
        label=QtWidgets.QLabel('Name your library')
        #label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        v_layout.addWidget(label)

        self.lib_name_le=QtWidgets.QLineEdit()
        regex=QRegExp("[a-z-A-Z_\d]+")
        validator = QRegExpValidator(regex)
        self.lib_name_le.setValidator(validator)

        label=QtWidgets.QLabel('(Only alphanumeric characters and "-", "_" are allowed)')
        v_layout.addWidget(label)

        #ha=QtWidgets.QHBoxLayout()
        v_layout.addWidget(self.lib_name_le)
        #ha.addWidget(label)

        #v_layout.addLayout(ha)
        v_layout.addWidget(getHLine())

        #-------------------Save folder-------------------
        storage_folder=self.settings.value('saving/storage_folder',str)

        label=QtWidgets.QLabel('Storage Folder')
        #label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        v_layout.addWidget(label)

        self.folder_le=QtWidgets.QLineEdit(self)
        #self.folder_le.setPlaceholderText(storage_folder)
        self.folder_le.setText(storage_folder)

        self.open_button=QtWidgets.QPushButton(self)
        self.open_button.setText('Open')
        self.open_button.clicked.connect(lambda: self.dirChooseButtonClicked(
            self.folder_le))

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.folder_le)
        ha.addWidget(self.open_button)
        v_layout.addLayout(ha)

        #------------------Dialog buttons------------------
        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                Qt.Horizontal, self)

        self.buttons.accepted.connect(self.okClicked)
        self.buttons.rejected.connect(self.reject)

        v_layout.addStretch()
        v_layout.addWidget(self.buttons)


    @pyqtSlot(QtWidgets.QLineEdit)
    def dirChooseButtonClicked(self, le):

        storage_folder=self.settings.value('saving/storage_folder',str)
        fname = QtWidgets.QFileDialog.getExistingDirectory(self,
                'Choose a folder to save library files',
                storage_folder)

        if fname:
            print('# <dirChooseButtonClicked>: fname = ',fname)
            #LOGGER.info('Choose file name %s' %fname)
            le.setText(fname)

        return


    @pyqtSlot()
    def okClicked(self):

        lib_name=self.lib_name_le.text()
        fname=self.folder_le.text()
        if lib_name=='':
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Input needed')
            msg.setText("Library name can't be empty")
            msg.exec_()
            return

        if fname=='':
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Input needed')
            msg.setText("Choose a folder to save library files.")
            msg.exec_()
            return

        self.accept()


