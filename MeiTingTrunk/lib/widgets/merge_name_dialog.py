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
from collections import OrderedDict
from fuzzywuzzy import fuzz
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QBrush, QFontMetrics
from PyQt5.QtWidgets import QDialogButtonBox, QStyle
from ..tools import getHLine, isXapianReady, dfsCC, Cache, parseAuthors,\
        getSqlitePath, createDelButton
from .threadrun_dialog import ThreadRunDialog, Master
from .doc_table import MyHeaderView, TableModel
from .. import sqlitedb
from ..._MainFrameLoadData import prepareDocs

LOGGER=logging.getLogger(__name__)




class MergeNameDialog(QtWidgets.QDialog):

    def __init__(self, db, meta_dict, scores_dict, settings, parent):
        '''
        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''

        super().__init__(parent=parent)

        self.db=db
        self.meta_dict=meta_dict
        self.settings=settings
        self.parent=parent

        self.scores_dict=scores_dict
        self.cate_dict={}
        self.reload_gui=False

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


    def exec_(self):

        super().exec_()
        return self.reload_gui


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
            #self.content_frame=self.loadAuthorName()
            self.content_frame=self.loadTab('Authors')
        elif item_text=='Merge Journal Names':
            #self.content_frame=self.loadJournalName()
            self.content_frame=self.loadTab('Journals')
        elif item_text=='Merge Keywords':
            #self.content_frame=self.loadJournalName()
            self.content_frame=self.loadTab('Keywords')
        elif item_text=='Merge Tags':
            self.content_frame=self.loadTab('Tags')

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
        va.addWidget(getHLine(self))

        #------------Duplicate check min score------------
        label3=QtWidgets.QLabel('Minimum Similarity Score to Define Duplicate (10-100)')
        self.spinbox=QtWidgets.QSpinBox()
        self.spinbox.setMinimum(10)
        self.spinbox.setMaximum(100)
        self.spinbox.setValue(80)
        #self.spinbox.valueChanged.connect(self.changeDuplicateMinScore)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(label3)
        ha.addWidget(self.spinbox)
        va.addLayout(ha)

        va.addWidget(getHLine(self))

        #---------------Start search button---------------
        self.number_label=QtWidgets.QLabel('NO. of unique names in library =')
        #label.setTextFormat(Qt.RichText)
        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.number_label)

        self.search_button=QtWidgets.QToolButton(self)
        self.search_button.setText('Search For Similary Terms')
        self.search_button.clicked.connect(self.searchButtonClicked)
        ha.addWidget(self.search_button)
        va.addLayout(ha)

        self.merge_frame=MergeFrame(self.settings, self)
        self.no_dup_label=QtWidgets.QLabel('No Similar Names Found')
        self.no_dup_label.setVisible(False)
        va.addWidget(self.no_dup_label)
        va.addWidget(self.merge_frame)

        return scroll, va


    def loadTab(self, category_name):
        '''Load a category for merging'''

        scroll,va=self.createFrame('Merge %s Names' %category_name)
        self.current_task=category_name

        docids=list(self.meta_dict.keys())
        print('# <loadAuthorName>: len(docids)=',len(docids))

        if category_name=='Authors':
            key='authors_l'
        elif category_name=='Journals':
            key='publication'
        elif category_name=='Keywords':
            key='keywords_l'
        elif category_name=='Tags':
            key='tags_l'

        terms=sqlitedb.fetchMetaData(self.meta_dict, key, docids,
                unique=True,sort=True)

        n_unique=len(terms)
        print('# <loadTab>: n_unique=',n_unique)
        self.number_label.setText('NO. of unique terms in library = %s'\
                %str(n_unique))

        #va.addStretch()
        self.text_list=terms

        if self.current_task in self.cate_dict:
            self.addResults(self.cate_dict[self.current_task])

        return scroll


    @pyqtSlot()
    def delFromCache(self, key):
        if key in self.cate_dict:
            print('# <delFromCache>: ############## del key',key)
            del self.cate_dict[key]

        return


    @pyqtSlot()
    def searchButtonClicked(self):

        # if in cache, call addResults()
        if self.current_task in self.cate_dict:
            print('# <searchButtonClicked>: using exising for ', self.current_task)
            self.addResults(self.cate_dict[self.current_task])
        else:
            print('# <searchButtonClicked>: call findsimilar')
            self.thread_run_dialog1=ThreadRunDialog(
                    self.prepareJoblist,
                    [(0, self.text_list)],
                    show_message='Preparing job list...',
                    max_threads=1,
                    get_results=True,
                    close_on_finish=True,
                    progressbar_style='busy',
                    post_process_func=None,
                    parent=self)

            self.thread_run_dialog1.master.all_done_signal.connect(
                    self.jobListReady)
            self.thread_run_dialog1.abort_job_signal.connect(lambda:\
                    (self.delFromCache(self.current_task),
                        self.thread_run_dialog1.master.all_done_signal.disconnect()))
            self.thread_run_dialog1.exec_()

        return


    def prepareJoblist(self, jobid, text_list):


        n=len(text_list)
        print('# <prepareJoblist>: n=',n )
        job_list=[]
        sdict=self.cate_dict.setdefault(self.current_task, {})

        #-----------------Prepare joblist-----------------
        jobid2=0
        for ii in range(n):
            tii=text_list[ii]
            for jj in range(n):
                tjj=text_list[jj]
                if ii>=jj:
                    sdict.setdefault((tii, tjj), 0)
                else:
                    # shortcut: skip if 1st letter don't match
                    if tii[0].lower() != tjj[0].lower():
                        sdict[(tii, tjj)]=0
                        continue
                    # shortcut: skip if string len diff >= 50%
                    if abs(len(tii)-len(tjj))>=\
                            max(len(tii), len(tjj))//2:
                        sdict[(tii, tjj)]=0
                        continue

                    # shortcut: if in cache:
                    if (tii, tjj) in self.scores_dict:
                        sdict[(tii, tjj)]=self.scores_dict[(tii, tjj)]
                        continue

                    if (tii, tjj) not in sdict:
                        job_list.append((jobid2, tii, tjj))
                        jobid2+=1

        print('# <prepareJoblist>: len(job_list)=', len(job_list))
        return 0,jobid,job_list


    @pyqtSlot()
    def jobListReady(self):
        '''After getting all jobs, launch threads and process jobs
        '''

        QtWidgets.QApplication.processEvents() # needed?
        rec,jobid,job_list=self.thread_run_dialog1.results[0]
        print('# <jobListReady>: rec=',rec, len(job_list))
        LOGGER.debug('rec from job list prepare = %s' %rec)

        def fuzzWrapper(jobid, t1, t2):
            try:
                s=fuzz.ratio(t1, t2)
                return 0, jobid, ((t1, t2), s)
            except:
                return 1, jobid, None

        if rec==0 and len(job_list)>0:

            self.thread_run_dialog2=ThreadRunDialog(
                    fuzzWrapper,
                    job_list,
                    show_message='Computing Fuzzy Matching...',
                    max_threads=1,
                    get_results=True,
                    close_on_finish=True,
                    progressbar_style='classic',
                    post_process_func=None,
                    parent=self)

            self.thread_run_dialog2.master.all_done_signal.connect(
                    self.collectResults)
            self.thread_run_dialog2.abort_job_signal.connect(lambda:\
                    self.delFromCache(self.current_task))
            self.thread_run_dialog2.exec_()
        else:
            #self.collectResults()
            sdict=self.cate_dict[self.current_task]
            self.scores_dict.update(sdict)
            self.addResults(sdict)

        return


    @pyqtSlot()
    def collectResults(self):
        '''Collect matching results and send results to GUI'''

        new=self.thread_run_dialog2.results
        sdict=self.cate_dict[self.current_task]
        for recii,jobidii,resii in new:
            if recii==0:
                kii,vii=resii
                sdict[kii]=vii

        self.cate_dict[self.current_task]=sdict
        self.scores_dict.update(sdict)
        LOGGER.info('Duplicate search results collected.')
        self.addResults(sdict)

        return


    @pyqtSlot()
    def addResults(self, sdict):
        '''Add matching results to treewidget'''

        edges=[kk for kk,vv in sdict.items() if vv>=self.spinbox.value()]
        # if no duplicates, return
        if len(edges)==0:
            self.no_dup_label.setVisible(True)
            LOGGER.info('No duplicate found.')
            return

        self.no_dup_label.setVisible(False)

        #--------------------Get groups--------------------
        groups={}  # key: gid, value: list of doc ids in same group

        # get connected components
        comps=dfsCC(edges)
        for ii,cii in enumerate(comps):
            cii.sort()
            groups[ii]=cii

        #--------------------Add header rows--------------------
        # sort by alphabetic
        headers=sorted(groups.keys(), key=lambda x: groups[x],
                reverse=False)

        self.group_dict=OrderedDict()
        # key: groupid, value: dict: {'header': one term,
        #                             'members': list of all terms in group}

        self.merge_frame.clearMergeGrid()
        print('# <addResults>: headers=',headers)
        for ii,gii in enumerate(headers):

            members=groups[gii]
            textii=members[0]
            #others=members[1:]
            newgid=ii+1
            #print('# <addResults>: ii=',ii,'gii=',gii,'members=',members)

            #----------------Add to group_dict----------------
            self.group_dict[newgid]={'header': textii, 'members' : members}

            # add to merge_frame
            self.merge_frame.createMergeForGroup(newgid, self.group_dict)

        return


    @pyqtSlot()
    def doMerge(self):

        choice=QtWidgets.QMessageBox.question(self, 'Confirm Merge',
                'Changes can not be reverted. Confirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice==QtWidgets.QMessageBox.No:
            return

        LOGGER.info('task = %s' %self.current_task)

        collect_dict=self.merge_frame.collect_dict
        group_dict=self.merge_frame.group_dict
        button_le_dict=self.merge_frame.button_le_dict
        sel_groups=self.merge_frame.getCheckedGroups()

        job_list=[]

        #for gidii,gdictii in group_dict.items():
        for gidii in group_dict:
            print('# <doMerge>: gid=',gidii)
            #print('# <doMerge>: gdict=',gdictii)

            if gidii not in sel_groups:
                print('# <doMerge>: ################## skip', gidii)
                continue

            rgroupii=collect_dict[gidii]
            checked=rgroupii.checkedButton()
            # get the corresponding textedit/lineedit
            textwidget=button_le_dict[checked]
            newterm=textwidget.text()
            print('# <doMerge>: sel text', newterm)
            #members=gdictii['members']
            members=[button_le_dict[tii].text() for tii in rgroupii.buttons()]
            print('# <doMerge>: members=', members)

            job_list.append((members, newterm))

        if len(job_list)==0:
            return

        #-----------------Call save first-----------------
        # probably can't use signal as i have to wait for it to complete.
        self.parent.saveDatabaseTriggered()

        for old_listii, newtermii in job_list:
            sqlitedb.replaceTerm(self.db, self.current_task, old_listii,
                    newtermii)

        #----------------Remove from cache----------------
        del self.cate_dict[self.current_task]

        #--------------------Clear gui--------------------
        self.merge_frame.clearMergeGrid()

        #-------------------Reload data-------------------
        self.parent.loadSqlite(getSqlitePath(self.db), load_to_gui=False)

        #--------------------Reload data--------------------
        old=self.meta_dict
        self.meta_dict=self.parent.main_frame.meta_dict
        print('# <doMerge>: old is new', old is self.meta_dict, old == self.meta_dict)
        #self.loadTab(self.current_task)
        self.cateSelected(self.cate_list.currentItem())
        self.reload_gui=True


        return



class MergeFrame(QtWidgets.QScrollArea):

    # add new doc after merging. Connect to _MainFrameDataSlots.addDocFromDuplicateMerge()
    #add_new_doc_sig=pyqtSignal(sqlitedb.DocMeta)

    # del docs after merging. Connect to _MainFrameDocTableSlots.delDoc()
    #del_doc_sig=pyqtSignal(list, bool, bool)  # docids, reload_table, ask

    # change to table view after merging. Connect to CheckDuplicateFrame.changeView()
    #change_to_table_sig=pyqtSignal()

    def __init__(self, settings, parent=None):
        '''Interface for resolving conflicts in duplicate merging

        Args:
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
            tree (QTreeWidget): treewidget created in CheckDuplicateFrame.
        '''

        super(self.__class__, self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        self.setWidgetResizable(True)
        self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)
        #va.setContentsMargins(0,0,0,0)

        label=QtWidgets.QLabel('Merge Similar Terms')
        label.setStyleSheet('font: bold 14px;')
        self.sel_all_button=QtWidgets.QCheckBox('Select All', self)
        self.sel_all_button.setChecked(True)
        self.groupbox=QtWidgets.QButtonGroup(self)
        self.groupbox.setExclusive(False)
        #self.groupbox.setCheckable(True)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.sel_all_button)
        ha.addWidget(label, 1, Qt.AlignRight)
        self.sel_all_button.toggled.connect(lambda on: self.checkboxGroupChanged(on,
            self.groupbox))
        va.addLayout(ha)
        va.addWidget(getHLine())

        # vbox layout, will be filled in createMergeForGroup
        self.merge_grid=QtWidgets.QVBoxLayout()
        va.addLayout(self.merge_grid)
        va.addStretch()

        frame.setLayout(va)

        self.group_dict={}
        self.collect_dict={} # key: gid, value: buttongroup
        self.button_le_dict={} # key: radiobutton/checkbox:
                               # value: textedit/lineedit





    def createMergeForGroup(self, gid, group_dict):
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
        self.group_dict=group_dict

        #-----------Collect meta data by fields-----------
        members=group_dict[gid]['members']
        self.addFieldRows(gid, members)

        return


    def clearMergeGrid(self):
        '''Clear grid layout'''


        def clearLayout(layout):
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    try:
                        clearLayout(child.widget().layout())
                    except:
                        pass
                    child.widget().deleteLater()
            return

        '''
        while self.merge_grid.count():
            child = self.merge_grid.takeAt(0)
            if child.widget():
                self.clearMergeGrid(child.widget())
                child.widget().deleteLater()
        '''
        clearLayout(self.merge_grid)

        self.collect_dict={}
        self.button_le_dict={}

        return


    def addFieldRows(self, gid, members):
        '''Add uniqute values in a field to the merge frame'''

        font=self.settings.value('display/fonts/doc_table',QFont)
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        rgroup=QtWidgets.QButtonGroup(self) # NOTE: has to add self
        rgroup.setExclusive(True)
        self.collect_dict[gid]=rgroup

        # a dummy widget to hold the widgets in a group
        tmpw=QtWidgets.QWidget()
        # alternating coloring
        if gid%2==1:
            tmpw.setStyleSheet('background-color: %s;'\
                    %hi_color.color().name())

        grid=QtWidgets.QGridLayout(tmpw)
        crow=0
        del_group_button=QtWidgets.QToolButton(self)
        del_group_button.setText('Del Group')
        del_group_button.clicked.connect(lambda: self.delGroupClicked(gid, tmpw))
        grid.addWidget(del_group_button, 0, 0)

        checkbox=QtWidgets.QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda on: self.groupCheckStateChange(on,
            tmpw))
        self.groupbox.addButton(checkbox, gid)
        grid.addWidget(checkbox, 1, 0)

        # add unique values
        for jj,vjj in enumerate(members):

            radiojj=QtWidgets.QRadioButton()

            text_editjj=QtWidgets.QLineEdit()
            text_editjj.setFont(font)
            text_editjj.setText(vjj)
            text_editjj.setReadOnly(True)

            # create a del entry button
            font_height=QFontMetrics(text_editjj.font()).height()
            button=createDelButton(font_height)
            button.clicked.connect(lambda: self.delValueButtonClicked(
                gid, tmpw))

            # create a show details button
            detail_button=QtWidgets.QToolButton()
            detail_button.setText('Docs')
            detail_button.clicked.connect(lambda x, t=vjj: self.openRelatedDialog(
                t))

            grid.addWidget(radiojj,crow,1)
            grid.addWidget(text_editjj,crow,2)
            grid.addWidget(button,crow,3)
            grid.addWidget(detail_button,crow,4)
            rgroup.addButton(radiojj)
            self.button_le_dict[radiojj]=text_editjj


            radiojj.toggled.connect(lambda on: self.radioButtonStateChange(
                on, tmpw))
            if jj==0:
                radiojj.setChecked(True)
            crow+=1

        self.merge_grid.addWidget(tmpw)

        return

    @pyqtSlot(int, QtWidgets.QWidget)
    def radioButtonStateChange(self, on, widget):

        grid=widget.layout()
        idx=grid.indexOf(self.sender())
        rowid=grid.getItemPosition(idx)[0]

        textwidget=grid.itemAtPosition(rowid, 2).widget()
        if on:
            textwidget.setReadOnly(False)
        else:
            textwidget.setReadOnly(True)

        return

    @pyqtSlot(int, QtWidgets.QWidget)
    def groupCheckStateChange(self, on, widget):

        grid=widget.layout()
        nrow=grid.rowCount()
        ncol=grid.columnCount()
        sender=self.sender()

        for ii in range(nrow):
            for jj in range(ncol):
                itemij=grid.itemAtPosition(ii, jj)
                if itemij:
                    wij=itemij.widget()
                    if wij == sender:
                        continue
                    if hasattr(wij, 'setEnabled'):
                        wij.setEnabled(True if on>0 else False)

        return



    def checkboxGroupChanged(self, on, groupbox):
        '''Change check states in the omit keys checkbox group as a whole'''

        for box in groupbox.buttons():
            box.toggle()

        return


    def getCheckedGroups(self):
        '''Collect check states in the omit key checkbox group'''

        checked=[]

        for box in self.groupbox.buttons():
            if box.isChecked():
                checked.append(self.groupbox.id(box))

        print('# <getCheckedGroups>: checked=',checked)
        return checked


    @pyqtSlot(int, QtWidgets.QWidget)
    def delValueButtonClicked(self, gid, widget):

        grid=widget.layout()
        #nrow=grid.rowCount()
        #button=self.sender()
        idx=grid.indexOf(self.sender())
        rowid=grid.getItemPosition(idx)[0]

        textwidget=grid.itemAtPosition(rowid, 2).widget()
        text=textwidget.text()

        values=self.group_dict[gid]['members']
        if text in values:
            values.remove(text)
            self.group_dict[gid]['members']=values

        for jj in range(grid.columnCount()):
            itemjj=grid.itemAtPosition(rowid, jj)
            if itemjj:
                wjj=itemjj.widget()
                wjj.setParent(None)
                wjj.deleteLater()

        #---------Delete the group if only 1 left---------
        # NOTE that the rowcount() method doesn't decrease!!!
        if len(values)<2:
            self.delGroupClicked(gid, widget)


        return





    @pyqtSlot(int, QtWidgets.QWidget)
    def delGroupClicked(self, gid, widget):

        if gid in self.group_dict:
            del self.group_dict[gid]
        if gid in self.collect_dict:
            del self.collect_dict[gid]
        if gid in self.button_le_dict:
            del self.button_le_dict[gid]

        idx=self.merge_grid.indexOf(widget)
        if idx != -1:
            item=self.merge_grid.takeAt(idx)
            if item:
                item.widget().deleteLater()

            # recolor
            self.alternateColor()

        return


    def alternateColor(self):

        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        n=self.merge_grid.count()
        for ii in range(n):
            wii=self.merge_grid.itemAt(ii).widget()
            if ii%2==0:
                wii.setStyleSheet('background-color: %s;'\
                        %hi_color.color().name())
            else:
                wii.setStyleSheet('background-color: rgb(255,255,255);')

        return


    @pyqtSlot()
    def previewMerge(self):
        pass


    @pyqtSlot(bool, str)
    def openRelatedDialog(self, filter_text):

        current_task=self.parent.current_task
        meta_dict=self.parent.meta_dict

        if current_task=='Authors':
            filter_type='Filter by authors'
        elif current_task=='Journals':
            filter_type='Filter by publications'
        elif current_task=='Keywords':
            filter_type='Filter by keywords'
        elif current_task=='Tags':
            filter_type='Filter by tags'

        filter_docids=sqlitedb.filterDocs(meta_dict,
                meta_dict.keys(),
                filter_type, filter_text)

        print('# <openRelatedDialog>: filter_docids=',filter_docids)

        if not hasattr(self, 'related_doc_diag'):
            print('# <openRelatedDialog>: create new diag')
            self.related_doc_diag=RelatedDocsDialog(meta_dict,
                    self.settings, self)

        if len(filter_docids)>0:
            self.related_doc_diag.loadDocTable(filter_docids)
        self.related_doc_diag.show()

        return


class RelatedDocsDialog(QtWidgets.QDialog):

    def __init__(self, meta_dict, settings, parent):
        super().__init__(parent=parent)

        self.meta_dict=meta_dict
        self.settings=settings
        self.parent=parent

        self.resize(700,600)
        self.setWindowTitle('Related documents')
        self.setWindowModality(Qt.NonModal)

        v_layout=QtWidgets.QVBoxLayout(self)
        #h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)

        self.doc_table=self.createDocTable()
        v_layout.addWidget(self.doc_table)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(self.accept)
        #self.buttons.rejected.connect(self.reject)
        v_layout.addWidget(self.buttons)


    def createDocTable(self):

        tv=QtWidgets.QTableView(self)

        hh=MyHeaderView(self)

        tv.setHorizontalHeader(hh)
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        #tv.setSortingEnabled(True)

        #tv.setDragEnabled(True)
        #tv.setSectionsMovable(True)
        #tv.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        header=['docid','favourite','read','has_file','author','title',
                'journal','year','added','confirmed']
        tablemodel=TableModel(self,[],header,self.settings)
        #tablemodel.dataChanged.connect(self.modelDataChanged)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True) # doc id column, hide
        tv.setColumnHidden(9,True) # needs review column, shown as bold/normal

        #tv.selectionModel().currentChanged.connect(self.selDoc)
        #tv.clicked.connect(self.docTableClicked)
        #tablemodel.rowsInserted.connect(self.model_insert_row)
        #tv.setContextMenuPolicy(Qt.CustomContextMenu)
        #tv.customContextMenuRequested.connect(self.docTableMenu)

        #tv.doubleClicked.connect(self.docDoubleClicked)
        tv.setAlternatingRowColors(True)

        # NOTE: this seems to be change somewhere between PyQt5.6.0 and
        # PyQt5.12.1 that the latter default to setWordWrap(True)
        tv.setWordWrap(False)

        tv.setStyleSheet('''alternate-background-color: rgb(230,230,249);
                background-color: none''')

        return tv


    def loadDocTable(self, docids=None, sortidx=4, sortorder=0, sel_row=None):
        """Load the doc table

        Kwargs:
            folder ((fname_in_str, fid_in_str) or None ): if tuple, load docs
                   within the folder. If None, load the <All> folder.
            docids (list or None): if list, a list of doc ids to load. If None,
                                   load according to the <folder> arg.
            sortidx (int or None or False): int in [0,9], index of the column
                to sort the table. If None, use current sortidx.
                If False, don't do sorting. This last case is for adding new
                docs to the folder and I want the new docs to appear at the
                end, so scrolling to and selecting them is easier, and makes
                sense.
            sortorder (int): sort order, Qt.AscendingOrder (0), or
                             Qt.DescendingOrder (1), order to sort the columns.
                           with.
            sel_row (int or None): index of the row to select after loading.
                                   If None, don't change selection.
        """

        tablemodel=self.doc_table.model()
        #hh=self.doc_table.horizontalHeader()

        #-------------Format data to table rows-------------
        data=prepareDocs(self.meta_dict, docids)
        tablemodel.arraydata=data

        if len(data)>0:
            #--------------------Sort rows--------------------
            tablemodel.sort(sortidx, sortorder)

        tablemodel.layoutChanged.emit()

        return
