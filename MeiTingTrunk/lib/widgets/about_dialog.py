'''
About dialog.


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
from PyQt5.QtCore import Qt

LOGGER=logging.getLogger(__name__)
REPO_URL='https://github.com/Xunius/MeiTingTrunk'



class AboutDialog(QtWidgets.QDialog):

    def __init__(self, version, parent=None):

        super(self.__class__,self).__init__(parent=parent)

        self.version=version

        logo=QPixmap(':/logo.png')
        logo_label=QtWidgets.QLabel(self)
        logo_label.setPixmap(logo)

        self.setWindowTitle('About MeiTing Trunk')

        va=QtWidgets.QVBoxLayout(self)
        va.addWidget(logo_label)

        label=QtWidgets.QLabel('MeiTing Truck')
        label.setStyleSheet('font: bold')
        va.addWidget(label, 0 , Qt.AlignHCenter)
        va.addWidget(QtWidgets.QLabel(self.version), 0 , Qt.AlignHCenter)
        va.addWidget(QtWidgets.QLabel('An open source reference management tool developed in PyQt5 and Python3.'), 0 , Qt.AlignHCenter)
        va.addWidget(QtWidgets.QLabel('Copyright 2018-2019 Guang-zhi XU'), 0 , Qt.AlignHCenter)
        va.addWidget(QtWidgets.QLabel('Please consider contributing. Repo:'),
                0 , Qt.AlignHCenter)
        va.addWidget(QtWidgets.QLabel(REPO_URL), 0 , Qt.AlignHCenter)

        logfolder=os.path.abspath(__file__)
        logfolder=os.path.dirname(logfolder)
        logfolder=os.path.dirname(logfolder)
        logfolder=os.path.dirname(logfolder)
        logfile1=os.path.join(logfolder, 'MTT.log')
        logfile2=os.path.join(logfolder, 'MTT.log.1')
        va.addWidget(QtWidgets.QLabel('Log files are at:'), 0,
                Qt.AlignHCenter)
        va.addWidget(QtWidgets.QLabel('%s and\n %s' %(logfile1, logfile2)), 0,
                Qt.AlignHCenter)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        va.addWidget(self.buttons)







