'''
A dialog to replace QMessageBox to display some error messages.
The default QMessageBox is very difficult to control its size.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from PyQt5.QtGui import QFont
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialogButtonBox, QStyle
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize


class FailDialog(QtWidgets.QDialog):
    create_fail_summary=pyqtSignal()

    def __init__(self,main_text='',info_text='',detailed_text='',parent=None):
        '''
        Args:
            main_text (str): main text set by setText().
            info_text (str): text set by setInformativeText().
            detailed_text (str): text set by setDetailedText().
            parent (QWidget): parent widget.
        '''

        super(self.__class__,self).__init__(parent=parent)

        self.main_text=main_text
        self.info_text=info_text
        self.detailed_text=detailed_text

        self.setWindowTitle('Error')
        self.resize(400,200)
        self.grid=QtWidgets.QGridLayout(self)

        icon=self.style().standardIcon(QStyle.SP_MessageBoxWarning)
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

        self.buttons=QDialogButtonBox(self)

        self.ok_button=QtWidgets.QPushButton('Ok')
        self.ok_button.setDefault(True)
        self.ok_button.setAutoDefault(True)

        self.detail_button=QtWidgets.QPushButton('Show Details')
        self.detail_button.setDefault(False)
        self.detail_button.setAutoDefault(False)
        self.detail_button.clicked.connect(self.detailButtonClicked)

        self.create_folder_button=QtWidgets.QPushButton('Show Failed Docs')
        self.create_folder_button.setDefault(False)
        self.create_folder_button.setAutoDefault(False)
        self.create_folder_button.clicked.connect(self.createFailList)

        self.buttons.addButton(self.ok_button,QDialogButtonBox.AcceptRole)
        self.buttons.addButton(self.detail_button,QDialogButtonBox.ActionRole)
        self.buttons.addButton(self.create_folder_button,
                QDialogButtonBox.ActionRole)

        self.grid.addWidget(self.buttons,2,2)

        self.text_edit=QtWidgets.QTextEdit(self)
        self.text_edit.setText(detailed_text)
        self.text_edit.setVisible(False)

        self.grid.addWidget(self.text_edit,3,0,1,3)

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

    def createFailList(self):
        self.create_fail_summary.emit()
        return
