from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.QtGui import QCursor, QBrush, QColor, QIcon
from lib import sqlitedb


class MainFrameLibTreeSlots:

    #######################################################################
    #                            Libtree slots                            #
    #######################################################################



    def clickSelFolder(self,item,column):
        '''Select folder by clicking'''
        folder=item.data(0,0)
        folderid=item.data(1,0)

        print('# <clickSelFolder>: Select folder %s. folderid=%s' \
                %(folder, folderid))
        self.logger.info('Select folder %s. folderid=%s' \
                %(folder, folderid))

        if item==self.all_folder:
            self.loadDocTable(folder=None,sortidx=4,sel_row=0)
        else:
            self.loadDocTable((folder,folderid),sortidx=4,sel_row=0)

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
            #self.create_subfolder_action.setDisabled(True)
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
        self.filterTypeCombboxChange(item)

        return


    def selFolder(self,selected,deselected):
        '''Select folder by changing current'''

        item=self._current_folder_item
        if item:
            column=0
            print('# <selFolder>: Selected item.data(0,0)=%s, item.data(1,0)=%s' \
                    %(item.data(0,0), item.data(1,0)))
            self.logger.info('Selected item.data(0,0)=%s, item.data(1,0)=%s' \
                    %(item.data(0,0), item.data(1,0)))

            self.clickSelFolder(item,column)


    def libTreeMenu(self,pos):

        item=self._current_folder_item
        folderid=item.data(1,0)

        if item:
            if item==self.trash_folder or folderid in self._trashed_folder_ids:
                menu=QtWidgets.QMenu()
                restore_action=menu.addAction('Restore Folder(s)')
                clear_action=menu.addAction('Delete From Trash')
                menu_type='trash'
            else:
                menu=QtWidgets.QMenu()
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
                rename_action.setIcon(QIcon.fromTheme('edit-select-all'))
                rename_action.setShortcut('R')

                menu_type='default'

            if menu_type=='trash':
                restore_action.setEnabled(True)
                clear_action.setEnabled(True)
            else:
                if item in [self.all_folder, self.needsreview_folder]:
                    add_action.setDisabled(True)
                    addsub_action.setDisabled(True)
                    del_action.setDisabled(True)
                    rename_action.setDisabled(True)
                else:
                    add_action.setEnabled(True)
                    addsub_action.setEnabled(True)
                    del_action.setEnabled(True)
                    rename_action.setEnabled(True)

            action=menu.exec_(QCursor.pos())

            if action:

                print('# <libTreeMenu>: action.text()=%s' %action.text())
                self.logger.info('action.text()=%s' %action.text())

                if menu_type=='trash':
                    if action==restore_action:
                        self.restoreFromTrash()
                    elif action==clear_action:
                        self.delFromTrash()
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
    def changeFolderParent(self,move_folder_id,new_parent_id):

        folder_name=self.folder_dict[move_folder_id][0]

        #------------------Restoring docs------------------
        print('# <changeFolderParent>: move_folder id=',move_folder_id)
        print('# <changeFolderParent>: trashed_folders=',self._trashed_folder_ids)
        if move_folder_id in self._trashed_folder_ids:
            for docid in self.folder_data[move_folder_id]:
                print('# <changeFolderParent>: restoring docii=',docid)
                if self.meta_dict[docid]['deletionPending']=='true':
                    self.meta_dict[docid]['deletionPending']=='false'

        print('# <changeFolderParent>: folder_dict[id] before change=%s'\
                %str(self.folder_dict[move_folder_id]))
        self.logger.info('folder_dict[id] before change=%s'\
                %str(self.folder_dict[move_folder_id]))

        self.folder_dict[move_folder_id]=(folder_name, new_parent_id)

        print('# <changeFolderParent>: folder_dict[id] after change=%s'\
                %str(self.folder_dict[move_folder_id]))
        self.logger.info('folder_dict[id] after change=%s'\
                %str(self.folder_dict[move_folder_id]))

        self.changed_folder_ids.append(move_folder_id)

        #sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                #self.settings.value('saving/storage_folder'))


        return



    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem,bool)
    def trashFolder(self,item,newparent=None,ask=True):

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Deleting a folder will delete all sub-folders and documents inside.\n\nConfirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)


        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):

            #self.libtree._trashed_folder_ids.append(item.data(1,0))
            #print('# <trashFolder>: Add folder id to _trashed_folders. _trashed_folders=%s' %self.libtree._trashed_folder_ids)
            #self.logger.info('Add folder id to _trashed_folders. _trashed_folders=%s' %self.libtree._trashed_folder_ids)

            root=self.libtree.invisibleRootItem()
            (item.parent() or root).removeChild(item)

            folderid=item.data(1,0)
            if newparent is None:
                self.trash_folder.addChild(item)
                self.changeFolderParent(folderid,'-3')
            else:
                newparent.addChild(item)
                self.changeFolderParent(folderid,newparent.data(1,0))

            self.postTrashFolder(item)

        return




    def postTrashFolder(self,item):

        folderid=item.data(1,0)


        delfolderids,deldocids=sqlitedb.walkFolderTree(self.folder_dict,
                self.folder_data,folderid)

        orphan_docs=sqlitedb.findOrphanDocs(self.folder_data,deldocids,
                self._trashed_folder_ids)

        print('# <postTrashFolder>: delfolderids=%s' %delfolderids)
        self.logger.info('delfolderids=%s' %delfolderids)

        print('# <postTrashFolder>: Docs to del=%s' %deldocids)
        self.logger.info('Docs to del=%s' %deldocids)

        print('# <postTrashFolder>: Orphan docs=%s' %orphan_docs)
        self.logger.info('Orphan docs=%s' %orphan_docs)

        #self._orphan_doc_ids.extend(orphan_docs)

        for idii in orphan_docs:
            self.meta_dict[idii]['deletionPending']='true'

            print('# <postTrashFolder>: Set deletionPending to orphan doc %s %s' \
                    %(idii, self.meta_dict[idii]['deletionPending']))
            self.logger.info('Set deletionPending to orphan doc %s %s' \
                    %(idii, self.meta_dict[idii]['deletionPending']))

        self.changed_doc_ids.extend(orphan_docs)

        for fii in delfolderids:
            #print('del folder',fii,self.folder_dict[fii])
            #del self.folder_data[fii]
            #del self.folder_dict[fii]
            pass
            #print(fii,'in folder_data?',fii in self.folder_data)
            #print(fii,'in folder_dict?',fii in self.folder_dict)

        return




    def restoreFromTrash(self):
        msg=QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Restore')
        msg.setText('Not implemented yet.')
        msg.setInformativeText('You can drag/drop trashed folders/documents to restore them.')
        msg.exec_()

        return

    def delFromTrash(self):

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
            'Deleting folder(s) and document within permanently?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice==QtWidgets.QMessageBox.No:
            return

        foldername,folderid=self._current_folder
        print('# <delFromTrash>: current_folder',foldername,folderid)

        #-------------------Empty trash-------------------
        if folderid=='-3':
            #-----------------Get orphan docs-----------------
            for docii in self.folder_data['-3']:
                print('# <delFromTrash>: orphan doc=',docii)

            for fii in self._trashed_folder_ids:
                print('# <delFromTrash>: trashed_folder=',fii)
                for docii in self.folder_data[fii]:
                    print('# <delFromTrash>: doc in trashed folder=',docii)

        else:
            for fii in self._trashed_folder_ids:
                if fii==folderid:
                    print('# <delFromTrash>: trashed_folder=',fii)
                    for docii in self.folder_data[fii]:
                        print('# <delFromTrash>: doc in trashed folder=',docii)






    def renameFolder(self):

        item=self._current_folder_item
        if item:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.libtree.scrollToItem(item)
            self.libtree.editItem(item)


    def removeFolderHighlights(self):

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
        ori_color=QBrush(QColor(255,255,255))
        root=self.libtree.invisibleRootItem()
        for item in iterItems(self.libtree, root):
            item.setBackground(0, ori_color)

        return


