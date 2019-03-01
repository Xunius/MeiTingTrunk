import os
import subprocess
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer, QPoint, pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor, QFontMetrics,\
        QCursor, QRegExpValidator
from queue import Queue
from lib import sqlitedb
from lib import widgets
from lib import bibparse
#from lib import export2bib
from lib import retrievepdfmeta
from lib.tools import getXExpandYMinSizePolicy, WorkerThread, parseAuthors
import logging




def _addPDF(jobid,abpath):
    try:
        pdfmetaii=retrievepdfmeta.getPDFMeta_pypdf2(abpath)
        pdfmetaii=retrievepdfmeta.prepareMeta(pdfmetaii)
        pdfmetaii['files_l']=[abpath,]
        rec=0
    except:
        pdfmetaii={}
        rec=1
    return rec,jobid,pdfmetaii


def checkFolderName(foldername,folderid,folder_dict):

    logger=logging.getLogger('default_logger')

    toplevelids=[kk for kk,vv in folder_dict.items() if vv[1]=='-1']

    print('# <checkFolderName>: toplevelids=%s. folderid=%s' \
            %(toplevelids, folderid))
    logger.info('toplevelids=%s. folderid=%s' \
            %(toplevelids, folderid))

    if folderid in toplevelids:
        siblings=[folder_dict[ii][0] for ii in toplevelids if ii!=folderid]
    else:
        parentid=folder_dict[folderid][1]
        siblings=[]
        for kk,vv in folder_dict.items():
            if kk!=folderid and vv[1]==parentid:
                siblings.append(vv[0])
        #siblings=[ii[0] for ii in folder_dict.values() if ii[1]==parentid]

    if foldername in siblings:
        print('# <checkFolderName>: foldername in siblings. foldername=%s. siblings=%s' \
                %(foldername, siblings))
        logger.info('foldername in siblings. foldername=%s. siblings=%s' \
                %(foldername, siblings))
        return 1

    return 0





class MainFrameSlots:



    def threadedFuncCall2(self,func,joblist,show_message='',max_threads=4,
            get_results=False,close_on_finish=True):

        thread_run_dialog=widgets.ThreadRunDialog(func,joblist,
                show_message,max_threads,get_results,close_on_finish,self)
        #thread_run_dialog.exec_()
        if get_results:
            #print('# <threadedFuncCall2>: results',thread_run_dialog.results)
            return thread_run_dialog.results
        else:
            return


    def threadedFuncCall(self,func,joblist,res_func=None,show_message=''):
        import time

        def updatePB():
            self.progressbar.setValue(self.progressbar.value()+1)
            print('# <threadedFuncCall>: progress bar value',self.progressbar.value())
            #time.sleep(0.1)
            return

        faillist=[]
        jobqueue=Queue()
        resqueue=Queue()

        #pb=QtWidgets.QProgressBar(self)
        #pb.setSizePolicy(getXExpandYMinSizePolicy())
        #pb.setMaximum(len(joblist))
        #self.status_bar.addPermanentWidget(pb)
        self.status_bar.showMessage(show_message)
        self.progressbar.setMaximum(len(joblist))
        self.progressbar.setValue(0)
        self.progressbar.show()

        for ii,jobii in enumerate(joblist):
            jobqueue.put((jobii,))

        threads=[]
        results=[]
        for ii in range(min(3,len(joblist))):
            tii=WorkerThread(func,jobqueue,resqueue,self)
            #tii.daemon=True
            tii.jobdone_signal.connect(updatePB)
            threads.append(tii)
            tii.start()

        for tii in threads:
            tii.wait()

        #-------------------Get results-------------------
        while resqueue.qsize():
            try:
                resii=resqueue.get()
                if resii[0]==0:
                    results.append(resii[1])
                    if res_func is not None:
                        res_func(resii[1])
                else:
                    faillist.append(resii[2])
            except:
                break



        #self.progressbar.hide()
        self.status_bar.clearMessage()

        return results,faillist




    #######################################################################
    #                      Meta data update functions                      #
    #######################################################################

    def updateTabelData(self,docid,meta_dict,field_list=None):

        if docid is None:

            newid=max(self.meta_dict.keys())+1

            # update folder_data
            foldername,folderid=self._current_folder
            if folderid not in ['-1', '-2', '-3']:
                self.folder_data[folderid].append(newid)

                if (folderid, foldername) not in meta_dict['folders_l']:
                    meta_dict['folders_l'].append((folderid,foldername))
                    print('# <updateTabelData>: Add new doc to folder %s. meta_dict["folders_l"]=%s' %(foldername, meta_dict['folders_l']))
                    self.logger.info('Add new doc to folder %s. meta_dict["folders_l"]=%s' %(foldername, meta_dict['folders_l']))

            # update meta_dict
            print('# <updateTabelData>: Add new doc. Given id=%s' %newid)
            self.logger.info('Add new doc. Given id=%s' %newid)
            docid=newid

            self.meta_dict[newid]=meta_dict
            self.loadDocTable(docids=self._current_docids+[newid,],sel_row=None)
            self.doc_table.scrollToBottom()
            self.doc_table.selectRow(self.doc_table.model().rowCount(None)-1)

        else:
            if docid in self.meta_dict:
                print('# <updateTabelData>: Updating existing doc. docid=%s' %docid)
                self.logger.info('Updating existing doc. docid=%s' %docid)

                for kk in field_list:
                    if kk=='authors_l':
                        self.meta_dict[docid]['firstNames_l']=meta_dict['firstNames_l']
                        self.meta_dict[docid]['lastName_l']=meta_dict['lastName_l']
                    else:
                        self.meta_dict[docid][kk]=meta_dict[kk]
            else:
                print('wtf?')
                self.meta_dict[docid]=meta_dict

            self.loadDocTable(docids=self._current_docids,
                    sel_row=self.doc_table.currentIndex().row())


        #self.saveToDatabase(docid)
        self.changed_doc_ids.append(docid)

        return

    @pyqtSlot(sqlitedb.DocMeta)
    def updateByDOI(self,meta_dict):
        docid=self._current_doc
        print('# <updateByDOI>: Update doc %s' %docid)
        self.logger.info('Update doc %s' %docid)

        if docid:
            self.meta_dict[docid]=meta_dict

            self.loadMetaTab(docid)
        return



    def updateNotes(self,docid,note_text):
        if docid is None:
            return

        self.meta_dict[docid]['notes']=note_text
        print('# <updateNotes>: New notes for docid=%s: %s' %(docid,note_text))
        self.logger.info('New notes for docid=%s: %s' %(docid,note_text))

        self.changed_doc_ids.append(docid)

        return


    @pyqtSlot(int,str)
    def addDocToFolder(self,docid,folderid):

        print('# <addDocToFolder>: docid=%s, folderid=%s' %(docid,folderid))
        self.logger.info('docid=%s, folderid=%s' %(docid,folderid))

        docfolders=self.meta_dict[docid]['folders_l']
        # note folderid here is an int
        newfolder=(int(folderid), self.folder_dict[folderid][0])
        if newfolder not in docfolders:
            docfolders.append(newfolder)
            self.meta_dict[docid]['folders_l']=docfolders

        if docid not in self.folder_data[folderid]:
            self.folder_data[folderid].append(docid)

        print('# <addDocToFolder>: Updated meta_dict["folders_l"]=%s' %self.meta_dict[docid]['folders_l'])
        self.logger.info('Updated meta_dict["folders_l"]=%s' %self.meta_dict[docid]['folders_l'])

        print('# <addDocToFolder>: Updated folder_data=%s' %self.folder_data[folderid],
                type(self.folder_data[folderid][0]))
        self.logger.info('Updated folder_data=%s' %self.folder_data[folderid])

        # add highlight to folder
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        mii=self.libtree.findItems(folderid, Qt.MatchExactly | Qt.MatchRecursive,
                column=1)
        if len(mii)>0:
            for mjj in mii:
                mjj.setBackground(0, hi_color)

        self.changed_doc_ids.append(docid)

        return




    def saveToDatabase(self,docid):

        print('# <saveToDatabase>: Saving folders to database.')
        self.logger.info('Saving folders to database')

        #----------------Save folders first----------------
        sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                self.settings.value('saving/storage_folder'))

        sqlitedb.metaDictToDatabase(self.db,docid,self.meta_dict[docid],
                self.settings.value('saving/storage_folder'),
                self.settings.value('saving/rename_files'))

        if docid in self.changed_doc_ids:
            self.changed_doc_ids.remove(docid)

        return

    def autoSaveToDatabase(self):
        from datetime import datetime
        mtime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        print('# <autoSaveToDatabase>: Auto save called. %s' %mtime)
        self.logger.info('Auto save called. %s' %mtime)

        for ii in self.changed_doc_ids:
            print('# <autoSaveToDatabase>: Save doc %s' %ii)
            self.logger.info('Save doc %s' %ii)

        self.changed_doc_ids=[]
        self.settings.sync()

        return






    #######################################################################
    #                        Tool bar button slots                        #
    #######################################################################
    

    def addPDF(self,jobid,abpath):
        rec,jobid,meta_dict=_addPDF(jobid,abpath)

        if rec==0:
            self.updateTabelData(None,meta_dict)
        return rec,jobid,None


    @pyqtSlot(QtWidgets.QAction)
    def addActionTriggered(self,action):

        action_text=action.text()

        print('# <addActionTriggered>: action.text()=%s' %action_text)
        self.logger.info('action.text()=%s' %action_text)

        if action_text=='Add PDF File':
            fname = QtWidgets.QFileDialog.getOpenFileNames(self, 'Choose a PDF file',
         '',"PDF files (*.pdf);; All files (*)")[0]

            print('# <addActionTriggered>: Chosen PDF file=%s' %fname)
            self.logger.info('Chosen PDF file=%s' %fname)

            if fname:
                self.doc_table.clearSelection()
                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.MultiSelection)

                #results, faillist=self.threadedFuncCall(addPDF,fname,
                        #lambda x:self.updateTabelData(None,x),'Adding PDF Files...')

                joblist=list(zip(range(len(fname)), fname))
                t_dialog=self.threadedFuncCall2(_addPDF, joblist,
                    'Adding PDF Files...',max_threads=1,get_results=True,
                    close_on_finish=True)

                fail_list=[]
                for recii,jobidii,meta_dictii in t_dialog:
                    print('# <addActionTriggered>: rec of t_dialog:',
                            recii,jobidii,meta_dictii)
                    if recii==0:
                        self.updateTabelData(None,meta_dictii)
                    else:
                        fail_list.append(jobidii)

                fail_files=[jii[1] for jii in joblist if jii[0] in fail_list]

                if len(fail_files)>0:

                    for fii in fail_files:
                        metaii=sqlitedb.DocMeta()
                        metaii['files_l']=[fii,]
                        self.updateTabelData(None,metaii)

                    msg=QtWidgets.QMessageBox()
                    msg.resize(500,400)
                    msg.setIcon(QtWidgets.QMessageBox.Information)
                    msg.setWindowTitle('Error')
                    msg.setText('Oopsie.')
                    msg.setInformativeText('Failed to retrieve metadata from these files:\n\n %s'\
                            %('\n'.join(fail_files)))
                    msg.exec_()


                print('# <addActionTriggered>: failist for PDF importing', fail_files)
                #self.logger.info('failist for PDF importing: %s' %faillist)

                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.ExtendedSelection)


        elif action_text=='Add BibTex File':
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a bibtex file',
         '',"Bibtex files (*.bib);; All files (*)")[0]

            print('# <addActionTriggered>: Chosen bib file=%s' %fname)
            self.logger.info('Chosen bib file=%s' %fname)

            if fname:
                try:
                    bib_entries=bibparse.readBibFile(fname)
                    self.doc_table.clearSelection()
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.MultiSelection)
                    for eii in bib_entries:
                        self.updateTabelData(None,eii)
                except Exception as e:
                    print('# <addActionTriggered>: Failed to parse bib file.')
                    self.logger.info('Failed to parse bib file.')

                    msg=QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setWindowTitle('Error')
                    msg.setText('Oopsie. Failed to parse bib file.')
                    msg.setInformativeText('bibtexparser complaints:\n\n%s' %str(e))
                    msg.exec_()
                finally:
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.ExtendedSelection)

        elif action_text=='Add Entry Manually':
            '''
            dialog=widgets.MetaDataEntryDialog(self.settings,self)
            dl_ret,dl_dict=dialog.exec_()

            if dl_ret:
                print('# <addActionTriggered>: Add Entry Manually. Return value=%s' %dl_ret)
                self.logger.info('Add Entry Manually. Return value=%s' %dl_ret)
                self.updateTabelData(None, dl_dict)
            '''
            dummy=sqlitedb.DocMeta()
            self.updateTabelData(None, dummy)

        return


    @pyqtSlot(QtWidgets.QAction)
    def addFolderButtonClicked(self,action):

        print('# <addFolderButtonClicked>: action.text()=%s' %action.text())
        self.logger.info('action.text()=%s' %action.text())

        item=self._current_folder_item
        if item:
            folderid=item.data(1,0)

            # create new item
            current_ids=map(int,self.folder_dict.keys())
            newid=str(max(current_ids)+1)
            newitem=QtWidgets.QTreeWidgetItem(['New folder',str(newid)])
            style=QtWidgets.QApplication.style()
            diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
            newitem.setIcon(0,diropen_icon)
            newitem.setFlags(newitem.flags() | Qt.ItemIsEditable)

            action_text=action.text()

            if action_text=='Create Folder':
                toplevelids=[self.libtree.topLevelItem(jj).data(1,0) for jj\
                        in range(self.libtree.topLevelItemCount())]

                if folderid in toplevelids:
                    self.libtree.addTopLevelItem(newitem)
                    parentid='-1'
                else:
                    item.parent().addChild(newitem)
                    parentid=item.parent().data(1,0)

            elif action_text=='Create Sub Folder':
                item.addChild(newitem)
                parentid=folderid

            self.libtree.scrollToItem(newitem)
            self.libtree.editItem(newitem)
            self.folder_dict[newid]=('New folder',parentid)

            print('# <addFolderButtonClicked>: Folder new id=%s. New entry in folder_dict=%s' %(newid, self.folder_dict[newid]))
            self.logger.info('Folder new id=%s. New entry in folder_dict=%s' %(newid, self))




    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def addNewFolderToDict(self,item,column):

        print('# <addNewFolderToDict>: item', item,'column count',item.columnCount())
        print('# <addNewFolderToDict>: item.data(0,0)=%s. item.data(1,0)=%s'\
                %(item.data(0,0), item.data(1,0)))
        self.logger.info('item.data(0,0)=%s. item.data(1,0)=%s'\
                %(item.data(0,0), item.data(1,0)))

        foldername,folderid=item.data(0,0), item.data(1,0)
        if folderid not in ['-1', '-2', '-3']:
            fnameold,parentid=self.folder_dict[folderid]

            print('# <addNewFolderToDict>: Old folder name=%s. parentid=%s'\
                    %(fnameold, parentid))
            self.logger.info('Old folder name=%s. parentid=%s'\
                    %(fnameold, parentid))

            # add new folder
            if folderid not in self.folder_data:
                self.folder_data[folderid]=[]

            # check validity of new name
            valid=checkFolderName(foldername,folderid,self.folder_dict)
            if valid!=0:

                print('# <addNewFolderToDict>: Found invalid name: %s' %foldername)
                self.logger.info('Found invalid name: %s' %foldername)

                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle('Name conflict')
                msg.setText('Name conflict.')
                msg.setInformativeText('The given name\n\t%s\nconflicts with another folder name.\nPlease choose another name.' %foldername)
                msg.exec_()

                item.setData(0,0,fnameold)
                self.libtree.editItem(item)

                return

            self.folder_dict[folderid]=[foldername,parentid]
            print('new foldername and parentid =',self.folder_dict[folderid])
            print('# <addNewFolderToDict>: New folder name=%s. parentid=%s'\
                    %(self.folder_dict[folderid][0], self.folder_dict[folderid][1]))
            self.logger.info('New folder name=%s. parentid=%s'\
                    %(self.folder_dict[folderid][0], self.folder_dict[folderid][1]))

        self.sortFolders()
        self.libtree.setCurrentItem(item)

        #sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                #self.settings.value('saving/storage_folder'))

        return

    def sortFolders(self):

        def moveItemToTop(item):
            idx=self.libtree.indexOfTopLevelItem(item)
            item=self.libtree.takeTopLevelItem(idx)
            self.libtree.insertTopLevelItem(0,item)

        self.libtree.sortItems(0,Qt.AscendingOrder)

        # move system folders to back to top
        for itemii in reversed(self.sys_folders):
            moveItemToTop(itemii)

        return


    @pyqtSlot(str,str)
    def changeFolderParent(self,move_folder_id,new_parent_id):

        folder_name=self.folder_dict[move_folder_id][0]

        print('# <changeFolderParent>: folder_dict[id] before change=%s'\
                %str(self.folder_dict[move_folder_id]))
        self.logger.info('folder_dict[id] before change=%s'\
                %str(self.folder_dict[move_folder_id]))

        self.folder_dict[move_folder_id]=(folder_name, new_parent_id)

        print('# <changeFolderParent>: folder_dict[id] after change=%s'\
                %str(self.folder_dict[move_folder_id]))
        self.logger.info('folder_dict[id] after change=%s'\
                %str(self.folder_dict[move_folder_id]))

        #sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                #self.settings.value('saving/storage_folder'))
        return


    @pyqtSlot()
    def checkDuplicateClicked(self):

        print('# <checkDuplicateClicked>: Check duplicate button triggered')
        self.logger.info('Check duplicate button triggered')

        docids=self._current_docids
        self.doc_table.setVisible(False)

        current_folder=self._current_folder[0]
        self.duplicate_result_frame.clear_duplicate_label.setText(
                'Checking duplicates in folder "%s".' %current_folder)

        self.duplicate_result_frame.checkDuplicates(self.meta_dict,
                self._current_folder,
                docids,
                None)
        self.duplicate_result_frame.addResultToTree()
        self.duplicate_result_frame.setVisible(True)

        return

    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem)
    def duplicateResultCurrentChange(self,current,previous):

        if current:
            docid=int(current.data(6,0))

            print('# <duplicateResultCurrentChange>: current=%s' %docid)
            self.logger.info('current=%s' %docid)

            self.loadMetaTab(docid)
            self.loadBibTab(docid)
            self.loadNoteTab(docid)
        return




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
        elif item==self.needsreview_folder:
            self.add_button.setDisabled(True)
            self.add_folder_button.setDisabled(True)
        elif item==self.trash_folder:
            self.add_button.setDisabled(True)
            self.add_folder_button.setDisabled(True)
            #self.create_subfolder_action.setDisabled(True)
        else:
            if folderid in self.libtree._trashed_folder_ids:
                self.add_button.setDisabled(True)
                self.add_folder_button.setDisabled(True)
                self.create_subfolder_action.setDisabled(True)
            else:
                self.add_button.setEnabled(True)
                self.add_folder_button.setEnabled(True)
                self.create_subfolder_action.setEnabled(True)
                self.duplicate_check_button.setEnabled(True)

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
            if item==self.trash_folder or folderid in self.libtree._trashed_folder_ids:
                menu=QtWidgets.QMenu()
                restore_action=menu.addAction('Restore Folder(s)')
                clear_action=menu.addAction('Clear Folder(s) From Trash')
                menu_type='trash'
            else:
                menu=QtWidgets.QMenu()
                add_action=menu.addAction('Create Folder')
                addsub_action=menu.addAction('Create Sub Folder')
                del_action=menu.addAction('Delete Folder')
                rename_action=menu.addAction('Rename Folder')
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
                        pass
                    elif action==clear_action:
                        pass
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



    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem,bool)
    def trashFolder(self,item,newparent=None,ask=True):

        if ask:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Deleting a folder will delete all sub-folders and documents inside.\n\nConfirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)


        if not ask or (ask and choice==QtWidgets.QMessageBox.Yes):

            self.libtree._trashed_folder_ids.append(item.data(1,0))
            print('# <trashFolder>: Add folder id to _trashed_folders. _trashed_folders=%s' %self.libtree._trashed_folder_ids)
            self.logger.info('Add folder id to _trashed_folders. _trashed_folders=%s' %self.libtree._trashed_folder_ids)

            root=self.libtree.invisibleRootItem()
            (item.parent() or root).removeChild(item)

            if newparent is None:
                self.trash_folder.addChild(item)
            else:
                newparent.addChild(item)

            folderid=item.data(1,0)
            self.changeFolderParent(folderid,'-3')
            self.postTrashFolder(item)

        return




    def postTrashFolder(self,item):

        folderid=item.data(1,0)


        delfolderids,deldocids=sqlitedb.walkFolderTree(self.folder_dict,
                self.folder_data,folderid)

        orphan_docs=sqlitedb.findOrphanDocs(self.folder_data,deldocids,
                self.libtree._trashed_folder_ids)

        self.libtree._trashed_doc_ids.extend(orphan_docs)

        print('# <postTrashFolder>: delfolderids=%s' %delfolderids)
        self.logger.info('delfolderids=%s' %delfolderids)

        print('# <postTrashFolder>: Docs to del=%s' %deldocids)
        self.logger.info('Docs to del=%s' %deldocids)

        print('# <postTrashFolder>: Orphan docs=%s' %orphan_docs)
        self.logger.info('Orphan docs=%s' %orphan_docs)

        for idii in orphan_docs:
            self.meta_dict[idii]['pend_delete']=True

            print('# <postTrashFolder>: Set pend_delete to orphan doc %s %s' \
                    %(idii, self.meta_dict[idii]['pend_delete']))
            self.logger.info('Set pend_delete to orphan doc %s %s' \
                    %(idii, self.meta_dict[idii]['pend_delete']))

        for fii in delfolderids:
            #print('del folder',fii,self.folder_dict[fii])
            #del self.folder_data[fii]
            #del self.folder_dict[fii]
            pass
            #print(fii,'in folder_data?',fii in self.folder_data)
            #print(fii,'in folder_dict?',fii in self.folder_dict)

        return





    def renameFolder(self):

        item=self._current_folder_item
        if item:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.libtree.scrollToItem(item)
            self.libtree.editItem(item)




    #######################################################################
    #                          Filter list slots                          #
    #######################################################################
    
    def filterItemClicked(self,item):

        print('# <filterItemClicked>: Clicked item.text()=%s' %item.text())
        self.logger.info('Clicked item.text()=%s' %item.text())

        filter_type=self.filter_type_combbox.currentText()
        filter_text=item.text()
        current_folder=self._current_folder
        if current_folder:
            folderid=current_folder[1]

            filter_docids=sqlitedb.filterDocs(self.meta_dict,self.folder_data,
                    filter_type,filter_text,folderid)

            if len(filter_docids)>0:
                self.loadDocTable(None,filter_docids,sortidx=4,sel_row=0)
                #self.doc_table.selectRow(0)

            sel=self.filter_type_combbox.currentText()

            if sel=='Filter by keywords':
                self.clear_filter_label.setText(
                        'Showing documents with keyword "%s"' %filter_text)
            elif sel=='Filter by authors':
                self.clear_filter_label.setText(
                        'Showing documents authored by "%s"' %filter_text)
            elif sel=='Filter by publications':
                self.clear_filter_label.setText(
                        'Showing documents published in "%s"' %filter_text)
            elif sel=='Filter by tags':
                self.clear_filter_label.setText(
                        'Showing documents tagged "%s"' %filter_text)

            self.clear_filter_frame.setVisible(True)

        return

    def filterTypeCombboxChange(self,item):
        # clear current filtering first
        self.clearFilterButtonClicked()

        sel=self.filter_type_combbox.currentText()
        current_folder=self._current_folder

        print('# <filterTypeCombboxChange>: Filter type combobox select=%s'\
                %sel)
        self.logger.info('Filter type combobox select=%s'\
                %sel)

        if current_folder:

            print('# <filterTypeCombboxChange>: current_folder=%s, folderid_d=%s'\
                    %(current_folder[0], current_folder[1]))
            self.logger.info('current_folder=%s, folderid_d=%s'\
                    %(current_folder[0], current_folder[1]))

            #---------------Get items in folder---------------
            foldername,folderid=current_folder
            if foldername=='All' and folderid=='-1':
                docids=list(self.meta_dict.keys())
            else:
                docids=self.folder_data[folderid]

            if sel=='Filter by keywords':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'keywords_l',docids,
                        unique=True,sort=True)
            elif sel=='Filter by authors':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'authors_l',docids,
                        unique=False,sort=False)
                # why not unique and sort?
            elif sel=='Filter by publications':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'publication',docids,
                        unique=True,sort=True)
            elif sel=='Filter by tags':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'tags_l',docids,
                        unique=True,sort=True)

            folderdata=list(set(folderdata))
            folderdata.sort()
            self.filter_item_list.clear()
            self.filter_item_list.addItems(folderdata)

        return




    #######################################################################
    #                           Doc table slots                           #
    #######################################################################

    def docTableClicked(self):

        print('# <docTableClicked>: Doc clicked. Set to extendedselection.')
        self.logger.info('Doc clicked. Set to extendedselection.')

        self.doc_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

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
        ori_color=QBrush(QColor(255,255,255))
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        root=self.libtree.invisibleRootItem()
        # disconnect libtree item change signal
        #self.libtree.itemChanged.disconnect()
        for item in iterItems(self.libtree, root):
            item.setBackground(0, ori_color)

        #------------Search folders in libtree------------
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
        open_action=menu.addAction('Open File Externally')
        open_folder_action=menu.addAction('Open Containing Folder')
        del_from_folder_action=menu.addAction('Delete From Current Folder')
        del_action=menu.addAction('Delete From Library')
        mark_needsreview_action=menu.addAction('Mark document as Needs Review')
        menu.addSeparator()
        #export_menu=menu.addMenu('Export Citation')
        export_bib_action=menu.addAction('Export bib to File')
        copy_clipboard_action=menu.addAction('Export Citation To Clipboard')

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

            foldername,folderid=self._current_folder
            if self._current_folder_item in self.sys_folders:
                del_from_folder_action.setDisabled(True)
            else:
                del_from_folder_action.setEnabled(True)

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
                    self.delFromFolder(docids, foldername, folderid, True)

                elif action==del_action:
                    self.delDoc(docids,True)

                elif action==mark_needsreview_action:
                    self.markDocNeedsReview(docids)

                elif action==export_bib_action:
                    self.exportToBib(docids)

                elif action==copy_clipboard_action:
                    self.copyToClipboard(docids,style=None)

        return


    def openDoc(self,docids):

        print('# <openDoc>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        for docii in docids:
            file_pathii=self.meta_dict[docii]['files_l'][0] # take the 1st file

            print('# <openDoc>: docid=%s. file_path=%s' %(docii, file_pathii))
            self.logger.info('docid=%s. file_path=%s' %(docii, file_pathii))

            # what if file is not found?
            prop=subprocess.call(('xdg-open', file_pathii))
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

        # check orphan docs
        for idii in docids:
            self.folder_data[folderid].remove(idii)
            print('####',self.meta_dict[idii]['folders_l'])
            if (int(folderid),foldername) in self.meta_dict[idii]['folders_l']:
                self.meta_dict[idii]['folders_l'].remove((int(folderid),foldername))

        orphan_docs=sqlitedb.findOrphanDocs(self.folder_data,docids,
                self.libtree._trashed_folder_ids)
        self.libtree._trashed_doc_ids.extend(orphan_docs)

        if reload_table:
            self.loadDocTable(folder=(foldername,folderid),sel_row=None)

        return


    def delDoc(self,docids,reload_table):

        print('# <delDoc>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Confirm deleting a document permanently?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if choice==QtWidgets.QMessageBox.Yes:

            for idii in docids:
                for kk,vv in self.folder_data.items():
                    if idii in vv:
                        vv.remove(idii)

                        print('# <delDoc>: docid %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))
                        self.logger.info('docid %s in folder_data[%s]?: %s'\
                                %(idii, kk, idii in self.folder_data[kk]))

                del self.meta_dict[idii]

                print('# <delDoc>: docid %s in meta_dict?: %s'\
                        %(idii, idii in self.meta_dict))
                self.logger.info('docid %s in meta_dict?: %s'\
                        %(idii, idii in self.meta_dict))

                if idii in self.libtree._trashed_doc_ids:
                    self.libtree._trashed_doc_ids.remove(idii)

                print('# <delDoc>: docid %s in _trashed_doc_ids?: %s'\
                        %(idii, idii in self.libtree._trashed_doc_ids))
                self.logger.info('docid %s in _trashed_doc_ids?: %s'\
                        %(idii, idii in self.libtree._trashed_doc_ids))

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

        row=self.doc_table.currentIndex().row()
        self.loadDocTable(folder=self._current_folder,sortidx=4,
                sel_row=row)

        return


    def exportToBib(self,docids):

        print('# <exportToBib>: docids=%s' %docids)
        self.logger.info('docids=%s' %docids)

        if len(docids)==1:
            default_path='%s.bib' %(self.meta_dict[docids[0]]['citationkey'])
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

        if fname:
            text=''
            omit_keys=self.settings.value('export/bib/omit_fields', [], str)
            if isinstance(omit_keys,str) and omit_keys=='':
                omit_keys=[]

            for idii in docids:

                print('# <exportToBib>: Parsing bib for docid=%s' %idii)
                self.logger.info('Parsing bib for docid=%s' %idii)
                metaii=self.meta_dict[idii]

                #textii=export2bib.parseMeta(metaii,'',metaii['folders_l'],True,False,
                        #True)
                textii=bibparse.metaDictToBib(metaii,bibparse.INV_ALT_KEYS,
                        omit_keys)
                text=text+textii+'\n'

            with open(fname,'w') as fout:
                fout.write(text)

            print('# <exportToBib>: File saved to %s' %fname)
            self.logger.info('File saved to %s' %fname)

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
                        subprocess.call(('xdg-open',fii))







    #######################################################################
    #                            Meta tab slots                           #
    #######################################################################

    def clearMetaTab(self):
        for kk,vv in self._current_meta_dict.items():
            if kk=='files_l':
                #vv=[]
                self.t_meta.delFileField()
            else:
                vv.clear()
                vv.setReadOnly(True)

        for tii in [self.note_textedit, self.bib_textedit]:
            tii.clear()
            tii.setReadOnly(True)

        return

    def enableMetaTab(self):
        for kk,vv in self._current_meta_dict.items():
            if kk!='files_l':
                vv.setReadOnly(False)

        for tii in [self.note_textedit, ]:
            tii.setReadOnly(False)

        return

    def confirmReviewButtonClicked(self):
        docid=self._current_doc

        print('# <confirmReviewButtonClicked>: Before: self.meta_dict[docid]["confirmed"]', self.meta_dict[docid]['confirmed'])

        self.meta_dict[docid]['confirmed']='true'

        print('# <confirmReviewButtonClicked>: After: self.meta_dict[docid]["confirmed"]', self.meta_dict[docid]['confirmed'])

        self.confirm_review_frame.setVisible(False)
        idx=self.doc_table.currentIndex()
        self.doc_table.model().dataChanged.emit(idx,idx)

        # del doc from needs review folder
        if docid in self.folder_data['-2']:
            self.folder_data['-2'].remove(docid)

        self.loadDocTable(folder=self._current_folder,sortidx=4,sel_row=idx.row())



    #######################################################################
    #                             Other slots                             #
    #######################################################################


    def foldFilterButtonClicked(self):

        height=self.filter_list.height()
        if height>0:
            self.filter_list.setVisible(not self.filter_list.isVisible())
            self.fold_filter_button.setArrowType(Qt.UpArrow)
        else:
            self.filter_list.setVisible(not self.filter_list.isVisible())
            self.fold_filter_button.setArrowType(Qt.DownArrow)
        return


    def foldTabButtonClicked(self):

        width=self.tabs.width()
        if width>0:
            self.tabs.setVisible(not self.tabs.isVisible())
            self.fold_tab_button.setArrowType(Qt.LeftArrow)
        else:
            self.tabs.setVisible(not self.tabs.isVisible())
            self.fold_tab_button.setArrowType(Qt.RightArrow)
        return

    def clearFilterButtonClicked(self):

        if self.clear_filter_frame.isVisible():
            self.clear_filter_frame.setVisible(False)

        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

        current_folder=self._current_folder
        if current_folder:
            folder,folderid=current_folder

            # TODO: keep a record of previous sortidx?
            if folder=='All' and folderid=='-1':
                self.loadDocTable(None,sortidx=4,sel_row=0)
            else:
                self.loadDocTable((folder,folderid),sortidx=4,sel_row=0)
            self.doc_table.selectRow(0)


        return

    def clearDuplicateButtonClicked(self):

        if self.duplicate_result_frame.isVisible():
            self.duplicate_result_frame.setVisible(False)

        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

            current_folder=self._current_folder
            if current_folder:
                folder,folderid=current_folder

                # TODO: keep a record of previous sortidx?
                if folder=='All' and folderid=='-1':
                    self.loadDocTable(None,sortidx=4,sel_row=0)
                else:
                    self.loadDocTable((folder,folderid),sortidx=4,sel_row=0)
                self.doc_table.selectRow(0)




    def searchBarClicked(self):
        print('search term:', self.search_bar.text())

    def copyBibButtonClicked(self):
        self.bib_textedit.selectAll()
        self.bib_textedit.copy()


    def clearData(self):

        self.clearMetaTab()
        self.doc_table.model().arraydata=[]
        self.libtree.clear()
        self.filter_item_list.clear()

        self.add_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.duplicate_check_button.setEnabled(False)

        print('# <clearData>: Data cleared.')
        self.logger.info('Data cleared.')
