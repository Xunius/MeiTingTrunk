from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.QtGui import QCursor, QBrush, QColor, QIcon
from lib import sqlitedb

def addFolder(parent,folderid,folder_dict):

    foldername,parentid=folder_dict[folderid]
    fitem=QtWidgets.QTreeWidgetItem([foldername,str(folderid)])
    style=QtWidgets.QApplication.style()
    diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
    fitem.setIcon(0,diropen_icon)
    sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
    if parentid=='-1':
        parent.addTopLevelItem(fitem)
    else:
        parent.addChild(fitem)
    if len(sub_ids)>0:
        for sii in sub_ids:
            addFolder(fitem,sii,folder_dict)

    return

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
                rename_action.setIcon(QIcon.fromTheme('edit-select-all'))
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

                print('# <libTreeMenu>: action.text()=%s' %action.text())
                self.logger.info('action.text()=%s' %action.text())

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
    def changeFolderParent(self,move_folder_id,new_parent_id):

        folder_name=self.folder_dict[move_folder_id][0]

        #------------------Restoring docs------------------
        print('# <changeFolderParent>: move_folder id=',move_folder_id)
        print('# <changeFolderParent>: trashed_folders=',self._trashed_folder_ids)
        trashed_folder_ids=self._trashed_folder_ids
        if move_folder_id in trashed_folder_ids and new_parent_id \
                not in trashed_folder_ids:
            for docid in self.folder_data[move_folder_id]:
                print('# <changeFolderParent>: restoring docii=',docid)
                self.meta_dict[docid]['deletionPending']=='false'
                self.changed_doc_ids.append(docid)

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

        return



    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem,bool)
    def trashFolder(self,item,newparent=None,ask=True):

        if newparent is not None:
            if newparent.data(1,0) in self._trashed_folder_ids+['-3']:
                ask=False

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Deleting a folder will delete all sub-folders and documents inside.\n\nConfirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)


        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):

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

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
            'Deleting folder(s) and document within permanently?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice==QtWidgets.QMessageBox.No:
            return

        foldername=item.data(0,0)
        folderid=item.data(1,0)
        item_parent=item.parent()
        print('# <delFolderFromTrash>: current_folder',foldername,folderid)

        # Not sure, may need to stop the timer
        self.auto_save_timer.stop()

        #-------------------Empty trash-------------------
        if folderid=='-3':
            changed_folders=self._trashed_folder_ids

            #-----------------Get orphan docs in Trash-----------------
            for docii in self.folder_data['-3']:
                print('# <delFolderFromTrash>: orphan doc=',docii)
                #self.meta_dict[docii]={}
                del self.meta_dict[docii]
                self.folder_data['-3'].remove(docii)
                self.changed_doc_ids.append(docii)

        #-------------------Empty folders in trash-------------------
        else:
            changed_folders, _=sqlitedb.walkFolderTree(self.folder_dict,
                    self.folder_data, folderid)

        for fii in changed_folders:
            print('# <delFolderFromTrash>: trashed_folder=',fii)
            #self.changed_doc_ids.extend(self.folder_data[fii])
            self.destroyDoc(self.folder_data[fii], fii, False, False)

        # del folders after all docs are destroyed
        for fii in changed_folders:
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
        print('# <delFolderFromTrash>: Restart auto save timer.')

        return


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


