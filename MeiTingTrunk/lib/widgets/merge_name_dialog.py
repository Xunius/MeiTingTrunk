'''
Merge names dialog.

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
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialogButtonBox, QStyle
from ..tools import getHLine, isXapianReady
from .threadrun_dialog import ThreadRunDialog
from .. import sqlitedb

LOGGER=logging.getLogger(__name__)



class MergeNameDialog(QtWidgets.QDialog):

    def __init__(self, meta_dict, settings, parent):
        '''
        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''

        super().__init__(parent=parent)

        self.meta_dict=meta_dict
        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(900,600)
        self.setWindowTitle('Merge Names')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Choose Field')
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

        self.cate_list.addItems(['Merge Author Names',
            'Merge Journal Names',
            'Merge Keywords',
            'Merge Tags'
            ])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Close,
            Qt.Horizontal, self)
        self.import_button=self.buttons.addButton('Apply',
                QDialogButtonBox.ApplyRole)

        self.import_button.clicked.connect(self.doMerge)
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

        if item_text=='Merge Author Names':
            self.content_frame=self.loadAuthorName()
        elif item_text=='Merge Journal Names':
            self.content_frame=self.loadJournalName()
        elif item_text=='Merge Keywords':
            #self.content_frame=self.loadJournalName()
            pass
        elif item_text=='Merge Tags':
            pass

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


    def loadAuthorName(self):
        '''Load author name merge'''

        scroll,va=self.createFrame('Merge Author Names')
        self.current_task='authors'

        docids=list(self.meta_dict.keys())
        print('# <loadAuthorName>: len(docids)=',len(docids))

        folderdata=sqlitedb.fetchMetaData(self.meta_dict, 'authors_l', docids,
                unique=False,sort=False)
        print('# <loadAuthorName>: ', folderdata)


        return scroll


    def loadJournalName(self):
        '''Load journal name merge'''

        scroll,va=self.createFrame('Merge Journal Names')
        self.current_task='journal'

        return scroll


    def findSimilar(self, text_list):

        n=len(docids1)
        job_list=[]
        cache_dict={}  # store strings for docs to avoid re-compute

        def getFromCache(cdict, key):
            if key in cdict:
                value=cdict[key]
            else:
                value=fuzzyMatchPrepare(key, self.meta_dict[key])
                cdict[key]=value
            return value

        #----------------Check among docds----------------
        if docid2 is None:
            jobid=0
            for ii in range(n):
                docii=docids1[ii]
                _, authorsii, titleii, jyii=getFromCache(cache_dict, docii)
                for jj in range(n):
                    docjj=docids1[jj]
                    if ii>=jj:
                        self.scores_dict[(docii, docjj)]=0
                    else:
                        _, authorsjj, titlejj, jyjj=getFromCache(cache_dict,
                                docjj)

                        # shortcut: skip if author string len diff >= 50%
                        if abs(len(authorsii)-len(authorsjj))>=\
                                max(len(authorsii), len(authorsjj))//2:
                            self.scores_dict[(docii, docjj)]=0
                            continue

                        # shortcut: skip if title string len diff >= 50%
                        if abs(len(titleii)-len(titlejj))>=\
                                max(len(titleii), len(titlejj))//2:
                            self.scores_dict[(docii, docjj)]=0
                            continue

                        job_list.append((jobid,
                            getFromCache(cache_dict, docii),
                            getFromCache(cache_dict, docjj),
                            self.min_score))
                        jobid+=1





    def doMerge(self):

        LOGGER.info('task = %s' %self.current_task)

        if self.current_task=='authors':
            #self.doMendeleyImport1()
            pass
        elif self.current_task=='journal':
            pass

        return
