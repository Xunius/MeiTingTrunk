import os
import subprocess
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
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

    def docTableClicked(self):

        print('# <docTableClicked>: Doc clicked. Set to extendedselection.')
        self.logger.info('Doc clicked. Set to extendedselection.')

        self.doc_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # count selected docs
        sel_rows=self.doc_table.selectionModel().selectedRows()
        if len(sel_rows)>1:
            self.status_bar.showMessage('%d rows selected' %len(sel_rows))

        return


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

        print('# <modelDataChanged>: Changed row=%s. Changed docid=%s. meta_dict["favourite"]=%s. meta_dict["read"]=%s. confirmed=%s' \
                %(row, docid, self.meta_dict[docid]['favourite'],\
                self.meta_dict[docid]['read'], self.meta_dict[docid]['confirmed']))
        self.logger.info('Changed row=%s. Changed docid=%s. meta_dict["favourite"]=%s. meta_dict["read"]=%s' \
                %(row, docid, self.meta_dict[docid]['favourite'],\
                self.meta_dict[docid]['read']))

        self.changed_doc_ids.append(docid)

        return


    def selDoc(self,current,previous):
        '''Actions on selecting a document in doc table
        '''
        rowid=current.row()
        docid=self._tabledata[rowid][0]

        print('# <selDoc>: Select rowid=%s. docid=%s' %(rowid, docid))
        self.logger.info('Select rowid=%s. docid=%s' %(rowid, docid))

        self.loadMetaTab(docid)
        self.loadBibTab(docid)
        self.loadNoteTab(docid)

        #-------------------Get folders-------------------
        metaii=self.meta_dict[docid]
        folders=metaii['folders_l']
        folders=[str(fii[0]) for fii in folders]

        print('# <selDoc>: Ids of folders of docid=%s: %s' %(docid, folders))
        self.logger.info('Ids of folders of docid=%s: %s' %(docid, folders))

        def iterItems(treewidget, root):
            if root is not None:
                stack = [root]
                while stack:
                    parent = stack.pop(0)
                    for row in range(parent.childCount()):
                        child = parent.child(row)
                        yield child
                        if child.childCount()>0:
                            stack.append(child)

        #------------Remove highlights for all------------
        self.removeFolderHighlights()
        #ori_color=QBrush(QColor(255,255,255))

        #root=self.libtree.invisibleRootItem()
        # disconnect libtree item change signal
        #self.libtree.itemChanged.disconnect()
        #for item in iterItems(self.libtree, root):
            #item.setBackground(0, ori_color)

        #------------Search folders in libtree------------
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


        # re-connect libtree item change signal
        #self.libtree.itemChanged.connect(self.addNewFolderToDict, Qt.QueuedConnection)




    def docTableMenu(self,pos):

        menu=QtWidgets.QMenu()
        current_folder_item=self._current_folder_item

        open_action=menu.addAction('&Open File Externally')
        open_action.setIcon(QIcon.fromTheme('document-open'))
        open_action.setShortcut('O')

        open_folder_action=menu.addAction('Open Containing &Folder')
        #open_folder_action.setIcon(QIcon.fromTheme('system-file-manager'))
        open_folder_action.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_DirIcon))
        open_folder_action.setShortcut('F')

        del_from_folder_action=menu.addAction('&Delete From Current Folder')
        del_from_folder_action.setIcon(QIcon.fromTheme('user-trash'))
        del_from_folder_action.setShortcut('D')

        del_from_lib_action=QtWidgets.QAction('Delete From Library',menu)
        del_from_lib_action.setIcon(QIcon.fromTheme('user-trash'))

        del_from_trash_action=QtWidgets.QAction('Delete From Trash',menu)
        del_from_trash_action.setIcon(QIcon.fromTheme('edit-delete'))

        if current_folder_item==self.trash_folder:
            menu.addAction(del_from_trash_action)
        else:
            menu.addAction(del_from_lib_action)

        mark_needsreview_action=menu.addAction('&Mark document as Needs Review')
        mark_needsreview_action.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_MessageBoxInformation))
        mark_needsreview_action.setShortcut('M')

        check_duplicate_folder_action=menu.addAction('Check Du&plicates Within Folder')
        check_duplicate_folder_action.setIcon(QIcon.fromTheme('edit-find'))
        check_duplicate_folder_action.setShortcut('P')

        check_duplicate_lib_action=menu.addAction('Check Duplicates Within Library')
        check_duplicate_lib_action.setIcon(QIcon.fromTheme('edit-find'))

        menu.addSeparator()
        #export_menu=menu.addMenu('Export Citation')
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

        print('# <docTableMenu>: Seleted rows=%s' %sel_rows)
        self.logger.info('Seleted rows=%s' %sel_rows)

        if len(sel_rows)>0:

            docids=[self._tabledata[ii][0] for ii in sel_rows]
            has_files=[self.meta_dict[docii]['has_file'] for docii in docids]

            print('# <docTableMenu>: Selected docids=%s. has_files=%s'\
                    %(docids, has_files))
            self.logger.info('Selected docids=%s. has_files=%s'\
                    %(docids, has_files))

            if any(has_files):
                open_action.setEnabled(True)
                open_folder_action.setEnabled(True)
            else:
                open_action.setDisabled(True)
                open_folder_action.setDisabled(True)


            if current_folder_item in self.sys_folders:
                del_from_folder_action.setDisabled(True)
            else:
                del_from_folder_action.setEnabled(True)

            if current_folder_item==self.needsreview_folder:
                mark_needsreview_action.setDisabled(True)
            else:
                mark_needsreview_action.setEnabled(True)



            action=menu.exec_(QCursor.pos())

            if action:
                print('# <docTableMenu>: action.text()=%s' %action.text())
                self.logger.info('action.text()=%s' %action.text())

                if action==open_action:
                    open_docs=[docids[ii] for ii in range(len(docids)) if has_files[ii]]

                    print('# <docTableMenu>: Open docs: %s' %open_docs)
                    self.logger.info('Open docs: %s' %open_docs)

                    self.openDoc(open_docs)

                elif action==open_folder_action:
                    open_docs=[docids[ii] for ii in range(len(docids)) if has_files[ii]]

                    print('# <docTableMenu>: Open docs in file mananger: %s' %open_docs)
                    self.logger.info('Open docs in file mananger: %s' %open_docs)

                    self.openDocFolder(open_docs)

                elif action==del_from_folder_action:
                    foldername,folderid=self._current_folder
                    self.delFromFolder(docids, foldername, folderid, True)

                elif action==del_from_lib_action:
                    self.delDoc(docids,True)

                elif action==del_from_trash_action:
                    self.destroyDoc(docids,True)

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

        print('# <openDoc>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file

            if not os.path.exists(file_pathii):
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText("Can't find file.")
                msg.setInformativeText("No such file: %s. Please re-attach the document file." %file_pathii)
                msg.exec_()
                return

            print('# <openDoc>: docid=%s. file_path=%s' %(docii, file_pathii))
            self.logger.info('docid=%s. file_path=%s' %(docii, file_pathii))

            # what if file is not found?
            prop=subprocess.call(('xdg-open', file_pathii))
            print('# <openDoc>: prop=',prop)

            if prop==0:
                # set read to True
                print('# <openDoc>: read=',self.meta_dict[docii]['read'])
                self.meta_dict[docii]['read']='true'
                print('# <openDoc>: after read=',self.meta_dict[docii]['read'])

                self.changed_doc_ids.append(docii)

        # refresh to show read change
        self.loadDocTable(folder=self._current_folder,sortidx=4,
                sel_row=None)

        return

    def openDocFolder(self,docids):

        print('# <openDocFolder>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        #------------Get default file mananger------------
        prop=subprocess.Popen(['xdg-mime','query','default','inode/directory'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        file_man=prop.communicate()[0].decode('ascii').strip().replace('.desktop','')

        #----------------Open file manager----------------
        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file

            print('# <openDocFolder>: docid=%s. file_path=%s' %(docii, file_pathii))
            self.logger.info('docid=%s. file_path=%s' %(docii, file_pathii))

            # what if file is not found?
            prop=subprocess.call((file_man, file_pathii))

        return



    def delFromFolder(self,docids,foldername,folderid,reload_table):

        print('# <delFromFolder>: docids=%s. foldername=%s. folderid=%s'\
                %(docids, foldername, folderid))
        self.logger.info('docids=%s. foldername=%s. folderid=%s'\
                %(docids, foldername, folderid))

        # remove doc from folder
        for idii in docids:
            self.folder_data[folderid].remove(idii)
            print('####',self.meta_dict[idii]['folders_l'])
            # remove folder from doc
            if (int(folderid),foldername) in self.meta_dict[idii]['folders_l']:
                self.meta_dict[idii]['folders_l'].remove((int(folderid),foldername))
                self.changed_doc_ids.append(idii)

        # check orphan
        orphan_docs=sqlitedb.findOrphanDocs(self.folder_data,docids,
                self._trashed_folder_ids)
        #self._orphan_doc_ids.extend(orphan_docs)

        for idii in orphan_docs:
            self.meta_dict[idii]['deletionPending']='true'
            self.folder_data['-3'].append(idii)
            self.changed_doc_ids.append(idii)

        if reload_table:
            self.loadDocTable(folder=(foldername,folderid),sel_row=None)


        return


    def delDoc(self,docids,reload_table):

        print('# <delDoc>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Confirm deleting a document from library?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice==QtWidgets.QMessageBox.Yes:

            for idii in docids:
                # remove from all folders
                for kk,vv in self.folder_data.items():
                    if idii in vv:
                        vv.remove(idii)

                        print('# <delDoc>: docid %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))
                        self.logger.info('docid %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))

                #del self.meta_dict[idii]
                self.meta_dict[idii]['folders_l']=[]

                #print('# <delDoc>: docid %s in meta_dict?: %s'\
                        #%(idii, idii in self.meta_dict))
                #self.logger.info('docid %s in meta_dict?: %s'\
                        #%(idii, idii in self.meta_dict))

                #if idii not in self._orphan_doc_ids:
                    #self._orphan_doc_ids.append(idii)

                self.folder_data['-3'].append(idii)
                self.meta_dict[idii]['deletionPending']='true'

                #print('# <delDoc>: docid %s in _trashed_doc_ids?: %s'\
                        #%(idii, idii in self.libtree._trashed_doc_ids))
                #self.logger.info('docid %s in _trashed_doc_ids?: %s'\
                        #%(idii, idii in self.libtree._trashed_doc_ids))
                self.changed_doc_ids.append(idii)

            if reload_table:
                self.loadDocTable(folder=self._current_folder,sel_row=None)


        return


    def markDocNeedsReview(self,docids):
        print('# <markDocNeedsReview>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        for idii in docids:
            self.meta_dict[idii]['confirmed']='false'
            if idii not in self.folder_data['-2']:
                self.folder_data['-2'].append(idii)
            self.changed_doc_ids.append(idii)

        row=self.doc_table.currentIndex().row()
        self.loadDocTable(folder=self._current_folder,sortidx=4,
                sel_row=row)

        return

    def destroyDoc(self,docids,reload_table):

        print('# <destroyDoc>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Confirm deleting a document permanently?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice==QtWidgets.QMessageBox.Yes:

            for idii in docids:
                # remove from all folders
                for kk,vv in self.folder_data.items():
                    if idii in vv:
                        vv.remove(idii)

                        print('# <destroyDoc>: docid %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))
                        self.logger.info('docid %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))

                #del self.meta_dict[idii]

                # NOTE: need to del this from sqlite
                self.changed_doc_ids.append(idii)
                self.meta_dict[idii]={}
                #self.meta_dict[idii]['folders_l']=[]

                #print('# <destroyDoc>: docid %s in meta_dict?: %s'\
                        #%(idii, idii in self.meta_dict))
                #self.logger.info('docid %s in meta_dict?: %s'\
                        #%(idii, idii in self.meta_dict))

                #if idii not in self._orphan_doc_ids:
                    #self._orphan_doc_ids.append(idii)

                #self.folder_data['-3'].append(idii)
                #self.meta_dict[idii]['deletionPending']='true'

                #print('# <destroyDoc>: docid %s in _trashed_doc_ids?: %s'\
                        #%(idii, idii in self.libtree._trashed_doc_ids))
                #self.logger.info('docid %s in _trashed_doc_ids?: %s'\
                        #%(idii, idii in self.libtree._trashed_doc_ids))

            if reload_table:
                self.loadDocTable(folder=self._current_folder,sel_row=None)


        return

    def exportToBib(self,docids,meta_dict):

        print('# <exportToBib>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        if len(docids)==1:
            default_path='%s.bib' %(meta_dict[docids[0]]['citationkey'])
        else:
            default_path='./bibtex.bib'

        print('# <exportToBib>: Default export path=%s' %default_path)
        self.logger.info('Default export path=%s' %default_path)

        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Save Citaitons to bib File',
                default_path,
                "bib Files (*.bib);; All files (*)")[0]

        print('# <exportToBib>: Chosen bib file=%s' %fname)
        self.logger.info('Chosen bib file=%s' %fname)

        def saveBib(results):
            #results=self.master1.results
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
            #self.master1.all_done_signal.connect(saveBib)
            self.master1.run()

        return



    def exportToRIS(self,docids,meta_dict):

        print('# <exportToRIS>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        if len(docids)==1:
            default_path='%s.ris' %(meta_dict[docids[0]]['citationkey'])
        else:
            default_path='./RIS.ris'

        print('# <exportToRIS>: Default export path=%s' %default_path)
        self.logger.info('Default export path=%s' %default_path)

        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Save Citaitons to RIS File',
                default_path,
                "bib Files (*.ris);; All files (*)")[0]

        print('# <exportToRIS>: Chosen ris file=%s' %fname)
        self.logger.info('Chosen ris file=%s' %fname)

        def saveRIS(results):
            #results=self.master1.results
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

        return


    def copyToClipboard(self,docids,style=None):

        cb=QtWidgets.QApplication.clipboard()
        meta={}
        meta_list=[]

        for idii in docids:
            docii=self.meta_dict[idii]

            print('# <copyToClipboard>: docii["authors_l"]=%s' %docii['authors_l'])
            self.logger.info('docii["authors_l"]=%s' %docii['authors_l'])

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

            print('# <copyToClipboard>: metaii=%s', meta)

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



    def docDoubleClicked(self,idx):
        row_idx=idx.row()

        print('# <docDoubleClicked>: Clicked row=%s' %row_idx)
        self.logger.info('Clicked row=%s' %row_idx)

        docid=self._tabledata[row_idx][0]
        files=self.meta_dict[docid]['files_l']
        nfiles=len(files)

        if nfiles==0:
            return
        elif nfiles==1:
            self.openDoc([docid,])
        else:

            print('# <docDoubleClicked>: Selected multiple files.')
            self.logger.info('Selected multiple files.')

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
            for fii in files:
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

            print('# <docDoubleClicked>: return from dialog: %s' %rec)
            self.logger.info('return from dialog: %s' %rec)

            if rec:
                sel_files=listwidget.selectionModel().selectedRows()
                #print('sel_files',sel_files)
                sel_files=[listwidget.item(ii.row()) for ii in sel_files]
                #print('sel_files',sel_files)
                sel_files=[ii.data(0) for ii in sel_files]

                print('# <docDoubleClicked>: Selected files=%s' %sel_files)
                self.logger.info('Selected files=%s' %sel_files)

                if len(sel_files)>0:
                    for fii in sel_files:
                        prop=subprocess.call(('xdg-open',fii))
                        if prop==0:
                            # set read to True
                            print('# <docDoubleClicked>: read=',
                                    self.meta_dict[docid]['read'])
                            self.meta_dict[docid]['read']='true'
                            print('# <docDoubleClicked>: after read=',
                                    self.meta_dict[docid]['read'])

                            self.changed_doc_ids.append(docid)

    def checkDocDuplicate(self,docids2,domain):

        print('# <checkDocDuplicate>: docids=%s, domain=%s' %(docids2, domain))
        self.logger.info('docids=%s, domain=%s' %(docids2, domain))

        self.doc_table.setVisible(False)

        if domain=='folder':
            current_folder=self._current_folder
            docids1=self._current_docids
            print('# <checkDocDuplicate>: docids1=',docids1)
        elif domain=='lib':
            current_folder=('All', '-1')
            docids1=list(self.meta_dict.keys())

        self.duplicate_result_frame.clear_duplicate_label.setText(
                'Checking duplicates in folder "%s".' %current_folder[0])

        self.duplicate_result_frame.checkDuplicates(self.meta_dict,
                current_folder, docids1, docids2)









