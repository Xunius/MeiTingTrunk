'''
MeiTing Trunk

An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.


Slots involving folder changes, including creation, re-parenting, renaming,
trashing, and restoring from trash.
'''

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QStyle
from PyQt5.QtGui import QCursor, QBrush, QColor, QIcon
from .lib import sqlitedb
from .lib.tools import iterTreeWidgetItems



class MainFrameLibTreeSlots:

    #######################################################################
    #                            Libtree slots                            #
    #######################################################################


    def clickSelFolder(self, item, column):
        """Change button states and load doc table on selecting a folder

        Args:
            item (QTreeWidgetItem): selected item in folder tree.
            column (int): column index in folder tree.
        """

        folder=item.data(0,0)
        folderid=item.data(1,0)

        # NOTE that this hiding is necessary, although it is called via
        # filterTypeCombboxChange() -> clearFilterButtonClicked().
        # Because in that case, the loadDocTable() will be called twice,
        # if the clear_filter_frame was visible before this clickSelFolder()
        # call. If I remove loadDocTable() and leave it in the
        # clearFilterButtonClicked(), it would be less transparent.
        if self.clear_filter_frame.isVisible():
            self.clear_filter_frame.setVisible(False)

        self.logger.info('Selected folder = %s. folderid = %s' \
                %(folder, folderid))

        if item==self.all_folder:
            self.loadDocTable(folder=None,sortidx=None,sel_row=0)
        else:
            self.loadDocTable((folder,folderid),sortidx=None,sel_row=0)

        if item==self.all_folder:
            self.add_button.setDisabled(True)
            self.create_subfolder_action.setDisabled(True)
            self.create_folder_action.setEnabled(True)
            self.add_folder_button.setEnabled(True)
            self.duplicate_check_button.setEnabled(True)
            self.search_button.setEnabled(True)
        elif item==self.needsreview_folder:
            self.add_button.setDisabled(True)
            self.add_folder_button.setDisabled(True)
            self.search_button.setEnabled(True)
        elif item==self.trash_folder:
            self.add_button.setDisabled(True)
            self.add_folder_button.setDisabled(True)
            self.search_button.setEnabled(True)
        else:
            if folderid in self._trashed_folder_ids:
                self.add_button.setDisabled(True)
                self.add_folder_button.setDisabled(True)
                self.create_subfolder_action.setDisabled(True)
                self.search_button.setEnabled(True)
            else:
                self.add_button.setEnabled(True)
                self.add_folder_button.setEnabled(True)
                self.create_subfolder_action.setEnabled(True)
                self.duplicate_check_button.setEnabled(True)
                self.search_button.setEnabled(True)

        # Refresh filter list
        self.filterTypeCombboxChange()

        return


    @pyqtSlot()
    def selFolder(self):
        '''Select folder by changing current

        This is the slot to libtree.selectionModel().selectionChanged signal.
        '''

        item=self._current_folder_item
        if item:
            self.clickSelFolder(item,0)

        return


    def libTreeMenu(self,pos):
        '''Right click menu in folder tree'''

        item=self._current_folder_item
        folderid=item.data(1,0)

        if item:
            menu=QtWidgets.QMenu()
            if item==self.trash_folder or folderid in self._trashed_folder_ids:
                menu_type='trash'
                restore_action=menu.addAction('Restore Folder(s)')
                clear_action=menu.addAction('Delete From Trash')
            else:
                menu_type='default'
                add_action=menu.addAction('&Create Folder')
                add_action.setIcon(self.style().standardIcon(
                    QtWidgets.QStyle.SP_DirOpenIcon))
                add_action.setShortcut('C')

                addsub_action=menu.addAction('Create &Sub Folder')
                addsub_action.setIcon(self.style().standardIcon(
                    QtWidgets.QStyle.SP_DirClosedIcon))
                addsub_action.setShortcut('S')

                del_action=menu.addAction('&Delete Folder')
                del_action.setIcon(self.style().standardIcon(
                    QtWidgets.QStyle.SP_TrashIcon))
                del_action.setShortcut('D')

                rename_action=menu.addAction('&Rename Folder')
                rename_action.setIcon(QIcon.fromTheme('edit-select-all',
                    self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
                rename_action.setShortcut('R')

                if item==self.needsreview_folder:
                    add_action.setEnabled(False)
                    addsub_action.setEnabled(False)
                    del_action.setEnabled(False)
                    rename_action.setEnabled(False)
                elif item==self.all_folder:
                    addsub_action.setEnabled(False)
                    del_action.setEnabled(False)
                    rename_action.setEnabled(False)

            action=menu.exec_(QCursor.pos())

            if action:

                self.logger.info('action.text() = %s' %action.text())

                if menu_type=='trash':
                    if action==restore_action:
                        self.restoreFolderFromTrash()
                    elif action==clear_action:
                        self.delFolderFromTrash(item)
                else:
                    if action==add_action:
                        self.addFolderButtonClicked(add_action)
                    elif action==addsub_action:
                        self.addFolderButtonClicked(addsub_action)
                    elif action==del_action:
                        self.trashFolder(item,None,True)
                    elif action==rename_action:
                        self.renameFolder()

        return


    @pyqtSlot(str,str)
    def changeFolderParent(self, move_folder_id, new_parent_id):
        """Change the parent of a folder

        Args:
            move_folder_id (str): id of changed folder.
            new_parent_id (str): id of new parent folder.

        This is the slot to libree.folder_move_signal signal, which is emitted
        on re-parenting by drag/drop. See lib/widgets/folder_tree.py.

        It is also called when trashing a folder, see trashFolder().
        """

        folder_name=self.folder_dict[move_folder_id][0]

        #------------------Restoring docs------------------
        trashed_folder_ids=self._trashed_folder_ids
        if move_folder_id in trashed_folder_ids and new_parent_id \
                not in trashed_folder_ids:
            self.logger.info('Moving folder (id = %s) out from Trash. Restoring docs within.'\
                    %move_folder_id)
            for docid in self.folder_data[move_folder_id]:
                self.meta_dict[docid]['deletionPending']=='false'
                self.changed_doc_ids.append(docid)

                self.logger.debug("Restoring doc %d. meta_dict[docid]['deletionPending'] = %s"\
                        %(docid, self.meta_dict[docid]['deletionPending']))

        self.folder_dict[move_folder_id]=(folder_name, new_parent_id)

        self.logger.debug('folder_dict[move_folder_id] = %s'\
                %str(self.folder_dict[move_folder_id]))

        self.changed_folder_ids.append(move_folder_id)

        return


    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem,bool)
    def trashFolder(self, item, newparent=None, ask=True):
        """Send a folder into Trash

        Args:
            item (QTreeWidgetItem): item of the folder to trash.

        Kwargs:
            newparent (QTreeWidgetItem or None): if QTreeWidgetItem, the new
                parent item onto which to add <item>. This happens when
                dragging a folder onto a folder already in Trash, or onto Trash
                itself.  Then this function acts as the slot to
                libtree.folder_del_signal emitted in libtree.dropEvent(), see
                lib/widgets/folder_tree.py

                If None, send the folder to Trash, this happens when trashing
                a folder from the right click menu, see libTreeMenu().
            ask (bool): whether to prompt for confirmation. Default to True.
                It gets overwritten to False if it's moving folders within
                the Trash.
        """

        folderid=item.data(1,0)
        do_post_trash=True

        #--------------Trashing by drag/drop--------------
        if newparent is not None:

            if folderid in self._trashed_folder_ids+['-3']:
                # move within Trash
                self.logger.debug('newparent id %s, folderid %s both in _trashed_folder_ids. Skip postTrashFolder()'\
                        %(newparent.data(1,0), folderid))
                ask=False
                do_post_trash=False

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Deleting a folder will delete all sub-folders and documents inside.\n\nConfirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):

            root=self.libtree.invisibleRootItem()
            (item.parent() or root).removeChild(item)

            if newparent is None:
                self.logger.info('Send folder %s to Trash' %folderid)
                self.trash_folder.addChild(item)
                self.changeFolderParent(folderid,'-3')
            else:
                self.logger.info('Put folder %s to trashed folder %s'\
                        %(folderid, newparent.data(1,0)))
                newparent.addChild(item)
                self.changeFolderParent(folderid,newparent.data(1,0))

            if do_post_trash:
                self.postTrashFolder(item)

        return


    def postTrashFolder(self, item):
        """Update orphan doc records after folder trashing

        Args:
            item (QTreeWidgetItem): item of folder been trashed.
        """

        folderid=item.data(1,0)

        # get subfolders and docs in trashed folder and subfolders
        delfolderids,deldocids=sqlitedb.walkFolderTree(self.folder_dict,
                self.folder_data,folderid)
        # find orphan docs within
        orphan_docs=sqlitedb.findOrphanDocs(self.folder_data,deldocids,
                self._trashed_folder_ids)

        self.logger.debug('Ids of folders to trash = %s' %delfolderids)
        self.logger.debug('Ids of docs within = %s' %deldocids)
        self.logger.info('Orphan docs = %s' %orphan_docs)

        for idii in orphan_docs:
            self.meta_dict[idii]['deletionPending']='true'
            self.logger.debug('Set deletionPending to orphan doc %s %s' \
                    %(idii, self.meta_dict[idii]['deletionPending']))

        self.changed_doc_ids.extend(orphan_docs)

        return


    def restoreFolderFromTrash(self):

        msg=QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Restore')
        msg.setText('Not implemented yet.')
        msg.setInformativeText('You can drag/drop trashed folders/documents to restore them.')
        msg.exec_()

        return


    def delFolderFromTrash(self, item):
        """Delete a trashed folder

        Args:
            item (QTreeWidgetItem): item of folder to be deleted
        """

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
            'Deleting folder(s) and document within permanently?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice==QtWidgets.QMessageBox.No:
            return

        foldername=item.data(0,0)
        folderid=item.data(1,0)
        item_parent=item.parent()

        self.logger.info('current folder name = %s. folder id = %s.' \
                %(foldername, folderid))

        # Not sure, may need to stop the timer
        self.auto_save_timer.stop()
        self.logger.info('Stoped auto save timer.')

        #-------------------Empty trash-------------------
        if folderid=='-3':
            changed_folders=self._trashed_folder_ids

            #-----------------Get orphan docs in Trash-----------------
            for docii in self.folder_data['-3']:

                self.logger.warning('Deleting orphan doc %s from meta_dict' %docii)
                del self.meta_dict[docii]
                self.logger.warning('Deleting orphan doc %s from folder_data[-3]' %docii)
                self.folder_data['-3'].remove(docii)
                self.changed_doc_ids.append(docii)

        #-------------------Empty folders in trash-------------------
        else:
            changed_folders, _=sqlitedb.walkFolderTree(self.folder_dict,
                    self.folder_data, folderid)

        self.logger.info('Ids of folders to clear from trash = %s' %changed_folders)

        #-------------Destroy docs in folders-------------
        for fii in changed_folders:
            self.logger.info('Destroying docs in folder %s' %fii)
            self.destroyDoc(self.folder_data[fii], fii, False, False)

        #-----Del folders after all docs are destroyed-----
        for fii in changed_folders:
            self.logger.warning('Deleting folder %s from folder_dict, folder_data' %fii)
            del self.folder_dict[fii]
            del self.folder_data[fii]

            itemii=self.libtree.findItems(fii, Qt.MatchExactly | Qt.MatchRecursive,
                    column=1)
            if len(itemii)>0:
                itemii=itemii[0]
                itemii.parent().removeChild(itemii)

        self.changed_folder_ids.extend(changed_folders)

        self.libtree.setCurrentItem(item_parent)

        self.auto_save_timer.start()
        self.logger.info('Restarted auto save timer.')

        return


    def renameFolder(self):

        item=self._current_folder_item
        if item:
            if item in self.sys_folders:
                return
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.libtree.scrollToItem(item)
            self.libtree.editItem(item)

        return


    def removeFolderHighlights(self):

        ori_color=QBrush(QColor(255,255,255))
        root=self.libtree.invisibleRootItem()
        for item in iterTreeWidgetItems(self.libtree, root):
            item.setBackground(0, ori_color)

        return


