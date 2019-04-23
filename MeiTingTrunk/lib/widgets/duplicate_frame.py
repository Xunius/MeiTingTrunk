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
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QBrush, QColor, QIcon, QCursor, QFont
from PyQt5.QtWidgets import QDialogButtonBox, QStyle
from .. import sqlitedb
from ..tools import fuzzyMatchPrepare, fuzzyMatch, dfsCC, getHLine, parseAuthors
from .threadrun_dialog import Master
from .search_res_frame import AdjustableTextEditWithFold


LOGGER=logging.getLogger(__name__)



class CheckDuplicateFrame(QtWidgets.QScrollArea):

    del_doc_from_folder_signal=pyqtSignal(list, # docids
            str, #foldername
            str, #folderid
            bool #reload_talbe
            )
    del_doc_from_lib_signal=pyqtSignal(list, # docids
            bool, #reload_table
            bool # ask
            )

    def __init__(self,settings,parent=None):
        '''
        Args:
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
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
        self.tree.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.docTreeMenu)

        #----------------Create merge frame----------------
        self.merge_frame=MergeFrame(self.settings, self.tree)
        self.merge_frame.setVisible(False)
        self.merge_frame.change_to_table_sig.connect(self.changeView)

        self.no_dup_label=QtWidgets.QLabel('No duplicates found.')
        self.no_dup_label.setVisible(False)
        va.addWidget(self.no_dup_label)
        va.addWidget(self.tree)
        va.addWidget(self.merge_frame)

        frame.setLayout(va)


    def createClearDuplicateFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        ha=QtWidgets.QHBoxLayout()
        self.current_view='table'  # 'table' | 'merge'

        # del button
        self.del_duplicate_button=QtWidgets.QToolButton(self)
        self.del_duplicate_button.setText('Delete Selected')
        self.del_duplicate_button.clicked.connect(self.delDocs)

        # change to merge/table view button
        self.change_view_button=QtWidgets.QToolButton(self)
        self.change_view_button.setText('Change to Merge View')
        self.change_view_button.clicked.connect(self.changeView)

        # clear button
        self.clear_duplicate_button=QtWidgets.QToolButton(self)
        self.clear_duplicate_button.setText('Exit')

        self.clear_duplicate_label=QtWidgets.QLabel()
        ha.addWidget(self.clear_duplicate_label)
        tip_label=QtWidgets.QLabel()
        tip_icon=QIcon.fromTheme('help-about',
            self.style().standardIcon(QStyle.SP_MessageBoxInformation)).pixmap(
                    QSize(16,16))
        tip_label.setPixmap(tip_icon)
        tip_label.setToolTip('''Change "Mininimum Similary Score" in "Preferences" to change the filtering of matching results.''')

        ha.addWidget(tip_label)
        ha.addWidget(self.del_duplicate_button)
        ha.addWidget(self.change_view_button)
        ha.addWidget(self.clear_duplicate_button)

        frame.setLayout(ha)

        return frame


    @pyqtSlot()
    def changeView(self):
        '''Change between the table/merge view'''

        current=self.tree.currentItem()

        #---------------Change to merge view---------------
        if self.current_view=='table' and current:
            self.change_view_button.setText('Change to Table View')
            self.current_view='merge'
            self.del_duplicate_button.setVisible(False)
            self.tree.setVisible(False)
            self.merge_frame.setVisible(True)

            # current is a child row
            if current.data(0,0)=='':
                gid=current.parent().data(0,0)
            else:
                gid=current.data(0,0)

            LOGGER.debug('current_item gid = %s' %current.data(0,0))

            self.merge_frame.createMergeForGroup(gid, self.group_dict,
                    self.meta_dict, self.folder_dict, self.current_folder)

        #---------------Change to table view---------------
        # NOTE: I said 'table' but it's really a QTreeWidget
        elif self.current_view=='merge':
            self.change_view_button.setText('Change to Merge View')
            self.current_view='table'
            self.del_duplicate_button.setVisible(True)
            self.tree.setVisible(True)
            self.merge_frame.setVisible(False)

        LOGGER.info('View changed to %s' %self.current_view)

        return


    def checkDuplicates(self, meta_dict, folder_dict, current_folder, docids1,
            docid2=None):
        """Start the duplicate checking among documents

        Args:
            meta_dict (dict): meta data of all documents. keys: docid,
                              values: DocMeta dict.
            folder_dict (dict): folder structure info. keys: folder id in str,
                values: (foldername, parentid) tuple.
            current_folder (tuple): (foldername_in_str, folder_id_in_str).
            docids1 (list): ids of docs in group 1.

        Kwargs:
            docid2 (int, list or None): if int or list, ids of docs in group 2,
                then duplicate checking is done among all pairs across group 1,
                2. If None, checking is done among all pairs in group 1.
        """

        self.tree.clear()
        self.setVisible(True)
        if self.current_view=='merge':
            self.changeView()

        self.meta_dict=meta_dict
        self.folder_dict=folder_dict
        self.current_folder=current_folder # (name, id)
        self.docids1=docids1
        self.docids1.sort()
        self.docid2=docid2

        #---------Disable merging if inside trash---------
        trashed_folder_ids=sqlitedb.getTrashedFolders(self.folder_dict)
        if current_folder[1] in trashed_folder_ids:
            self.change_view_button.setEnabled(False)
        else:
            self.change_view_button.setEnabled(True)

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
            jobid2=0
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

                        job_list.append((jobid2,
                            getFromCache(cache_dict, docii),
                            getFromCache(cache_dict, docjj),
                            self.min_score))
                        jobid2+=1


        #-----------------nxm compare-----------------
        else:
            if not isinstance(docid2, (tuple,list)):
                # docid2 is a single doc
                docid2=[docid2,]

            m=len(docid2)
            jobid2=0

            for ii in range(m):
                docii=docid2[ii]
                _, authorsii, titleii, jyii=getFromCache(cache_dict, docii)
                for jj in range(n):
                    docjj=docids1[jj]
                    if docii!=docjj:
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

                        job_list.append((jobid2,
                            getFromCache(cache_dict, docii),
                            getFromCache(cache_dict, docjj),
                            self.min_score))
                        jobid2+=1

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
                    'classic',self.parent.status_bar,'Computing Fuzzy Matching...')
            self.master2.all_done_signal.connect(self.collectResults)
            self.clear_duplicate_button.clicked.connect(self.master2.abortJobs)
            self.master2.run()

        return


    @pyqtSlot()
    def collectResults(self):
        '''Collect matching results and send results to GUI'''

        new=self.master2.results
        for recii,jobidii,resii in new:
            if recii==0:
                kii,vii=resii
                self.scores_dict[kii]=vii

        LOGGER.info('Duplicate search results collected.')
        self.addResults()

        return


    def createEntry(self, docid, gid, score):
        '''Create a QTreeWidgetItem for a doc

        Args:
            docid (int): doc id.
            gid (int): group id.
            score (int): similarity score.

        Return: item (QTreeWidgetItem): QTreeWidgetItem to add to the tree
        '''

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


    def addResults(self):
        '''Add matching results to treewidget'''

        edges=[kk for kk,vv in self.scores_dict.items() if vv>=self.min_score]
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        # if no duplicates, return
        if len(edges)==0:
            self.no_dup_label.setVisible(True)
            LOGGER.info('No duplicate found.')
            return

        self.no_dup_label.setVisible(False)

        #--------------------Get groups--------------------
        groups={}  # key: gid, value: list of doc ids in same group

        if self.docid2 is None:
            # get connected components
            comps=dfsCC(edges)
            LOGGER.debug('connected components = %s' %comps)
            for ii,cii in enumerate(comps):
                cii.sort()
                groups[ii]=cii
        else:
            if not isinstance(self.docid2, (tuple,list)):
                # docid2 is a single doc
                docid2=[self.docid2,]
            else:
                docid2=self.docid2

            for ii,docii in enumerate(docid2):
                docs=[kk[1] for kk in edges if kk[0]==docii]
                if len(docs)>0:
                    groups[ii]=[docii]+docs # don't forget docii itself

        #--------------------Add header rows--------------------
        # sort by group length
        headers=sorted(groups.keys(), key=lambda x: len(groups[x]),
                reverse=True)

        self.group_dict=OrderedDict()
        # key: groupid, value: dict: {'header': header QTreeWidgetItem,
        #                             'members': list of doc ids in group}
        # this dict is later used to reconstruct tree after a merging.

        for ii,gii in enumerate(headers):

            members=groups[gii]
            docii=members[0]
            others=members[1:]
            newgid=ii+1
            itemii=self.createEntry(docii, str(newgid), '')

            # highlight group header
            for jj in range(self.tree.columnCount()):
                itemii.setBackground(jj, hi_color)

            self.tree.addTopLevelItem(itemii)

            #------------Create table view members------------
            # sort group members by scores
            scores=[]
            for djj in others:
                if (docii, djj) in edges:
                    sii=self.scores_dict[(docii, djj)]
                else:
                    sii=self.scores_dict[(djj, docii)]
                scores.append(sii)

            others=[x for _,x in sorted(zip(scores,others), reverse=True)]
            scores=sorted(scores,reverse=True)

            #----------------Add to group_dict----------------
            members=[docii]+others
            self.group_dict[newgid]={'header': itemii, 'members' : members}

            #-------------------Add to tree-------------------
            for jj,docjj in enumerate(members[1:]):
                # connection lost along the path between 2 vertices
                sjj=str(scores[jj])
                #if sjj=='0':
                    #sjj='N/A'
                itemjj=self.createEntry(docjj, '', sjj)
                itemii.addChild(itemjj)

        self.tree.setStyleSheet('''
        QTreeWidget::item:has-children { border-left: 1px solid black;
        background-color: %s;}
        ''' %hi_color.color().name())

        self.tree.expandAll()
        LOGGER.info('Duplicate search results added.')

        return


    def docTreeMenu(self,pos):
        '''Right click menu in the document tree'''

        menu=QtWidgets.QMenu()

        foldername,folderid=self.current_folder
        if folderid=='-1':
            menu.addAction('Delete From &Library')
        else:
            menu.addAction('Delete From Current &Folder')

        menu.addAction('&Remove From Duplicate Group')

        action=menu.exec_(QCursor.pos())

        if action:
            action_text=action.text().replace('&','')
            if action_text in ['Delete From Current Folder',
                    'Delete From Library']:
                self.delDocs()
            elif action_text=='Remove From Duplicate Group':
                self.removeFromGroup()

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
                self.del_doc_from_lib_signal.emit(docids,False,True)
            else:
                LOGGER.info('Emit signal for doc deletion in folder %s' %foldername)
                self.del_doc_from_folder_signal.emit(docids, foldername,
                        folderid, False)

            for itemii in sel_rows:
                self.tree.invisibleRootItem().removeChild(itemii)

        return


    def removeFromGroup(self):

        sel_rows=self.tree.selectedItems()
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        #-------------------Remove items-------------------
        # while is better than for when dealing with item iter
        while len(sel_rows)>0:
            itemii=sel_rows.pop()
            docid=int(itemii.data(6,0))

            #------------Remove a child from group------------
            if itemii.data(0,0)=='':
                gid=int(itemii.parent().data(0,0))
                itemii.parent().removeChild(itemii)

                if gid in self.group_dict:
                    members=self.group_dict[gid]['members']
                    if docid in members:
                        members.remove(docid)
                    self.group_dict[gid]['members']=members

            #-------------Remove header from group-------------
            else:
                gid=int(itemii.data(0,0))
                members=self.group_dict[gid]['members']
                # single header, del
                if len(members)==1:
                    self.tree.invisibleRootItem().removeChild(itemii)
                    del self.group_dict[gid]
                else:
                    idx=self.tree.indexOfTopLevelItem(itemii)
                    children=itemii.takeChildren()
                    itemii=self.tree.takeTopLevelItem(idx)

                    if len(children)>=2:
                        if docid in members:
                            members.remove(docid)
                        self.group_dict[gid]['members']=members

                        # promote the next child to header
                        newheader=children[0]
                        newheader.setData(0,0,str(gid))
                        self.tree.insertTopLevelItem(idx, newheader)

                        # highlight group header
                        for jj in range(self.tree.columnCount()):
                            newheader.setBackground(jj, hi_color)

                        # add new children
                        for cjj in children[1:]:
                            newheader.addChild(cjj)

                        newheader.setExpanded(True)
                    else:
                        del self.group_dict[gid]

        #-------------Remove singleton headers-------------
        idx=0
        while idx<self.tree.topLevelItemCount():
            itemii=self.tree.topLevelItem(idx)
            if itemii.childCount()==0:
                self.tree.takeTopLevelItem(idx)
                gid=itemii.data(0,0)
                del self.group_dict[int(gid)]
            else:
                idx+=1

        LOGGER.debug('groups after deletion: %s' %self.group_dict.keys())

        return



class MergeFrame(QtWidgets.QScrollArea):

    # add new doc after merging. Connect to _MainFrameDataSlots.addDocFromDuplicateMerge()
    add_new_doc_sig=pyqtSignal(sqlitedb.DocMeta)

    # del docs after merging. Connect to _MainFrameDocTableSlots.delDoc()
    del_doc_sig=pyqtSignal(list, bool, bool)  # docids, reload_table, ask

    # change to table view after merging. Connect to CheckDuplicateFrame.changeView()
    change_to_table_sig=pyqtSignal()

    def __init__(self, settings, tree, parent=None):
        '''Interface for resolving conflicts in duplicate merging

        Args:
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
            tree (QTreeWidget): treewidget created in CheckDuplicateFrame.
        '''

        super(self.__class__, self).__init__(parent=parent)

        self.settings=settings
        self.tree=tree

        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        self.setWidgetResizable(True)
        self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)
        #va.setContentsMargins(0,0,0,0)

        self.label=QtWidgets.QLabel('Resolve Conflicts')
        self.label.setStyleSheet('font: bold 14px;')

        # toggle all fields button
        self.toggle_all_button=QtWidgets.QToolButton(self)
        self.toggle_all_button.setText('Show All Fields')
        self.toggle_all_button.clicked.connect(self.toggleAllFields)
        self.show_all=False

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.label)
        ha.addWidget(self.toggle_all_button, 1, Qt.AlignRight)
        va.addLayout(ha)
        va.addWidget(getHLine())

        # grid layout, will be filled in createMergeForGroup
        self.merge_grid=QtWidgets.QGridLayout()
        va.addLayout(self.merge_grid)
        va.addStretch()

        # confirm button
        self.confirm_button=QtWidgets.QToolButton(self)
        self.confirm_button.setText('Confirm Merge')
        self.confirm_button.clicked.connect(self.confirmMerge)
        self.confirm_button.setStyleSheet('font: bold 12px;')

        # preview button
        #self.preview_button=QtWidgets.QToolButton(self)
        #self.preview_button.setText('Preview')
        #self.preview_button.clicked.connect(self.previewMerge)
        #self.preview_button.setStyleSheet('font: bold 12px;')

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.confirm_button, 0, Qt.AlignRight)
        #ha.addWidget(self.preview_button, 0, Qt.AlignRight)
        va.addLayout(ha)

        frame.setLayout(va)

        # complete field list not including 'folders_l'
        self.fields=[
                'title', 'issue', 'pages', 'publication', 'volume', 'year',
                'doi', 'abstract', 'arxivId', 'chapter', 'city', 'country',
                'edition', 'institution', 'isbn', 'issn', 'month', 'day',
                'publisher', 'series', 'pmid', 'keywords_l', 'files_l',
                'tags_l', 'urls_l', 'notes', 'authors_l'
                ]
        self.fields.sort()
        self.long_fields=['title', 'abstract', 'institution', #?
                'keywords_l', 'files_l', 'tags_l', 'urls_l', 'notes',
                'authors_l']


    def createMergeForGroup(self, gid, group_dict, meta_dict, folder_dict,
            current_folder):
        '''Create interface for merging a group

        Args:
            gid (int): group id.
            group_dict (dict): group info. key: groupid, value: dict:
                               {'header': header QTreeWidgetItem,
                                'members': list of doc ids in group}.
            meta_dict (dict): meta data of all documents. keys: docid,
                              values: DocMeta dict.
            folder_dict( dict): folder structure info. keys: folder id in str,
                                values: (foldername, parentid) tuple.
            current_folder (tuple): (folderid_in_str, foldername_in_str).
        '''

        def valueToStr(meta_dict, key):
            '''Convert meta dict field to str'''
            value=meta_dict[key]
            if value is None:
                return None
            if key.endswith('_l'):
                value='; '.join(value)
            else:
                value=str(value)
            return value

        #--------------------Store data--------------------
        gid=int(gid)  # gid was fetched from QTreeWidgetItem, get back to int
        self.gid=gid
        self.group_dict=group_dict
        self.meta_dict=meta_dict
        self.folder_dict=folder_dict
        self.current_folder=current_folder
        self.label.setText('Resolve Conflicts in Group %d' %gid)

        #-----------Collect meta data by fields-----------
        members=group_dict[gid]['members']
        meta_list=[meta_dict[ii] for ii in members]
        self.value_dict=OrderedDict() # key: field name (e.g. title), value:
        # non-empty list of unique values among members

        for kk in self.fields:
            valuekk=[]
            for dii in meta_list:
                vii=valueToStr(dii,kk)
                if vii != '' and vii is not None:
                    valuekk.append(vii)

            valuekk=list(set(valuekk))
            if len(valuekk)>0:
                self.value_dict[kk]=valuekk

        LOGGER.debug('gid = %s. members = %s' %(gid, members))

        #-------------------Collect folders-------------------
        folders=[]
        for dii in meta_list:
            folders.extend(map(tuple, dii['folders_l']))

        folders=list(set(folders))  # [(fid1, fname1), (fid2, fname2) ...]

        if len(folders)>0:  # it must be, unless in trash
            folders2=[]
            for fii in folders:
                folders2.append((str(fii[0]),  # folderid in str
                    sqlitedb.getFolderTree(self.folder_dict, str(fii[0]))[1])
                    # folder in tree e.g. folder1/sub1/subsub2
                    )
            self.value_dict['folders_l']=folders2

        LOGGER.debug('folders in group = %s' %folders2)
        self.addFieldRows()

        return


    def clearMergeGrid(self):
        '''Clear grid layout'''

        while self.merge_grid.count():
            child = self.merge_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        return


    def addFieldRows(self):
        '''Add uniqute values in a field to the merge frame'''

        font=self.settings.value('display/fonts/doc_table',QFont)
        self.clearMergeGrid()
        grid=self.merge_grid
        crow=grid.rowCount()

        self.collect_dict={} # key: field name, value: buttongroup if field
        # has more than 1 value. str if only 1 value.
        self.button_le_dict={} # key: radiobutton/checkbox:
                               # value: textedit/lineedit/str

        #--------------------Add fields--------------------
        for fii, valuesii in self.value_dict.items():

            # put folders at the end
            if fii=='folders_l':
                continue

            LOGGER.debug('adding field %s. NO values = %d' %(fii, len(valuesii)))

            # if no conflict and not showing all fields
            if not self.show_all and len(valuesii)==1:
                # still add to collect_dict as it will be used for creating
                # new doc
                self.collect_dict[fii]=valuesii[0]
                continue

            rgroup=QtWidgets.QButtonGroup(self) # NOTE: has to add self
            rgroup.setExclusive(True)
            self.collect_dict[fii]=rgroup

            # add unique values
            for jj,vjj in enumerate(valuesii):

                radiojj=QtWidgets.QRadioButton()

                if jj==0:
                    labelii=QtWidgets.QLabel('%s: ' %fii.replace('_l','').capitalize())
                    # highlight fields with conflicts
                    if len(valuesii)>1:
                        labelii.setStyleSheet('font: bold; color: red;')
                    grid.addWidget(labelii,crow,0)
                    radiojj.setChecked(True)

                if fii in self.long_fields:
                    text_editjj=AdjustableTextEditWithFold(self)
                    text_editjj.unfoldText()
                    grid.addWidget(text_editjj.fold_button,crow,2)

                    # set tooltip texts
                    if fii=='authors_l':
                        text_editjj.label_enabled=True
                        text_editjj.tooltip_text='lastname, firstname; lastname, firstname;...'
                    elif fii=='tags_l':
                        text_editjj.label_enabled=True
                        text_editjj.tooltip_text='tag1; tag2; tag3 ...'
                    elif fii=='keywords_l':
                        text_editjj.label_enabled=True
                        text_editjj.tooltip_text='keyword1; keyword2; keyword3 ...'
                else:
                    text_editjj=QtWidgets.QLineEdit()
                text_editjj.setFont(font)
                text_editjj.setText(vjj)

                grid.addWidget(radiojj,crow,1)
                grid.addWidget(text_editjj,crow,3)
                rgroup.addButton(radiojj)
                self.button_le_dict[radiojj]=text_editjj

                crow+=1

        #------------Add folders as checkboxes------------
        folders=self.value_dict.get('folders_l')

        if folders:

            fii='folders_l'
            valuesii=folders

            rgroup=QtWidgets.QButtonGroup(self) # NOTE: has to add self
            rgroup.setExclusive(False)
            self.collect_dict[fii]=rgroup

            for jj,vjj in enumerate(valuesii):

                # vjj: (folderid_in_str, folder_tree_path_in_str)

                radiojj=QtWidgets.QCheckBox(self)
                radiojj.setChecked(True)
                # if only 1 folder, checking is within a folder, disable state
                # change
                if len(valuesii)==1:
                    radiojj.setEnabled(False)

                if jj==0:
                    labelii=QtWidgets.QLabel('Add to folder(s)')
                    if len(valuesii)>1:
                        labelii.setStyleSheet('font: bold; color: red;')
                    grid.addWidget(labelii,crow,0)

                text_editjj=QtWidgets.QLineEdit(self)
                text_editjj.setFont(font)
                text_editjj.setText(vjj[1])
                text_editjj.setReadOnly(True)

                grid.addWidget(radiojj,crow,1)
                grid.addWidget(text_editjj,crow,3)

                rgroup.addButton(radiojj)
                # NOTE: here value is folder id
                self.button_le_dict[radiojj]=vjj[0]

                crow+=1
                LOGGER.debug('added folder (%s, %s)' %(vjj[0], vjj[1]))

        return


    @pyqtSlot()
    def toggleAllFields(self):
        '''Switch between show all fields and show conflict only'''

        if self.show_all:
            self.toggle_all_button.setText('Show All Fields')
            self.show_all=False
        else:
            self.toggle_all_button.setText('Show Only Conflicts')
            self.show_all=True

        self.addFieldRows()

        return


    @pyqtSlot()
    def confirmMerge(self):
        '''Confirm a duplicate merge

        This will merge a group of duplicates into a unified document. A new
        doc is created from the fields picked by user, and previous docs in
        the group will be send to Trash.
        '''

        def parseToList(text):
            '''Text to list'''
            result=[]
            textlist=text.replace('\n',';').strip(';').split(';')
            for tii in textlist:
                tii=tii.strip()
                if len(tii)>0:
                    result.append(tii)
            return result

        members=self.group_dict[self.gid]['members']
        LOGGER.info('Merging group %s. Members = %s' %(self.gid, members))

        result_dict=sqlitedb.DocMeta()

        #---Get text from the checked textedit/lineedit---
        for fii, rgroupii in self.collect_dict.items():

            # special treatment
            if fii=='folders_l':
                continue

            # rgroupii is buttongroup: more than 1 value
            if isinstance(rgroupii, QtWidgets.QButtonGroup):
                checked=rgroupii.checkedButton()
                # get the corresponding textedit/lineedit
                textwidget=self.button_le_dict[checked]

                if isinstance(textwidget, QtWidgets.QTextEdit):
                    textii=self.button_le_dict[checked].toPlainText()
                elif isinstance(textwidget, QtWidgets.QLineEdit):
                    textii=self.button_le_dict[checked].text()

                LOGGER.debug('Conflict field = %s. Chosen value = %s'\
                        %(fii, textii))
            # no conflict, single value
            else:
                textii=rgroupii
                LOGGER.debug('Agreed field = %s. Chosen value = %s'\
                        %(fii, textii))

            if fii.endswith('_l'):
                values=parseToList(textii.strip())
                if fii=='authors_l':
                    firsts,lasts,_=parseAuthors(values)
                    result_dict['firstNames_l']=firsts
                    result_dict['lastName_l']=lasts
                else:
                    result_dict[fii]=values
            else:
                result_dict[fii]=textii.strip()

        #-------------------Get folders-------------------
        rgroup=self.collect_dict.get('folders_l')
        folders=[]
        if rgroup:
            for checkii in rgroup.buttons():
                if checkii.isChecked():
                    fid=self.button_le_dict[checkii]
                    # (folderid, foldername)
                    folders.append((fid, self.folder_dict[fid][0]))

        result_dict['folders_l']=folders
        LOGGER.debug('folders_l = %s' %folders)

        #-------------------Add new doc-------------------
        self.add_new_doc_sig.emit(result_dict)

        #---------------Del previous members---------------
        self.del_doc_sig.emit(members, False, False)

        # delete this group from tree
        del_header=self.group_dict[self.gid]['header']
        for ii in range(del_header.childCount()):
            cii=del_header.child(ii)
            del_header.removeChild(cii)
        self.tree.invisibleRootItem().removeChild(del_header)
        del self.group_dict[self.gid]

        #--------------Go back to table view--------------
        self.change_to_table_sig.emit()

        return


    @pyqtSlot()
    def previewMerge(self):
        pass


