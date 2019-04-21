#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Main GUI entrance.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import sys
import logging
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
from . import _MainWindow
from .version import __version__



dirname=os.path.split(__file__)[0]
LOG_CONFIG={
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                #'format': '<%(filename)s-%(funcName)s()>: %(asctime)s,%(levelname)s: %(message)s'},
                'format': '<%(filename)s-%(funcName)s()>: %(levelname)s: %(message)s'},
            },
        'handlers': {
            'default': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'filename': os.path.join(dirname,'MTT.log'),
                'mode': 'a',
                'maxBytes': 10*1024*1024,  # 10 M
                'backupCount': 1
                },
            },
        'root' : {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': True
            }
        }


# TODO:
# [NO] show docs in sub folders?
# [y] fold long fields in meta data tab?
# [y] create bib texts when clicking into the bibtex tab and changing doc
# [y] add icons to folders
# doc types, books, generic etc
# [NO] insert images to note?
# [y] add add folder functionality
# [indirectly y] add add doc functionalities, by doi
# [y] add add doc functionalities, by bib
# [y] add add doc functionalities, by RIS
# import from Mendeley, zotero, Endnote?
# [y] autosave
# auto backup
# export to text (clipboard, styles), bibtex, ris. citation styles things.
# [y] collapse side tab
# [y] seperate libraries
# [y] use resource file to load icons/images
# in note tab, add time stamps at left margin?
# [y] change meta dict key naming convention to distinguish string and list types:
#   e.g. authors -> authors_l, tag -> tag_l
# possible issue with local time with added time
# [y] add logger
# [y] get all bib entries for multiple selected docs?
# [y] right click menus
# [y] option menu
# [y] import/export menu
# [y] add trash can
# [y] sqlite text search: https://stackoverflow.com/questions/35020797/how-to-use-full-text-search-in-sqlite3-database-in-django
# PDF preview
# [y] add doc strings!!
# [partially y] make long actions threaded
# [y] need to deal with folder changes in sqlite
# [y] add doc drag drop to folders
# [y] change needs review states.
# choose pdf viewer software.
# [y] add doi lookup button
# add option to set autosave and auto backup
# add some actions to Edit menu
# [y] disable the add file button when no doc is selected, but not when adding new mannualy
# [not quite true] sqlite operations is restricted to a single thread.
# [y] add open doc folder action to right menu: 'xdg-mime query default inode/directory | sed 's/.desktop//g' -> e.g. nemo
# [y] auto open last datebase on launch
# rename file when exporting. Need to deal with switching to renaming after some files have been copied without renaming, or changing renaming pattern.
# perform duplicate check on adding
# [y] write a connected component function to replace networkx
# [y] text fold button has bug
# [N] add a copy to clipboard to messagebox showing failed tasks
# [y] connect the fail dialog's create folder button
# [y] Name a database file on creation and create collections folder under that name
# could probably make the thread call func using a decorator
# [y] possible to let user choose default add action?
# break down addActionTriggered()
# citation style stuff
# [y] change Ctrl-N shortcut to Add button. Maybe Ctrl-Shift-N for new lib.
# add more shortcuts
# qcompleter in some meta fields e.g. author, keyworgs
# [y] add search bar, result treewidget, clear frame, add folder from selection
# [Not now] add tooltip to search bar
# [y] the folder highlighting is still buggy
# add search result caching
# [y] save to sqlite before calling search
# [y] search desend into sub folders
# [y] crop file path within 255?
# [y] show number of docs and number of selected rows in status bar
# [y] import from Mendeley
# [y] show loaded lib name at title
# [y] deny renaming sys folders
# [y] make file paths relative
# [y] rel v.s. abs file path choices in bib, ris exports
# [y] del prints
# [y] add doc table sort idx to settings
# master control on the statusbar, show a diff message after done if not close_on_finish
# [y] disable save lib, close lib when not loaded
# add doc adding to Edit or File?
# [y] use open instead of xdg-open in Mac
# auto renaming bib, ris files when meta data is empty
# icons on mac missing
# [y] drag/drop on mac
# button style on mac

def main(args=None):

    if args is None:
        args=sys.argv[1:]

    logging.config.dictConfig(LOG_CONFIG)
    app=QtWidgets.QApplication(sys.argv)

    splash_pic=QPixmap(':/logo.png')
    splash=QtWidgets.QSplashScreen(splash_pic, Qt.WindowStaysOnTopHint)
    splash.show()
    splash.showMessage(__version__)

    QTimer.singleShot(1984, splash.close)

    app.processEvents()
    '''
    svgrenderer=QtSvg.QSvgRenderer('./recaman/recaman_box_n_33_fillline.svg.svg')
    qimage=QImage(522,305, QImage.Format_ARGB32)
    painter=QPainter(qimage)
    svgrenderer.render(painter)

    splash_pic=QPixmap.fromImage(qimage)
    print('# <__init__>: splash_pic', splash_pic)
    splash=QtWidgets.QSplashScreen(splash_pic, Qt.WindowStaysOnTopHint)
    splash.show()
    #splash.showMessage('Loading ...')

    QTimer.singleShot(3000, splash.close)

    app.processEvents()
    '''

    mainwindow=_MainWindow.MainWindow()
    sys.exit(app.exec_())

    return 0

if __name__=='__main__':

    main()


