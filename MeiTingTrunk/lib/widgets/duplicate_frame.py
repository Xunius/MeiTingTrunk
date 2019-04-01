'''
Widget for computing and displaying duplicate checking.

MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QBrush, QColor, QIcon, QCursor
from PyQt5.QtWidgets import QDialogButtonBox
from ..tools import fuzzyMatch, dfsCC
from .threadrun_dialog import Master


LOGGER=logging.getLogger(__name__)



class CheckDuplicateFrame(QtWidgets.QScrollArea):

    del_doc_from_folder_signal=pyqtSignal(list, # docids
            str, #foldername
            str, #folderid
            bool #reload_talbe
            )
    del_doc_from_lib_signal=pyqtSignal(list, # docids
            bool #reload_table
            )

    def __init__(self,settings,parent=None):
        '''
        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''
        super(CheckDuplicateFrame,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent
        self.min_score=self.settings.value('duplicate_min_score',type=int)

        frame=QtWidgets.QWidget()
        self.setWidgetResizable(True)
        self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)

        #----------------Create clear frame----------------
        va.addWidget(self.createClearDuplicateFrame())

        #----------------Create treewidget----------------
        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(7)
        self.tree.setColumnHidden(6,True)

        self.tree.setHeaderLabels(['Group', 'Authors', 'Title',
            'Publication', 'Year', 'Similarity','id'])
        self.tree.setColumnWidth(0, 55)
        self.tree.setColumnWidth(1, 250)
        self.tree.setColumnWidth(2, 300)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 50)
        self.tree.setColumnWidth(5, 20)
        self.tree.setColumnWidth(6, 0)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.docTreeMenu)

        self.noDupLabel=QtWidgets.QLabel('No duplicates found.')
        va.addWidget(self.noDupLabel)
        va.addWidget(self.tree)

        frame.setLayout(va)


    def createClearDuplicateFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        ha=QtWidgets.QHBoxLayout()

        # del button
        self.del_duplicate_button=QtWidgets.QToolButton(self)
        self.del_duplicate_button.setText('Delete Selected')
        self.del_duplicate_button.clicked.connect(self.delDocs)

        # clear button
        self.clear_duplicate_button=QtWidgets.QToolButton(self)
        self.clear_duplicate_button.setText('Exit')

        self.clear_duplicate_label=QtWidgets.QLabel('Clear current filtering')
        ha.addWidget(self.clear_duplicate_label)
        tip_label=QtWidgets.QLabel()
        tip_icon=QIcon.fromTheme('help-about').pixmap(QSize(16,16))
        tip_label.setPixmap(tip_icon)
        tip_label.setToolTip('''Change "Mininimum Similary Score" in "Preferences" to change the filtering of matching results.''')
        ha.addWidget(tip_label)
        ha.addWidget(self.del_duplicate_button)
        ha.addWidget(self.clear_duplicate_button)

        frame.setLayout(ha)

        return frame


    def checkDuplicates(self, meta_dict, current_folder, docids1, docid2=None):
        """Start the duplicate checking among documents

        Args:
            meta_dict (dict): meta data of all documents. keys: docid,
                              values: DocMeta dict.
            current_folder (tuple): (foldername_in_str, folder_id_in_str).
            docids1 (list): ids of docs in group 1.

        Kwargs:
            docid2 (int, list or None): if int or list, ids of docs in group 2,
                then duplicate checking is done among all pairs across group 1,
                2. If None, checking is done among all pairs in group 1.
        """

        self.tree.clear()
        self.setVisible(True)

        self.meta_dict=meta_dict
        self.current_folder=current_folder # (name, id)
        self.docids1=docids1
        self.docids1.sort()
        self.docid2=docid2

        self.scores_dict={}

        self.master1=Master(self.prepareJoblist, [(0,self.docids1,self.docid2)],
                1, self.parent.progressbar,
                'busy', self.parent.status_bar, 'Preparing job list...')
        self.master1.all_done_signal.connect(self.jobListReady)
        self.master1.run()

        return


    def prepareJoblist(self, jobid, docids1, docid2):
        '''Prepare fuzzy matching jobs

        Args:
            jobid (int): dummy job id.
            docids1 (list): ids of docs in group 1.
            docid2 (int, list or None): ids of docs in group 2,

        Returns:
            rec (int): 0 for success.
            jobid (int): dummy job id.
            job_list (list): list of tuples, each providing the args for a
                             fuzzyMatch() call.
        '''

        n=len(docids1)
        job_list=[]

        #----------------Check among docds----------------
        if docid2 is None:
            for ii in range(n):
                docii=docids1[ii]
                for jj in range(n):
                    docjj=docids1[jj]
                    if ii>=jj:
                        self.scores_dict[(docii, docjj)]=0
                    else:
                        job_list.append((ii, docii, docjj,
                            self.meta_dict[docii], self.meta_dict[docjj]))
        #-----------------nxm compare-----------------
        else:
            if not isinstance(docid2, (tuple,list)):
                # docid2 is a single doc
                docid2=[docid2,]

            m=len(docid2)

            for ii in range(m):
                docii=docid2[ii]
                for jj in range(n):
                    docjj=docids1[jj]
                    if docii!=docjj:
                        job_list.append((ii, docii, docjj, self.meta_dict[docii],
                            self.meta_dict[docjj]))

        return 0,jobid,job_list


    @pyqtSlot()
    def jobListReady(self):
        '''After getting all jobs, launch threads and process jobs
        '''

        rec,jobid,job_list=self.master1.results[0]
        LOGGER.debug('rec from job list prepare = %s' %rec)

        if rec==0 and len(job_list)>0:
            self.parent.progressbar.setMaximum(0)
            self.parent.progressbar.setVisible(True)
            # make a separate master for fuzzy matching. This separation of
            # joblist-preparing and fuzzy matching is for easy aborting.
            # For large data size, it might take a few seconds to get the job
            # list prepared, therefore 2 threaded calls.
            self.master2=Master(fuzzyMatch,job_list,1,self.parent.progressbar,
                    'busy',self.parent.status_bar,'Computing Fuzzy Matching...')
            self.master2.all_done_signal.connect(self.collectResults)
            self.clear_duplicate_button.clicked.connect(self.master2.abortJobs)
            self.master2.run()

        return


    def collectResults(self):
        '''Collect matching results'''

        new=self.master2.results
        for recii,jobidii,(kii,vii) in new:
            self.scores_dict[kii]=vii

        LOGGER.info('Duplicate search results collected.')
        self.addResultToTree()

        return


    def addResultToTree(self):
        '''Display results'''

        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        def createEntry(docid,gid,score):

            meta=self.meta_dict[docid]
            item=QtWidgets.QTreeWidgetItem([
                gid,
                ', '.join(meta['authors_l']),
                meta['title'],
                meta['publication'],
                str(meta['year']),
                score,
                str(docid)
                ])

            return item

        edges=[kk for kk,vv in self.scores_dict.items() if vv>=self.min_score]
        # if no duplicates, return
        if len(edges)==0:
            self.noDupLabel.setVisible(True)
            LOGGER.info('No duplicate found.')
            return

        self.noDupLabel.setVisible(False)

        #--------------------Get groups--------------------
        groups={}

        if self.docid2 is None:

            # get connected components
            comps=dfsCC(edges)
            LOGGER.debug('connected components = %s' %comps)

            for ii,cii in enumerate(comps):
                cii.sort()
                groups[cii[0]]=cii[1:]
        else:
            if not isinstance(self.docid2, (tuple,list)):
                # docid2 is a single doc
                docid2=[self.docid2,]
            else:
                docid2=self.docid2

            for ii,docii in enumerate(docid2):
                docs=[kk[1] for kk in edges if kk[0]==docii]
                if len(docs)>0:
                    groups[docii]=docs

        #--------------------Add items--------------------
        # sort by group length
        headers=sorted(groups.keys(), key=lambda x: len(groups[x]), reverse=True)

        for ii, docii in enumerate(headers):

            itemii=createEntry(docii, str(ii+1), '')

            # highlight group header
            for jj in range(self.tree.columnCount()):
                itemii.setBackground(jj, hi_color)

            self.tree.addTopLevelItem(itemii)

            # sort group members by scores
            members=groups[docii]
            scores=[]
            for djj in members:
                if (docii, djj) in edges:
                    sii=self.scores_dict[(docii, djj)]
                else:
                    sii=self.scores_dict[(djj, docii)]
                scores.append(sii)
            members=[x for _,x in sorted(zip(scores,members), reverse=True)]
            scores=sorted(scores,reverse=True)

            # add group members
            for jj,docjj in enumerate(members):
                itemjj=createEntry(docjj, '', str(scores[jj]))
                itemii.addChild(itemjj)

            self.tree.expandAll()

        color=hi_color.color().getRgb()
        color_str='rgb(%s)' %','.join(map(str,color))

        self.tree.setStyleSheet('''
        QTreeWidget::item:has-children { border-left: 1px solid black;
        background-color: %s;}
        ''' %color_str)

        LOGGER.info('Duplicate search results added.')

        return


    def docTreeMenu(self,pos):
        '''Right click menu in the document tree'''

        menu=QtWidgets.QMenu()

        foldername,folderid=self.current_folder
        if folderid=='-1':
            menu.addAction('Delete From Library')
        else:
            menu.addAction('Delete From Current Folder')

        action=menu.exec_(QCursor.pos())

        if action:
            self.delDocs()

        return


    @pyqtSlot()
    def delDocs(self):

        LOGGER.debug('current_folder = %s' %str(self.current_folder))
        foldername,folderid=self.current_folder
        sel_rows=self.tree.selectedItems()

        if len(sel_rows)>0:

            docids=[int(ii.data(6,0)) for ii in sel_rows]
            LOGGER.debug('Selected docids = %s.' %docids)

            if folderid=='-1':
                LOGGER.info('Emit signal for doc deletion in All')
                self.del_doc_from_lib_signal.emit(docids,False)
            else:
                LOGGER.info('Emit signal for doc deletion in folder %s' %foldername)
                self.del_doc_from_folder_signal.emit(docids, foldername,
                        folderid, False)

            for itemii in sel_rows:
                self.tree.invisibleRootItem().removeChild(itemii)

        return
