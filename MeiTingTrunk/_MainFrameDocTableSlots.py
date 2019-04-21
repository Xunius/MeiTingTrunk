'''
This part contains methods dealing with actions on documents in the doc table,
including selection, right clicking menu, deletion, opening.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import platform
import subprocess
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QModelIndex
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QStyle
from PyQt5.QtGui import QFont, QBrush, QColor, QCursor, QIcon
from .lib import sqlitedb
from .lib import bibparse, risparse
from .lib.tools import parseAuthors
from .lib.widgets import Master, FailDialog


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
    def modelDataChanged(self, index1, index2):
        """Update favourite and read dict data in response to checkbox changes

        Args:
            index1 (QModelIndex): index of changed row
            index2 (QModelIndex): index of changed row?

        This is a slot to doc_table.model().dataChanged signal, emitted when
        the checkboxes for favourite and read columns change state (in response
        to user clicking).
        """

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
    def selDoc(self, current, previous):
        """Select a doc in the doc table

        Args:
            current (QModelIndex): index of current selection
            previous (QModelIndex): index of previous selection

        This is a slot to the doc_table.selectionModel().currentChanged signal.
        """

        rowid=current.row()

        if rowid>=0 and rowid<len(self._tabledata):
            docid=self._tabledata[rowid][0]
            self.logger.info('Selected rowid = %s. docid = %s' %(rowid, docid))

            self.loadMetaTab(docid)
            self.loadBibTab(docid)
            self.loadNoteTab(docid)

            #------------Remove highlights for all folders-------
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


    def docTableMenu(self, pos):
        """Right click menu in the doc table

        Deletion actions differ depending on which folder the current doc is in:

            * in normal folder: "delete from folder" and "delete from library"
                  actions are added.
            * in Needs Review folder: no deletion action added. Docs can only
                  be removed from this folder by confirming
                  their meta data.
            * in All folder: "delete from library" action is added.
            * in Trash folder, or any folder within Trash: "delete from Trash"
                  action is added.

        "Mark as Needs Review" is not added when in Needs Review folder.
        "Open File Externally" and "Open Containing Folder" are disabled when
        none selected docs have any associated file.

        """

        menu=QtWidgets.QMenu()
        current_folderid=self._current_folder_item.data(1,0)
        trashed_folder_ids=self._trashed_folder_ids+['-3']

        open_action=menu.addAction('&Open File Externally')
        open_action.setIcon(QIcon.fromTheme('document-open',
                self.style().standardIcon(QStyle.SP_FileIcon)))
        open_action.setShortcut('O')

        open_folder_action=menu.addAction('Open Containing &Folder')
        open_folder_action.setIcon(QIcon.fromTheme('folder',
                self.style().standardIcon(QStyle.SP_FileDialogStart)))
        open_folder_action.setShortcut('F')

        #-----------------Deletion actions-----------------
        del_from_folder_action=QtWidgets.QAction('&Delete From Current Folder',
                menu)
        del_from_folder_action.setIcon(QIcon.fromTheme('user-trash',
                self.style().standardIcon(QStyle.SP_TrashIcon)))
        del_from_folder_action.setShortcut('D')

        del_from_lib_action=QtWidgets.QAction('Delete From Library',menu)
        del_from_lib_action.setIcon(QIcon.fromTheme('user-trash',
                self.style().standardIcon(QStyle.SP_TrashIcon)))

        del_from_trash_action=QtWidgets.QAction('Delete From Trash',menu)
        del_from_trash_action.setIcon(QIcon.fromTheme('edit-delete',
                self.style().standardIcon(QStyle.SP_TrashIcon)))
        #self.style().standardIcon(QStyle.SP_MessageBoxCritical)))

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
            QStyle.SP_MessageBoxInformation))
        mark_needsreview_action.setShortcut('M')

        if current_folderid!='-2':
            menu.addAction(mark_needsreview_action)

        #--------------Duplicate check action--------------
        check_duplicate_folder_action=menu.addAction('Check Du&plicates Within Folder')
        check_duplicate_folder_action.setIcon(QIcon.fromTheme('edit-find',
                self.style().standardIcon(QStyle.SP_FileDialogContentsView)))
        check_duplicate_folder_action.setShortcut('P')

        check_duplicate_lib_action=menu.addAction('Check Duplicates Within Library')
        check_duplicate_lib_action.setIcon(QIcon.fromTheme('edit-find',
                self.style().standardIcon(QStyle.SP_FileDialogContentsView)))

        #------------------Export actions------------------
        menu.addSeparator()
        export_bib_action=menu.addAction('Export to &bibtex File')
        export_bib_action.setIcon(QIcon.fromTheme('document-save-as',
                self.style().standardIcon(QStyle.SP_DialogSaveButton)))
        export_bib_action.setShortcut('B')

        export_ris_action=menu.addAction('Export to &RIS File')
        export_ris_action.setIcon(QIcon.fromTheme('document-save-as',
                self.style().standardIcon(QStyle.SP_DialogSaveButton)))
        export_ris_action.setShortcut('R')

        copy_clipboard_action=menu.addAction('Export Citation To &Clipboard')
        copy_clipboard_action.setIcon(QIcon.fromTheme('edit-copy',
                self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
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
                    self.delDoc(docids,True,True)

                elif action==del_from_trash_action:
                    self.destroyDoc(docids,current_folderid,True,True)

                elif action==mark_needsreview_action:
                    self.markDocNeedsReview(docids)

                elif action==check_duplicate_folder_action:
                    self.checkDocDuplicate(docids,'folder')

                elif action==check_duplicate_lib_action:
                    self.checkDocDuplicate(docids,'lib')

                elif action==export_bib_action:
                    self.exportToBib(docids)

                elif action==export_ris_action:
                    self.exportToRIS(docids)

                elif action==copy_clipboard_action:
                    self.copyToClipboard(docids,style=None)

        return


    def openDoc(self, docids):
        """Open attached files externally

        Args:
            docids (list): ids of docs to open

        xdg-open is called to open the attached files. If return code of this
        subprocess is 0, set 'read' dict value to 'true'.

        NOTE: need to re-write this for Windows version.
        """

        current_os=platform.system()
        if current_os=='Linux':
            open_command='xdg-open'
        elif current_os=='Darwin':
            open_command='open'
        elif current_os=='Windows':
            raise Exception("Currently only support Linux and Mac.")
        else:
            raise Exception("Currently only support Linux and Mac.")

        self.logger.info('docids = %s' %docids)
        self.logger.info('OS = %s, open command = %s' %(current_os, open_command))
        lib_folder=self.settings.value('saving/current_lib_folder',str)

        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file
            # prepend relative path with folder path
            file_pathii=os.path.join(lib_folder,file_pathii)

            if not os.path.exists(file_pathii):
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText("Can't find file.")
                msg.setInformativeText("No such file: %s. Please re-attach the document file." %file_pathii)
                msg.exec_()
                #return

            self.logger.debug('docid = %s. file_path = %s' %(docii, file_pathii))

            prop=subprocess.call((open_command, file_pathii))
            if prop==0:
                # set read to True
                self.meta_dict[docii]['read']='true'
                self.changed_doc_ids.append(docii)

        # refresh to show read change
        self.loadDocTable(folder=self._current_folder,sortidx=None,
                sel_row=None)

        return


    def openDocFolder(self, docids):
        """Locate the attached files in the file manager

        Args:
            docis (list): ids of docs to locate files

        xdg-mime is used to get the system file manager, which is then launched
        in subprocess.

        NOTE: need to re-write this for Windows verion.
        """

        current_os=platform.system()
        if current_os not in ['Linux', 'Darwin']:
            self.logger.exception('Currently only support Linux and Mac.')
            raise Exception("Currently only support Linux and Mac.")

        self.logger.info('docids = %s' %docids)

        if current_os=='Linux':
            #------------Get default file mananger------------
            prop=subprocess.Popen(['xdg-mime','query','default','inode/directory'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            file_man=prop.communicate()[0].decode('ascii').strip().replace('.desktop','')
            self.logger.info('OS = %s, file_man = %s' %(current_os, file_man))

        elif current_os=='Darwin':
            file_man='open'
            self.logger.info('OS = %s, file_man = %s' %(current_os, file_man))

        #----------------Open file manager----------------
        lib_folder=self.settings.value('saving/current_lib_folder',str)
        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file
            file_pathii=os.path.join(lib_folder,file_pathii)

            self.logger.debug('docid = %s. file_path = %s' %(docii, file_pathii))

            if current_os=='Darwin':
                prop=subprocess.call((file_man, '-R', file_pathii))
            else:
                prop=subprocess.call((file_man, file_pathii))

        return


    @pyqtSlot(list, str, str, bool)
    def delFromFolder(self, docids, foldername, folderid, reload_table):
        """Delete a doc from a folder

        Args:
            docids (list): ids of docs to delete.
            foldername (str): name of folder to delete docs from.
            folderid (str): id of folder to delete docs from.
            reload_table (bool): whether to reload the doc table after deletion.

        This is the implementation of the "Delete From Folder" action in the
        right click menu of doc table. See docTableMenu().

        It is also a slot to the del_doc_from_folder_signal emitted when the
        result frame of duplicate checking is shown and user chooses to delete
        some duplicated docs from the folder.

        Deleted docs become orphan docs if they no longer appear in any other
        normal folder, and will be put to the Trash folder.
        """

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
            #current_row=self.doc_table.currentIndex().row()
            self.loadDocTable(folder=(foldername,folderid),sortidx=None,
                    sel_row=None)
            #self.selDoc(self.doc_table.currentIndex(),None)


        return


    @pyqtSlot(list, bool, bool)
    def delDoc(self, docids, reload_table, ask=True):
        """Delete docs from the library (across all folders)

        Args:
            docids (list): ids of docs to delete.
            reload_table (bool): whether to reload the doc table after deletion.

        This is the implementation of the "Delete From Library" action in the
        right click menu of the doc table. See docTableMenu().

        It is also a slot to the del_doc_from_lib_signal emitted when the
        result frame of duplicate checking is shown and user chooses to delete
        some duplicated docs from all folders.

        Docs are removed from all normal folders, and thus become orphan docs
        and are put to the Trash folder.
        """

        self.logger.info('docids = %s' %docids)

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                    'Confirm deleting a document from library?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if not ask or choice==QtWidgets.QMessageBox.Yes:

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
                #current_row=self.doc_table.currentIndex().row()
                self.loadDocTable(folder=self._current_folder,sortidx=None,
                        sel_row=None)
                #self.selDoc(self.doc_table.currentIndex(),None)

        return


    def markDocNeedsReview(self, docids):
        """Set the confirmed dict value to 'false'

        Args:
            docids (list): ids of docs to change.

        Changed docs are added to the Needs Review folder.
        """

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
        # didn't find a better way to refresh the table view
        self.loadDocTable(folder=self._current_folder,sortidx=None,
                sel_row=row)

        return


    def destroyDoc(self, docids, current_folderid, ask, reload_table):
        """Delete docs from trash

        Args:
            docids (list): ids of docs to delete.
            current_folderid (str): id of current selected folder.
            ask (bool): whether to prompt for confirmation.
            reload_table (bool): whether to reload the doc table afterwards.

        This is the implementation of the "Delete From Trash" action in the
        right click menu of the doc table. See docTableMenu().

        It is also called when deleting folder(s) from Trash, see
        delFolderFromTrash().

        "destroy" means deleting from Trash, and after committing to sqlite,
        becomes permanently gone. Therefore it is only called in actions
        within the Trash context.

        NOTE that if a doc appears in Trash ITSELF, it is by design an
        orphan doc (no longer appearing in any other normal folder). But
        if it appears in a folder somewhere in Trash, it is not necessarily
        an orphan, it may still exists in a normal folder outside of
        Trash. In such cases, it is equivalently an "Delete From Folder" action
        in that it is only removed from the current folder. If it is indeed
        an orphan doc, it will be removed from the in-memory meta dict
        self.meta_dict, from all normal folders (self.folder_data), and
        after committing to sqlite, be permanently deleted.

        """

        self.logger.info('docids = %s' %docids)

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                    'Confirm deleting a document permanently?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):

            if current_folderid=='-3':
                current_foldername='Trash'
            else:
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
                self.loadDocTable(folder=self._current_folder, sortidx=None,
                        sel_row=None)

        return



    def exportToBib(self, docids):
        """Export meta data of docs to bibtex file

        Args:
            docids (list): ids of docs to export.

        Multiple entries are saved to a same bib file.
        Failed jobs will be shown in a pop-up dialog.
        """

        self.logger.info('docids = %s' %docids)

        if len(docids)==1:
            default_path='./%s.bib' %(self.meta_dict[docids[0]]['citationkey'])
        else:
            default_path='./bibtex.bib'
        self.logger.debug('Default export path = %s' %default_path)

        fname = QtWidgets.QFileDialog.getSaveFileName(self,
                'Save Citaitons to bib File',
                default_path,
                "bib Files (*.bib);; All files (*)")[0]
        self.logger.info('Chosen bib file = %s' %fname)

        def saveBib(results):
            '''Collect results and write file'''
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
            # omit some fields
            omit_keys=self.settings.value('export/bib/omit_fields', [], str)
            if isinstance(omit_keys,str) and omit_keys=='':
                omit_keys=[]

            # abs v.s. relative file paths
            path_type=self.settings.value('export/bib/path_type',str)
            if path_type=='absolute':
                prefix=self.settings.value('saving/current_lib_folder',str)
            elif path_type=='relative':
                prefix=''

            job_list=[]
            for ii,docii in enumerate(docids):
                job_list.append((ii,self.meta_dict[docii],omit_keys,prefix))

            # run in separate thread
            self.master1=Master(bibparse.metaDictToBib, job_list,
                    1, self.progressbar,
                    'classic', self.status_bar, 'Exporting to bibtex...',
                    post_process_func=saveBib,
                    close_on_finish=False)
            self.master1.run()

        self.logger.info('Bib file exported.')

        return


    def exportToRIS(self,docids):
        """Export meta data of docs to RIS file

        Args:
            docids (list): ids of docs to export.

        Multiple entries are saved to a same RIS file.
        Failed jobs will be shown in a pop-up dialog.
        """

        self.logger.info('docids = %s' %docids)

        if len(docids)==1:
            default_path='%s.ris' %(self.meta_dict[docids[0]]['citationkey'])
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
            path_type=self.settings.value('export/ris/path_type',str)
            if path_type=='absolute':
                prefix=self.settings.value('saving/current_lib_folder',str)
            elif path_type=='relative':
                prefix=''

            job_list=[]
            for ii,docii in enumerate(docids):
                job_list.append((ii,self.meta_dict[docii],prefix))
            self.master1=Master(risparse.metaDictToRIS, job_list,
                    1, self.progressbar,
                    'classic', self.status_bar, 'Exporting to RIS...',
                    post_process_func=saveRIS,
                    close_on_finish=False)
            self.master1.run()

        self.logger.info('RIS file created.')

        return


    def copyToClipboard(self, docids, style=None):
        """Copy citations of selected docs to system clipboard

        Args:
            docids (list): ids of docs to generate citation.

        Kwargs:
            style (str): citation to style. If None, use a default style

        NOTE: this is only a demo, needs to implememnt some proper style
        formatting. Help needed.
        """

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
    def docDoubleClicked(self, idx):
        """Slot to double clicking in doc table

        Args:
            idx (QModelIndex): index of doc table item been clicked on.

        If the selected doc has only 1 attachment file, call openDoc() on it.
        Otherwise, pop-up a dialog listing all attachments, and let user choose
        which one(s) to open externally. After successful subprocess call,
        set 'read' dict value to 'true'.
        """

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
                fii=os.path.join(lib_folder,fii)
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


    def checkDocDuplicate(self, docids, domain):
        """Search for duplicates with selected doc(s)

        Args:
            docids (list): ids of docs to check.
            domain (str): if 'folder', search within the current folder.
                          if 'lib', search within all folderes.


        """

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
                self.folder_dict,
                current_folder, docids1, docids)

        return

