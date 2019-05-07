'''
tab widget containing PDF viewer and thumbnail viewer.

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
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QUrl
from PyQt5 import QtWebEngineWidgets
from ..tools import clearLayout

LOGGER=logging.getLogger(__name__)

PDFJS = os.path.join(__file__, '../../pdfjs/web/viewer.html')


def getPath(relpath):
    '''Convert a relative file path to file URL

    Args:
        relpath (str): relative file path, wrt the lib_folder

    Returns:
        p (str): file url
    '''

    if not os.path.isabs(relpath):
        p=os.path.abspath(relpath)
    else:
        p=relpath

    p=QUrl.fromLocalFile(p).toString()

    return p


class PDFFrame(QtWebEngineWidgets.QWebEngineView):

    def __init__(self, parent=None):
        super().__init__()

        self.pdfjs_path=getPath(PDFJS)


    def loadFile(self, libfolder, relpath):

        filepath=os.path.join(libfolder, relpath)
        pdf_path=getPath(filepath)
        url='%s?file=%s' %(self.pdfjs_path, pdf_path)
        url=QUrl.fromUserInput(url)

        LOGGER.debug('pdf_path = %s' %pdf_path)
        LOGGER.debug('url = %s' %url)

        self.load(url)

        return


class PDFPreviewer(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.layout=QtWidgets.QVBoxLayout(self)


    def clearLayout(self):

        clearLayout(self.layout)

        return




