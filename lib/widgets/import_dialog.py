import os
import shutil
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt,\
        pyqtSignal,\
        pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialogButtonBox
import resources
from .. import sqlitedb
from .. import bibparse
from .. import risparse
from ..tools import getHLine, createFolderTree, iterTreeWidgetItems, autoRename
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

        #---------------Folder choice section---------------
        label=QtWidgets.QLabel('''
        Choose folders to export documents. <br/>
        This will copy documents (e.g. PDFs) from the
        <span style="font:bold;">"_collections"</span>
        folder to a separate folder under <span style="font:bold;">"%s/"</span>
        ''' %self.settings.value('saving/current_lib_folder',str))
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        va.addWidget(label)

        #if self.folder_tree:
            #self.clearFolderTreeState()
            #va.addWidget(self.folder_tree)
        #else:
            #va.addWidget(QtWidgets.QLabel('Library empty'))
            #self.export_button.setEnabled(False)

        return scroll


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

