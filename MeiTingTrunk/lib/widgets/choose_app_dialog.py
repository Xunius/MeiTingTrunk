'''
Dialog for choosing a default editor.


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
from PyQt5.QtGui import QPixmap
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtCore import Qt, pyqtSlot, QDir

LOGGER=logging.getLogger(__name__)



class ChooseAppDialog(QtWidgets.QDialog):

    def __init__(self, title, app_type, settings, parent=None):

        super(self.__class__,self).__init__(parent=parent)

        self.settings=settings

        self.setWindowTitle(title)
        self.resize(300,100)

        va=QtWidgets.QVBoxLayout(self)

        label=QtWidgets.QLabel('Give the command to launch editor (E.g. vim)')
        va.addWidget(label)


        default=self.settings.value(app_type, type=str)
        self.le=QtWidgets.QLineEdit(self)
        self.le.setText(default)

        #self.choose_button=QtWidgets.QPushButton('Choose')
        #self.choose_button.clicked.connect(self.chooseButtonClicked)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.le)
        #ha.addWidget(self.choose_button)

        va.addLayout(ha)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        va.addWidget(self.buttons)


    @pyqtSlot()
    def chooseButtonClicked(self):

        #fname = QtWidgets.QFileDialog.getOpenFileName(self,
                #'Choose application',
                #'',
                #QDir.Executable)[0]

        # this doesn't work
        diag=QtWidgets.QFileDialog()
        diag.setFilter(QDir.Executable)
        fname= diag.exec_()
        self.le.setText(fname)

        return





