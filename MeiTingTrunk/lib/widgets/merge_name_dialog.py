'''
Merge similar terms dialog.

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
from fuzzywuzzy import fuzz
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QBrush, QFontMetrics
from PyQt5.QtWidgets import QDialogButtonBox
from ..tools import getHLine, dfsCC, getSqlitePath,\
        createDelButton
from .threadrun_dialog import ThreadRunDialog
from .doc_table import MyHeaderView, TableModel
from .. import sqlitedb
from ..._MainFrameLoadData import prepareDocs

LOGGER=logging.getLogger(__name__)




class MergeNameDialog(QtWidgets.QDialog):

    def __init__(self, db, meta_dict, scores_dict, settings, parent):
        '''
        Args:
            db (sqlite connection): sqlite connection.
            meta_dict (dict): meta data of all documents. keys: docid,
                values: DocMeta dict.
            scores_dict (dict): a caching dict to save fuzzy matching scores:
                keys: (str1, str2), values: fuzzy ratio in int.
                This dict is passed in from the main window so compuations
                done during software running can be cached.
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
        '''

        super().__init__(parent=parent)

        self.db=db
        self.meta_dict=meta_dict
        self.settings=settings
        self.parent=parent

        self.scores_dict=scores_dict

        # cache scores for categories. keys: category_name_in_str (e.g.
        #    'Authors', 'Journals'). values: dict{(str1, str2): score12,
        #                                         (str1, str3): score13, ...}
        self.cate_dict={}

        # returned by dialog, if True, tell main window to reload data
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
        self.apply_button=self.buttons.addButton('Apply',
                QDialogButtonBox.ApplyRole)

        self.apply_button.clicked.connect(self.doMerge)
        self.buttons.rejected.connect(self.reject)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)

        # a non-modal dialog to show related docs in a doc table
        self.related_doc_diag=RelatedDocsDialog(self.meta_dict,
                self.settings, self)


    def exec_(self):
        '''Overwrite to return reload_gui'''

        super().exec_()
        LOGGER.debug('reload_gui = %s' %self.reload_gui)
        self.related_doc_diag.accept()

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
            self.content_frame=self.loadTab('Authors')
        elif item_text=='Merge Journal Names':
            self.content_frame=self.loadTab('Journals')
        elif item_text=='Merge Keywords':
            self.content_frame=self.loadTab('Keywords')
        elif item_text=='Merge Tags':
            self.content_frame=self.loadTab('Tags')

        self.content_vlayout.insertWidget(0,self.content_frame)

        return


    def createFrame(self, title):
        '''Create a frame for a category page

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

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(label3)
        ha.addWidget(self.spinbox)
        va.addLayout(ha)
        va.addWidget(getHLine(self))

        #-------------------Number label-------------------
        self.number_label=QtWidgets.QLabel()
        label.setTextFormat(Qt.RichText)
        va.addWidget(self.number_label)
        va.addWidget(getHLine(self))

        #----------------Select all button----------------
        self.sel_all_button=QtWidgets.QCheckBox('Select All', self)
        self.sel_all_button.setChecked(True)

        #---------------Start search button---------------
        self.search_button=QtWidgets.QToolButton(self)
        self.search_button.setText('Search')
        self.search_button.clicked.connect(self.searchButtonClicked)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.sel_all_button)
        ha.addWidget(self.search_button)
        va.addLayout(ha)

        #--------Frame to show similar term groups--------
        self.merge_frame=MergeFrame(self.settings, self)
        self.no_dup_label=QtWidgets.QLabel('No Similar Names Found')
        self.no_dup_label.setVisible(False)
        va.addWidget(self.no_dup_label)
        va.addWidget(self.merge_frame)

        return scroll, va


    def loadTab(self, category_name):
        '''Load a category'''

        scroll,va=self.createFrame('Merge %s Names' %category_name)
        self.current_task=category_name
        docids=list(self.meta_dict.keys())

        if category_name=='Authors':
            key='authors_l'
        elif category_name=='Journals':
            key='publication'
        elif category_name=='Keywords':
            key='keywords_l'
        elif category_name=='Tags':
            key='tags_l'

        # get terms
        self.text_list=sqlitedb.fetchMetaData(self.meta_dict, key, docids,
                unique=True,sort=True)
        n_unique=len(self.text_list)
        self.number_label.setText('NO. of unique terms in library = <span style="font:bold;">%d</span>' %n_unique)

        # if in cache, skip computation
        if self.current_task in self.cate_dict:
            self.addResults(self.cate_dict[self.current_task])

        return scroll


    @pyqtSlot()
    def delFromCache(self, key):
        '''Delete scores of a category from cache

        Args:
            key (str): category name, one of 'Authors', 'Journals', 'Keywords',
                       'Tags'.
        '''

        if key in self.cate_dict:
            LOGGER.debug('Delete from cache: %s' %key)
            del self.cate_dict[key]

        return


    @pyqtSlot()
    def searchButtonClicked(self):
        '''Start search for similar terms
        '''

        # if in cache, skip computation
        if self.current_task in self.cate_dict:
            LOGGER.debug('Key %s in cache' %self.current_task)
            self.addResults(self.cate_dict[self.current_task])
        else:
            LOGGER.debug('Key %s not in cache' %self.current_task)
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
            # if abort, del key from cache and disconnect all_done_signal
            self.thread_run_dialog1.abort_job_signal.connect(lambda:\
                    (self.delFromCache(self.current_task),
                    self.thread_run_dialog1.master.all_done_signal.disconnect()))
            self.thread_run_dialog1.exec_()

        return


    def prepareJoblist(self, jobid, text_list):
        '''Prepare job list for threaded fuzzy matching computations

        Args:
            jobid (int): jobid, value insignificant.
            text_list (list): list of terms among which to match similars.

        Returns:
            rec (int): 0 if successful, crash otherwise.
            jobid (int): input jobid.
            job_list (list): list of str pairs: [(str1, str2), (str1, str3),
                             ...]
        '''

        n=len(text_list)
        job_list=[]
        # a dict for this category. key: (str1, str2), value: fuzzy ratio
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
                    # shortcut: if in cache:
                    if (tii, tjj) in self.scores_dict:
                        sdict[(tii, tjj)]=self.scores_dict[(tii, tjj)]
                        continue
                    # shortcut: skip if 1st letter don't match
                    if tii[0].lower() != tjj[0].lower():
                        sdict[(tii, tjj)]=0
                        continue
                    # shortcut: skip if string len diff >= 50%
                    if abs(len(tii)-len(tjj))>=\
                            max(len(tii), len(tjj))//2:
                        sdict[(tii, tjj)]=0
                        continue

                    if (tii, tjj) not in sdict:
                        job_list.append((jobid2, tii, tjj))
                        jobid2+=1

        LOGGER.info('len(job_list) = %d' %len(job_list))

        return 0,jobid,job_list


    @pyqtSlot()
    def jobListReady(self):
        '''After getting all jobs, launch threads and process jobs
        '''

        rec,jobid,job_list=self.thread_run_dialog1.results[0]
        QtWidgets.QApplication.processEvents() # seems needed
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
            # if job_list empty, no new jobs to compute, got all scores from
            # cache.
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

        # save to cache for use during this dialog is open
        self.cate_dict[self.current_task]=sdict
        # save to cache for use during this app is running
        self.scores_dict.update(sdict)
        LOGGER.info('Duplicate search results collected.')
        self.addResults(sdict)

        return


    @pyqtSlot()
    def addResults(self, sdict):
        '''Add matching results to frame'''

        edges=[kk for kk,vv in sdict.items() if vv>=self.spinbox.value()]
        # if no duplicates, return
        if len(edges)==0:
            self.no_dup_label.setVisible(True)
            LOGGER.info('No duplicate found.')
            return

        self.no_dup_label.setVisible(False)

        #--------------------Get groups--------------------
        groups={}  # key: gid, value: list of terms in same group

        # get connected components
        comps=dfsCC(edges)
        for ii,cii in enumerate(comps):
            cii.sort()
            groups[ii]=cii

        # sort by alphabetic
        headers=sorted(groups.keys(), key=lambda x: groups[x],
                reverse=False)

        self.group_dict=OrderedDict()
        # key: groupid, value: dict: {'header': one term,
        #                             'members': list of all terms in group}

        # clear existing data in frame
        self.merge_frame.clearMergeLayout()

        for ii,gii in enumerate(headers):
            members=groups[gii]
            textii=members[0]

            # add to group_dict
            self.group_dict[ii]={'header': textii, 'members' : members}

            # add to merge_frame
            self.merge_frame.addGroup(ii, self.group_dict)

        return


    @pyqtSlot()
    def doMerge(self):
        '''Apply term merging in response to the Apply button click

        '''

        choice=QtWidgets.QMessageBox.question(self, 'Confirm Merge',
                'Changes can not be reverted. Confirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice==QtWidgets.QMessageBox.No:
            return

        LOGGER.info('Applying task = %s' %self.current_task)

        collect_dict=self.merge_frame.collect_dict
        group_dict=self.merge_frame.group_dict
        button_le_dict=self.merge_frame.button_le_dict
        sel_groups=self.merge_frame.getCheckedGroups()
        job_list=[]

        for gidii in group_dict:

            # skip if group de-selected
            if gidii not in sel_groups:
                continue

            rgroupii=collect_dict[gidii]
            checked=rgroupii.checkedButton()
            # get the corresponding textedit/lineedit
            textwidget=button_le_dict[checked]
            newterm=textwidget.text()
            # get members from button group
            members=[button_le_dict[tii].text() for tii in rgroupii.buttons()]
            LOGGER.info('New term = %s. Group = %s' %(newterm, members))
            job_list.append((members, newterm))

        if len(job_list)==0:
            return

        # call save first
        # probably can't use signal as i have to wait for it to complete.
        self.parent.saveDatabaseTriggered()

        for old_listii, newtermii in job_list:
            sqlitedb.replaceTerm(self.db, self.current_task, old_listii,
                    newtermii)

        # remove from cache
        del self.cate_dict[self.current_task]

        # clear frame
        self.merge_frame.clearMergeLayout()

        # reload data, delay load_to_gui till dialog closing
        self.parent.loadSqlite(getSqlitePath(self.db), load_to_gui=False)
        self.meta_dict=self.parent.main_frame.meta_dict
        # reload current category. can't just call loadTab().
        self.cateSelected(self.cate_list.currentItem())
        self.reload_gui=True

        return



class MergeFrame(QtWidgets.QScrollArea):

    def __init__(self, settings, parent=None):
        '''Interface for resolving conflicts in duplicate merging

        Args:
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
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

        # select all button
        self.sel_all_button=self.parent.sel_all_button

        # buttongroup, used with sel_all_button to toggle all checkboxes
        self.button_group=QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(False)

        self.sel_all_button.toggled.connect(lambda on: \
                self.invertAllSelection(on, self.button_group))

        # vbox layout, will be filled in addGroup
        self.merge_layout=QtWidgets.QVBoxLayout()
        va.addLayout(self.merge_layout)
        va.addStretch()

        frame.setLayout(va)

        self.group_dict={}
        # key: groupid, value: dict: {'header': one term,
        #                             'members': list of all terms in group}
        self.collect_dict={} # key: gid, value: buttongroup containing radiobuttons
        self.button_le_dict={} # key: radiobutton:
                               # value: textedit/lineedit


    def clearMergeLayout(self):
        '''Clear the merge layout'''

        def clearLayout(layout):
            '''Recursively clear a layout'''
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    try:
                        clearLayout(child.widget().layout())
                    except:
                        pass
                    child.widget().setParent(None)
                    child.widget().deleteLater()
            return

        clearLayout(self.merge_layout)
        self.collect_dict={}
        self.button_le_dict={}

        return


    def addGroup(self, gid, group_dict):
        '''Add to frame a merging group

        Args:
            gid (int): group id.
            group_dict (dict): group info. key: groupid, value: dict:
                               {'header': one term,
                                'members': list of all terms in group}.
        '''

        self.group_dict=group_dict
        members=group_dict[gid]['members']

        font=self.settings.value('display/fonts/doc_table',QFont)
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        rgroup=QtWidgets.QButtonGroup(self) # NOTE: has to add self
        rgroup.setExclusive(True)
        self.collect_dict[gid]=rgroup

        # a dummy widget to hold the widgets in a group
        tmpw=QtWidgets.QWidget()
        # alternating coloring
        if gid%2==0:
            tmpw.setStyleSheet('background-color: %s;'\
                    %hi_color.color().name())

        grid=QtWidgets.QGridLayout(tmpw)
        crow=0

        # delete group button
        del_group_button=QtWidgets.QToolButton(self)
        del_group_button.setText('Del Group')
        del_group_button.clicked.connect(lambda: self.delGroupClicked(
            gid, tmpw))
        grid.addWidget(del_group_button, 0, 0)

        # selection checkbox
        checkbox=QtWidgets.QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda on: self.groupCheckStateChange(on,
            tmpw))
        self.button_group.addButton(checkbox, gid)
        grid.addWidget(checkbox, 1, 0)

        # add unique values
        for jj,vjj in enumerate(members):

            # radio button
            radiojj=QtWidgets.QRadioButton()
            rgroup.addButton(radiojj)
            radiojj.toggled.connect(lambda on: self.radioButtonStateChange(
                on, tmpw))

            # textedit
            text_editjj=QtWidgets.QLineEdit()
            text_editjj.setFont(font)
            text_editjj.setText(vjj)
            text_editjj.setReadOnly(True)

            # del entry button
            font_height=QFontMetrics(text_editjj.font()).height()
            button=createDelButton(font_height)
            button.clicked.connect(lambda: self.delValueButtonClicked(
                gid, tmpw))

            # show related button
            detail_button=QtWidgets.QToolButton()
            detail_button.setText('Docs')
            detail_button.clicked.connect(lambda: self.openRelatedDialog(tmpw))

            grid.addWidget(radiojj,crow,1)
            grid.addWidget(text_editjj,crow,2)
            grid.addWidget(button,crow,3)
            grid.addWidget(detail_button,crow,4)
            self.button_le_dict[radiojj]=text_editjj

            if jj==0:
                # has to do this AFTER connecting radiojj.toggled
                radiojj.setChecked(True)
            crow+=1

        self.merge_layout.addWidget(tmpw)
        LOGGER.debug('Added group %s' %gid)

        return


    @pyqtSlot(int, QtWidgets.QWidget)
    def radioButtonStateChange(self, on, widget):
        '''Change textedit readonly depending on radiobutton state

        Args:
            on (int): radiobutton state.
            widget (QtWidgets.QWidget): container widget of the radiobutton.
        '''

        # find the related textedit
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
        '''Diable/enable widgets in a group depending on checkbox state

        Args:
            on (int): checkbox state.
            widget (QtWidgets.QWidget): container widget of the checkbox.
        '''

        grid=widget.layout()
        nrow=grid.rowCount()
        ncol=grid.columnCount()
        sender=self.sender()

        # loop through grid
        for ii in range(nrow):
            for jj in range(ncol):
                itemij=grid.itemAtPosition(ii, jj)
                if itemij:
                    wij=itemij.widget()
                    # don't disable the checkbox itself
                    if wij == sender:
                        continue
                    if hasattr(wij, 'setEnabled'):
                        wij.setEnabled(True if on>0 else False)

        return


    @pyqtSlot(int, QtWidgets.QButtonGroup)
    def invertAllSelection(self, on, button_group):
        '''Invert all checkbox states

        Args:
            on (int): invert checkbox state. Not used.
            button_group (QtWidgets.QButtonGroup): buttongroup containg all
                children buttons, whose states will be inverted.
        '''

        for box in button_group.buttons():
            box.toggle()

        return


    def getCheckedGroups(self):
        '''Collect check states in the checkbox buttongroup

        Returns:
            checked (list): list of group ids checked.
        '''

        checked=[]

        for box in self.button_group.buttons():
            if box.isChecked():
                checked.append(self.button_group.id(box))

        LOGGER.debug('Checked groups: %s' %checked)

        return checked


    @pyqtSlot(int, QtWidgets.QWidget)
    def delValueButtonClicked(self, gid, widget):
        '''Delete a term from group in response to del button click

        Args:
            gid (int): id of group from which the value is in.
            widget (QtWidgets.QWidget): container widget of the checkbox.
        '''

        # find the related textedit
        grid=widget.layout()
        idx=grid.indexOf(self.sender())
        rowid=grid.getItemPosition(idx)[0]
        textwidget=grid.itemAtPosition(rowid, 2).widget()
        text=textwidget.text()

        values=self.group_dict[gid]['members']
        if text in values:
            values.remove(text)
            self.group_dict[gid]['members']=values

        # del widgets in the row
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
        '''Delete a group in response to del button click

        Args:
            gid (int): id of group from which the value is in.
            widget (QtWidgets.QWidget): container widget of the checkbox.
        '''

        if gid in self.group_dict:
            del self.group_dict[gid]
        if gid in self.collect_dict:
            del self.collect_dict[gid]

        idx=self.merge_layout.indexOf(widget)
        if idx != -1:
            item=self.merge_layout.takeAt(idx)
            if item:
                item.widget().setParent(None)
                item.widget().deleteLater()

            # recolor
            self.alternateColor()

        return


    def alternateColor(self):
        '''Give alternating background colors to groups'''

        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        n=self.merge_layout.count()
        for ii in range(n):
            wii=self.merge_layout.itemAt(ii).widget()
            if ii%2==0:
                wii.setStyleSheet('background-color: %s;'\
                        %hi_color.color().name())
            else:
                wii.setStyleSheet('background-color: rgb(255,255,255);')

        return


    @pyqtSlot(QtWidgets.QWidget)
    def openRelatedDialog(self, widget):
        '''Open related doc dialog in response to detail_button click

        Args:
            widget (QtWidgets.QWidget): container widget of the checkbox.
        '''

        # find the related textedit
        grid=widget.layout()
        idx=grid.indexOf(self.sender())
        rowid=grid.getItemPosition(idx)[0]
        textwidget=grid.itemAtPosition(rowid, 2).widget()
        text=textwidget.text()

        if len(text)==0:
            self.parent.related_doc_diag.loadDocTable([])
            return

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
                filter_type, text)

        LOGGER.debug('term = %s' %text)
        LOGGER.debug('filter_docids = %s' %filter_docids)

        self.parent.related_doc_diag.loadDocTable(filter_docids)
        self.parent.related_doc_diag.show()

        return



class RelatedDocsDialog(QtWidgets.QDialog):

    def __init__(self, meta_dict, settings, parent):
        '''A dialog show a doc table containing related documents of a term

        Args:
            meta_dict (dict): meta data of all documents. keys: docid,
                values: DocMeta dict.
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
        '''

        super().__init__(parent=parent)

        self.meta_dict=meta_dict
        self.settings=settings
        self.parent=parent

        self.resize(700,600)
        self.setWindowTitle('Related documents')
        self.setWindowModality(Qt.NonModal)
        v_layout=QtWidgets.QVBoxLayout(self)

        self.doc_table=self.createDocTable()
        v_layout.addWidget(self.doc_table)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        v_layout.addWidget(self.buttons)


    def createDocTable(self):
        '''Create a table view as doc table'''

        tv=QtWidgets.QTableView(self)
        hh=MyHeaderView(self)

        tv.setHorizontalHeader(hh)
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        #tv.setSortingEnabled(True)  # dont enable sort!

        header=['docid','favourite','read','has_file','author','title',
                'journal','year','added','confirmed']
        tablemodel=TableModel(self,[],header,self.settings)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True) # doc id column, hide
        tv.setColumnHidden(9,True) # needs review column, shown as bold/normal
        tv.setAlternatingRowColors(True)

        # NOTE: this seems to be change somewhere between PyQt5.6.0 and
        # PyQt5.12.1 that the latter default to setWordWrap(True)
        tv.setWordWrap(False)

        tv.setStyleSheet('''alternate-background-color: rgb(230,230,249);
                background-color: none''')

        return tv


    def loadDocTable(self, docids, sortidx=4, sortorder=0):
        """Load the doc table

        Args:
            docids (list): if list, a list of doc ids to load.

        Kwargs:
            sortidx (int): int in [0,9], index of the column
                to sort the table.
            sortorder (int): sort order, Qt.AscendingOrder (0), or
                         Qt.DescendingOrder (1), order to sort the columns.
        """

        tablemodel=self.doc_table.model()

        #-------------Format data to table rows-------------
        data=prepareDocs(self.meta_dict, docids)
        tablemodel.arraydata=data

        if len(data)>0:
            #--------------------Sort rows--------------------
            tablemodel.sort(sortidx, sortorder)

        tablemodel.layoutChanged.emit()

        return
