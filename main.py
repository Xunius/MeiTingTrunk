#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
import _MainWindow

__version__='v0.1'

LOG_CONFIG={
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '<%(filename)s-%(funcName)s()>: %(asctime)s,%(levelname)s: %(message)s'},
            },
        'handlers': {
            'default': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'formatter': 'standard',
                'filename': 'MTT.log',
                },
            },
        'loggers': {
            'default_logger': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': True
                }
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
# add add doc functionalities, by doi
# [y] add add doc functionalities, by bib
# add add doc functionalities, by RIS
# import from Mendeley, zotero, Endnote?
# autosave, auto backup
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
# RIS
# import/export menu
# [y] add trash can
# sqlite text search: https://stackoverflow.com/questions/35020797/how-to-use-full-text-search-in-sqlite3-database-in-django 
# PDF preview
# add doc strings!!
# make long actions threaded
# [y] need to deal with folder changes in sqlite
# [y] add doc drag drop to folders
# [y] change needs review states.
# choose pdf viewer software.
# add doi lookup button
# add option to set autosave and auto backup
# add some actions to Edit menu
# [y] disable the add file button when no doc is selected, but not when adding new mannualy
# sqlite operations is restricted to a single thread.
# [y] add open doc folder action to right menu: 'xdg-mime query default inode/directory | sed 's/.desktop//g' -> e.g. nemo
# [y] auto open last datebase on launch
# rename file when exporting. Need to deal with switching to renaming after some files have been copied without renaming, or changing renaming pattern.
# perform duplicate check on adding
# [y] write a connected component function to replace networkx
# [y] text fold button has bug
# export dialog
# [N] add a copy to clipboard to messagebox showing failed tasks
# [y] connect the fail dialog's create folder button
# Name a database file on creation and create collections folder under that name


if __name__=='__main__':


    logging.config.dictConfig(LOG_CONFIG)
    app=QtWidgets.QApplication(sys.argv)

    splash_pic=QPixmap(':/logo.jpg')
    print('# <__init__>: splash_pic', splash_pic)
    splash=QtWidgets.QSplashScreen(splash_pic, Qt.WindowStaysOnTopHint)
    splash.show()
    #splash.showMessage('YOLO')

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
