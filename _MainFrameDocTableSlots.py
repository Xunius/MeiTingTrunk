import os
import subprocess
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QModelIndex
from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont, QBrush, QColor, QCursor, QIcon
from lib import sqlitedb
from lib import bibparse, risparse
from lib.tools import parseAuthors
from lib.widgets import Master, FailDialog
import logging


class MainFrameDocTableSlots:

    #######################################################################
    #                           Doc table slots                           #
    #######################################################################

    @pyqtSlot()
    def docTableClicked(self):

        self.logger.debug('Doc table clicked. Set to extendedselection.')

        self.doc_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # count selected docs
        sel_rows=self.doc_table.selectionModel().selectedRows()
        if len(sel_rows)>1:
            self.status_bar.showMessage('%d rows selected. %d rows in total'\
                    %(len(sel_rows), self.doc_table.model().rowCount(None)))

        return


    @pyqtSlot(QModelIndex, QModelIndex)
    def modelDataChanged(self,index1,index2):
        assert index1==index2, 'only one doc row is changed'
        # NOTE that the row is in general different from
        # self.doc_table.currentIndex().row(), the former may not change on
        # clicking the checkboxes
        row=index1.row()

        docid=self._tabledata[row][0]
        fav=self._tabledata[row][1].isChecked()
        read=self._tabledata[row][2].isChecked()

        self.meta_dict[docid]['favourite']='true' if fav else 'false'
        self.meta_dict[docid]['read']='true' if read else 'false'

        self.logger.info('Changed row = %s. Changed docid = %s. meta_dict["favourite"] = %s. meta_dict["read"] = %s' \
                %(row, docid, self.meta_dict[docid]['favourite'],\
                self.meta_dict[docid]['read']))

        self.changed_doc_ids.append(docid)

        return


    @pyqtSlot(QModelIndex, QModelIndex)
    def selDoc(self,current,previous):
        '''Actions on selecting a document in doc table
        '''
        rowid=current.row()
        docid=self._tabledata[rowid][0]

        self.logger.info('Selected rowid = %s. docid = %s' %(rowid, docid))

        self.loadMetaTab(docid)
        self.loadBibTab(docid)
        self.loadNoteTab(docid)

        #------------Remove highlights for all------------
        self.removeFolderHighlights()

        #-------------------Get folders-------------------
        folders=self.meta_dict[docid]['folders_l']
        folders=[str(fii[0]) for fii in folders]

        self.logger.debug('Ids of folders containing doc (%s): %s' %(docid, folders))

        #---------Highlight folders contaning doc---------
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)
        for fii in folders:
            mii=self.libtree.findItems(fii, Qt.MatchExactly | Qt.MatchRecursive,
                    column=1)
            if len(mii)>0:
                for mjj in mii:
                    mjj.setBackground(0, hi_color)

        #------------Show confirm review frame------------
        if self.meta_dict[docid]['confirmed'] in [None, 'false']:
            self.confirm_review_frame.setVisible(True)
        else:
            self.confirm_review_frame.setVisible(False)

        return


    def docTableMenu(self,pos):

        menu=QtWidgets.QMenu()
        current_folderid=self._current_folder_item.data(1,0)
        trashed_folder_ids=self._trashed_folder_ids+['-3']

        open_action=menu.addAction('&Open File Externally')
        open_action.setIcon(QIcon.fromTheme('document-open'))
        open_action.setShortcut('O')

        open_folder_action=menu.addAction('Open Containing &Folder')
        #open_folder_action.setIcon(QIcon.fromTheme('system-file-manager'))
        open_folder_action.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_DirIcon))
        open_folder_action.setShortcut('F')

        #-----------------Deletion actions-----------------
        del_from_folder_action=QtWidgets.QAction('&Delete From Current Folder',
                menu)
        del_from_folder_action.setIcon(QIcon.fromTheme('user-trash'))
        del_from_folder_action.setShortcut('D')

        del_from_lib_action=QtWidgets.QAction('Delete From Library',menu)
        del_from_lib_action.setIcon(QIcon.fromTheme('user-trash'))

        del_from_trash_action=QtWidgets.QAction('Delete From Trash',menu)
        del_from_trash_action.setIcon(QIcon.fromTheme('edit-delete'))

        if current_folderid=='-1':
            menu.addAction(del_from_lib_action)
        elif current_folderid=='-2':
            pass
        elif current_folderid in trashed_folder_ids:
            menu.addAction(del_from_trash_action)
        else:
            menu.addAction(del_from_folder_action)
            menu.addAction(del_from_lib_action)

        #-------------Mark needs review action-------------
        mark_needsreview_action=QtWidgets.QAction('&Mark document as Needs Review',menu)
        mark_needsreview_action.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_MessageBoxInformation))
        mark_needsreview_action.setShortcut('M')

        if current_folderid!='-2':
            menu.addAction(mark_needsreview_action)

        #--------------Duplicate check action--------------
        check_duplicate_folder_action=menu.addAction('Check Du&plicates Within Folder')
        check_duplicate_folder_action.setIcon(QIcon.fromTheme('edit-find'))
        check_duplicate_folder_action.setShortcut('P')

        check_duplicate_lib_action=menu.addAction('Check Duplicates Within Library')
        check_duplicate_lib_action.setIcon(QIcon.fromTheme('edit-find'))

        #------------------Export actions------------------
        menu.addSeparator()
        export_bib_action=menu.addAction('Export to &bibtex File')
        export_bib_action.setIcon(QIcon.fromTheme('document-save-as'))
        export_bib_action.setShortcut('B')

        export_ris_action=menu.addAction('Export to &RIS File')
        export_ris_action.setIcon(QIcon.fromTheme('document-save-as'))
        export_ris_action.setShortcut('R')

        copy_clipboard_action=menu.addAction('Export Citation To &Clipboard')
        copy_clipboard_action.setIcon(QIcon.fromTheme('edit-copy'))
        copy_clipboard_action.setShortcut('C')

        sel_rows=self.doc_table.selectionModel().selectedRows()
        sel_rows=[ii.row() for ii in sel_rows]

        if len(sel_rows)>0:

            docids=[self._tabledata[ii][0] for ii in sel_rows]
            has_files=[self.meta_dict[docii]['has_file'] for docii in docids]

            self.logger.info('Selected docids = %s. has_files = %s'\
                    %(docids, has_files))

            if any(has_files):
                open_action.setEnabled(True)
                open_folder_action.setEnabled(True)
            else:
                open_action.setDisabled(True)
                open_folder_action.setDisabled(True)

            action=menu.exec_(QCursor.pos())

            if action:
                self.logger.info('action.text() = %s' %action.text())

                if action==open_action:
                    open_docs=[docids[ii] for ii in range(len(docids)) if has_files[ii]]
                    self.openDoc(open_docs)

                elif action==open_folder_action:
                    open_docs=[docids[ii] for ii in range(len(docids)) if has_files[ii]]
                    self.openDocFolder(open_docs)

                elif action==del_from_folder_action:
                    foldername,folderid=self._current_folder
                    self.delFromFolder(docids, foldername, folderid, True)

                elif action==del_from_lib_action:
                    self.delDoc(docids,True)

                elif action==del_from_trash_action:
                    self.destroyDoc(docids,current_folderid,True,True)

                elif action==mark_needsreview_action:
                    self.markDocNeedsReview(docids)

                elif action==check_duplicate_folder_action:
                    self.checkDocDuplicate(docids,'folder')

                elif action==check_duplicate_lib_action:
                    self.checkDocDuplicate(docids,'lib')

                elif action==export_bib_action:
                    self.exportToBib(docids,self.meta_dict)

                elif action==export_ris_action:
                    self.exportToRIS(docids,self.meta_dict)

                elif action==copy_clipboard_action:
                    self.copyToClipboard(docids,style=None)

        return


    def openDoc(self,docids):

        self.logger.info('docids = %s' %docids)
        lib_folder=self.settings.value('saving/current_lib_folder',str)

        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file
            file_pathii=os.path.join(lib_folder,file_pathii)

            if not os.path.exists(file_pathii):
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText("Can't find file.")
                msg.setInformativeText("No such file: %s. Please re-attach the document file." %file_pathii)
                msg.exec_()
                return

            self.logger.debug('docid = %s. file_path = %s' %(docii, file_pathii))

            prop=subprocess.call(('xdg-open', file_pathii))
            if prop==0:
                # set read to True
                self.meta_dict[docii]['read']='true'
                self.changed_doc_ids.append(docii)

        # refresh to show read change
        self.loadDocTable(folder=self._current_folder,sortidx=4,
                sel_row=None)

        return


    def openDocFolder(self,docids):

        self.logger.info('docids = %s' %docids)

        #------------Get default file mananger------------
        prop=subprocess.Popen(['xdg-mime','query','default','inode/directory'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        file_man=prop.communicate()[0].decode('ascii').strip().replace('.desktop','')

        #----------------Open file manager----------------
        lib_folder=self.settings.value('saving/current_lib_folder',str)
        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file
            file_pathii=os.path.join(lib_folder,file_pathii)

            self.logger.debug('docid = %s. file_path = %s' %(docii, file_pathii))

            prop=subprocess.call((file_man, file_pathii))

        return


    @pyqtSlot(list, str, str, bool)
    def delFromFolder(self,docids,foldername,folderid,reload_table):

        self.logger.info('docids = %s. foldername = %s. folderid = %s'\
                %(docids, foldername, folderid))

        # remove doc from folder
        for idii in docids:
            self.folder_data[folderid].remove(idii)

            self.logger.debug('folder_data[folderid] = %s' %self.folder_data[folderid])

            # remove folder from doc
            if (int(folderid),foldername) in self.meta_dict[idii]['folders_l']:
                self.meta_dict[idii]['folders_l'].remove((int(folderid),foldername))
                self.changed_doc_ids.append(idii)

                self.logger.debug("meta_dict['folders_l'] = %s"\
                        %self.meta_dict[idii]['folders_l'])

        # check orphan
        orphan_docs=sqlitedb.findOrphanDocs(self.folder_data,docids,
                self._trashed_folder_ids)

        for idii in orphan_docs:
            self.meta_dict[idii]['deletionPending']='true'
            self.folder_data['-3'].append(idii)
            self.changed_doc_ids.append(idii)

            self.logger.debug('Set orphan doc deletionPending to: %s'\
                    %self.meta_dict[idii]['deletionPending'])

        if reload_table:
            self.loadDocTable(folder=(foldername,folderid),sel_row=None)


        return


    def delDoc(self,docids,reload_table):

        self.logger.info('docids = %s' %docids)

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Confirm deleting a document from library?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice==QtWidgets.QMessageBox.Yes:

            for idii in docids:

                # remove from all folders
                for kk,vv in self.folder_data.items():
                    if idii in vv:
                        vv.remove(idii)

                        self.logger.debug('doc %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))

                self.meta_dict[idii]['folders_l']=[]
                self.folder_data['-3'].append(idii)
                self.meta_dict[idii]['deletionPending']='true'
                self.changed_doc_ids.append(idii)

                self.logger.debug('Set orphan doc deletionPending to: %s'\
                        %self.meta_dict[idii]['deletionPending'])

            if reload_table:
                self.loadDocTable(folder=self._current_folder,sel_row=None)

        return


    def markDocNeedsReview(self,docids):

        self.logger.info('docids = %s' %docids)

        for idii in docids:
            self.meta_dict[idii]['confirmed']='false'
            if idii not in self.folder_data['-2']:
                self.folder_data['-2'].append(idii)
            self.changed_doc_ids.append(idii)

            self.logger.debug('Set doc confirmed to: %s. Doc in folder_data[-2]: %s'\
                    %(self.meta_dict[idii]['confirmed'],
                        idii in self.folder_data['-2']))

        row=self.doc_table.currentIndex().row()
        self.loadDocTable(folder=self._current_folder,sortidx=4,
                sel_row=row)

        return


    def destroyDoc(self,docids,current_folderid,ask,reload_table):

        self.logger.info('docids = %s' %docids)

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                    'Confirm deleting a document permanently?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):

            current_foldername=self.folder_dict[current_folderid][0]

            for idii in docids:

                # NOTE!!: if doc still exists in some other folder outside Trash,
                # (which can be tell by deletionPending=='false'), don't del,
                # only remove from current folder.

                if self.meta_dict[idii]['deletionPending']=='false':

                    self.logger.warning('Doc still relevant. Only delete from current folder.')

                    if idii in self.folder_data[current_folderid]:
                        self.folder_data[current_folderid].remove(idii)
                        self.meta_dict[idii]['folders_l'].remove(
                                (int(current_folderid), current_foldername))

                        self.logger.debug('doc %s in folder_data[%s]?: %s'\
                                %(idii, current_folderid,
                                    idii in self.folder_data[current_folderid]))
                        self.logger.debug("current folder id = %s. meta_dict[%s]['folders_l'] = %s" \
                                %(current_folderid, idii,
                                    self.meta_dict[idii]['folders_l']))

                    continue

                # remove from all folders
                for kk,vv in self.folder_data.items():
                    if idii in vv:
                        vv.remove(idii)

                        self.logger.debug('doc %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))

                self.changed_doc_ids.append(idii)
                del self.meta_dict[idii]

                self.logger.info('Deleted %s from meta_dict' %idii)

            if reload_table:
                self.loadDocTable(folder=self._current_folder,sel_row=None)

        return



    def exportToBib(self,docids,meta_dict):

        self.logger.info('docids = %s' %docids)

        if len(docids)==1:
            default_path='%s.bib' %(meta_dict[docids[0]]['citationkey'])
        else:
            default_path='./bibtex.bib'

        self.logger.debug('Default export path = %s' %default_path)

        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Save Citaitons to bib File',
                default_path,
                "bib Files (*.bib);; All files (*)")[0]

        self.logger.info('Chosen bib file = %s' %fname)

        def saveBib(results):
            faillist=[]

            text=''
            for recii,jobii,textii,docii in results:
                if recii==0:
                    text=text+textii+'\n'
                elif recii==1:
                    faillist.append(docii)

            with open(fname,'w') as fout:
                fout.write(text)

            # show failed jobs
            if len(faillist)>0:
                fail_entries=[]
                for docii in faillist:
                    metaii=self.meta_dict[docii]
                    entryii='* %s_%s_%s' %(', '.join(metaii['authors_l']),
                            metaii['year'],
                            metaii['title'])
                    fail_entries.append(entryii)

                msg=FailDialog()
                msg.setText('Oopsie')
                msg.setInformativeText('Failed to export some entires.')
                msg.setDetailedText('\n'.join(fail_entries))
                msg.create_fail_summary.connect(lambda: self.createFailFolder(
                    'bibtext export', faillist))
                msg.exec_()

            return


        if fname:
            omit_keys=self.settings.value('export/bib/omit_fields', [], str)
            if isinstance(omit_keys,str) and omit_keys=='':
                omit_keys=[]

            job_list=[]
            for ii,docii in enumerate(docids):
                job_list.append((ii,meta_dict[docii],omit_keys))
            self.master1=Master(bibparse.metaDictToBib, job_list,
                    1, self.progressbar,
                    'classic', self.status_bar, 'Exporting to bibtex...',
                    post_process_func=saveBib)
            self.master1.run()

        self.logger.info('Bib file exported.')

        return


    def exportToRIS(self,docids,meta_dict):

        self.logger.info('docids = %s' %docids)

        if len(docids)==1:
            default_path='%s.ris' %(meta_dict[docids[0]]['citationkey'])
        else:
            default_path='./RIS.ris'

        self.logger.debug('Default export path = %s' %default_path)

        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Save Citaitons to RIS File',
                default_path,
                "bib Files (*.ris);; All files (*)")[0]

        self.logger.info('Chosen ris file = %s' %fname)

        def saveRIS(results):
            faillist=[]

            text=''
            for recii,jobii,textii,docii in results:
                if recii==0:
                    text=text+textii+'\n'
                elif recii==1:
                    faillist.append(docii)

            with open(fname,'w') as fout:
                fout.write(text)

            # show failed jobs
            if len(faillist)>0:
                fail_entries=[]
                for docii in faillist:
                    metaii=self.meta_dict[docii]
                    entryii='* %s_%s_%s' %(', '.join(metaii['authors_l']),
                            metaii['year'],
                            metaii['title'])
                    fail_entries.append(entryii)

                msg=FailDialog()
                msg.setText('Oopsie')
                msg.setInformativeText('Failed to export some entires.')
                msg.setDetailedText('\n'.join(fail_entries))
                msg.create_fail_summary.connect(lambda: self.createFailFolder(
                    'RIS export', faillist))
                msg.exec_()

            return

        if fname:
            job_list=[]
            for ii,docii in enumerate(docids):
                job_list.append((ii,meta_dict[docii]))
            self.master1=Master(risparse.metaDictToRIS, job_list,
                    1, self.progressbar,
                    'classic', self.status_bar, 'Exporting to RIS...',
                    post_process_func=saveRIS)
            self.master1.run()

        self.logger.info('RIS file created.')

        return


    def copyToClipboard(self,docids,style=None):

        self.logger.info('docids = %s' %docids)

        cb=QtWidgets.QApplication.clipboard()
        meta={}
        meta_list=[]

        for idii in docids:
            docii=self.meta_dict[idii]

            self.logger.debug('docii["authors_l"]=%s' %docii['authors_l'])

            authorsii=parseAuthors(docii['authors_l'])[2]
            if len(authorsii)==0:
                authorsii='UNKNOWN'
            elif len(authorsii)==1:
                authorsii=authorsii[0]
            elif len(authorsii)>=2:
                authorsii=' and '.join(authorsii)

            meta['authors']=authorsii
            meta['year']=docii['year']
            meta['title']=docii['title']
            meta['journal']=docii['publication']
            meta['issue']=docii['issue']
            meta['pages']=docii['pages']

            self.logger.debug('meta = %s' %meta)

            meta_list.append(meta)


        text=''
        for docii in meta_list:
            if style is None:

                textii='%s, %s: %s. %s, <html><b>%s</b></html>, %s' %(docii['authors'],
                        docii['year'],
                        docii['title'],
                        docii['journal'],
                        docii['issue'],
                        docii['pages']
                        )

                text=text+textii+'\n\n'

        cb.setText(text)

        return


    @pyqtSlot(QModelIndex)
    def docDoubleClicked(self,idx):

        row_idx=idx.row()

        self.logger.info('Clicked row=%s' %row_idx)

        docid=self._tabledata[row_idx][0]
        files=self.meta_dict[docid]['files_l']
        nfiles=len(files)

        if nfiles==0:
            return
        elif nfiles==1:
            self.openDoc([docid,])
        else:

            self.logger.info('Multiple files associated with doc. n = %d' %nfiles)

            dialog=QtWidgets.QDialog()
            dialog.resize(500,500)
            dialog.setWindowTitle('Open Files Externally')
            dialog.setWindowModality(Qt.ApplicationModal)
            layout=QtWidgets.QVBoxLayout()
            dialog.setLayout(layout)

            label=QtWidgets.QLabel('Select file(s) to open')
            label_font=QFont('Serif',12,QFont.Bold)
            label.setFont(label_font)
            layout.addWidget(label)

            listwidget=QtWidgets.QListWidget()
            listwidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

            lib_folder=self.settings.value('saving/current_lib_folder',str)
            for fii in files:
                print('# <docDoubleClicked>: fii=',fii)
                fii=os.path.join(lib_folder,fii)
                print('# <docDoubleClicked>: fii=',fii)
                listwidget.addItem(fii)

            listwidget.setCurrentRow(0)
            layout.addWidget(listwidget)

            buttons=QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                Qt.Horizontal, dialog)

            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            rec=dialog.exec_()

            self.logger.debug('return value from dialog: %s' %rec)

            if rec:
                sel_files=listwidget.selectionModel().selectedRows()
                sel_files=[listwidget.item(ii.row()) for ii in sel_files]
                sel_files=[ii.data(0) for ii in sel_files]

                self.logger.info('Selected files=%s' %sel_files)

                if len(sel_files)>0:
                    for fii in sel_files:
                        prop=subprocess.call(('xdg-open',fii))
                        if prop==0:
                            # set read to True
                            self.meta_dict[docid]['read']='true'

                            self.logger.debug("New value of meta_dict[docid]['read'] = %s"\
                                    %self.meta_dict[docid]['read'])

                            self.changed_doc_ids.append(docid)

        return


    def checkDocDuplicate(self,docids,domain):

        self.logger.info('docids = %s, domain = %s' %(docids, domain))

        self.doc_table.setVisible(False)

        if domain=='folder':
            current_folder=self._current_folder
            docids1=self._current_docids
        elif domain=='lib':
            current_folder=('All', '-1')
            docids1=list(self.meta_dict.keys())

        self.duplicate_result_frame.clear_duplicate_label.setText(
                'Checking duplicates in folder "%s".' %current_folder[0])

        self.duplicate_result_frame.checkDuplicates(self.meta_dict,
                current_folder, docids1, docids)

        return

