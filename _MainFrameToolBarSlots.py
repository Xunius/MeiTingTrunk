from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from PyQt5 import QtWidgets
from lib import sqlitedb
from lib import sqlitefts
from lib import bibparse, risparse
from lib import retrievepdfmeta
from lib.widgets import FailDialog
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

class MainFrameToolBarSlots:

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

        if action.data() is not None:
            return

        action_text=action.text()

        print('# <addActionTriggered>: action.text()=%s' %action_text)
        self.logger.info('action.text()=%s' %action_text)

        print('# <addActionTriggered>: action data=',action.data())

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

                faillist=[]
                for recii,jobidii,meta_dictii in t_dialog:
                    print('# <addActionTriggered>: rec of t_dialog:',
                            recii,jobidii,meta_dictii)
                    if recii==0:
                        self.updateTabelData(None,meta_dictii)
                    else:
                        faillist.append(jobidii)

                fail_files=[jii[1] for jii in joblist if jii[0] in faillist]

                if len(fail_files)>0:

                    for fii in fail_files:
                        metaii=sqlitedb.DocMeta()
                        metaii['files_l']=[fii,]
                        self.updateTabelData(None,metaii)

                    msg=FailDialog()
                    msg.setText('Oopsie.')
                    msg.setInformativeText('Failed to retrieve metadata from some files.')
                    msg.setDetailedText('\n'.join(fail_files))
                    msg.exec_()


                print('# <addActionTriggered>: failist for PDF importing', fail_files)
                #self.logger.info('failist for PDF importing: %s' %faillist)

                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.ExtendedSelection)


        elif action_text=='Add Bibtex File':
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

        elif action_text=='Add RIS File':
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose an RIS file',
         '',"RIS files (*.ris);; All files (*)")[0]

            print('# <addActionTriggered>: Chosen ris file=%s' %fname)
            self.logger.info('Chosen ris file=%s' %fname)

            if fname:
                try:
                    ris_entries=risparse.readRISFile(fname)
                    self.doc_table.clearSelection()
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.MultiSelection)
                    for eii in ris_entries:
                        self.updateTabelData(None,eii)
                except Exception as e:
                    print('# <addActionTriggered>: Failed to parse RIS file.')
                    self.logger.info('Failed to parse RIS file.')

                    msg=QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setWindowTitle('Error')
                    msg.setText('Oopsie. Failed to parse RIS file.')
                    msg.setInformativeText('RISparser complaints:\n\n%s' %str(e))
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
        #self.duplicate_result_frame.addResultToTree()
        #self.duplicate_result_frame.setVisible(True)

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


    @pyqtSlot()
    def searchBarClicked(self):
        text=self.search_bar.text()
        if len(text)==0:
            return

        menu=self.search_button.menu()
        actions=menu.findChildren(QtWidgets.QWidgetAction)
        new_search_fields=[]
        for actii in actions:
            wii=actii.defaultWidget()
            print('# <searchBarClicked>: actii',actii.text(),wii.isChecked())
            if wii.isChecked():
                new_search_fields.append(actii.text())

        self.settings.setValue('search/search_fields',new_search_fields)

        if len(new_search_fields)==0:
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Information')
            msg.setText('Input needed')
            msg.setInformativeText('Select at least one field to search')
            msg.exec_()
            return

        current_folder=self._current_folder
        print('# <searchBarClicked>: folder=',current_folder)

        # TODO: need to write sqlite before searching

        # NOTE: order matters here:
        self.status_bar.showMessage('Searching ...')
        self.doc_table.setVisible(False)
        self.search_res_frame.search(self.db, text, new_search_fields,
                current_folder[1], self.meta_dict)

        return


    @pyqtSlot(str,list)
    def createFolderFromSearch(self, search_text, docids):
        foldername='search_%s' %search_text

        toplevelfolders=[vv[0] for kk,vv in self.folder_dict.items() if\
                vv[1] in ['-1',]]
        print('# <createFolderFromSearch>: toplevel folders=',toplevelfolders)

        # rename till no conflict
        append=1
        while foldername in toplevelfolders:
            foldername='%s_(%d)' %(foldername,append)
            append+=1

        # create new item
        current_ids=map(int,self.folder_dict.keys())
        newid=str(max(current_ids)+1)
        newitem=QtWidgets.QTreeWidgetItem([foldername,str(newid)])
        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        newitem.setIcon(0,diropen_icon)
        newitem.setFlags(newitem.flags() | Qt.ItemIsEditable)

        self.folder_dict[newid]=(foldername,'-1')
        self.folder_data[newid]=docids
        self.libtree.addTopLevelItem(newitem)
        self.libtree.scrollToItem(newitem)
        self.libtree.setCurrentItem(newitem)

        print('# <createFolderFromSearch>: Folder new id=%s. New entry in folder_dict=%s' %(newid, self.folder_dict[newid]))
        self.logger.info('Folder new id=%s. New entry in folder_dict=%s' %(newid, self))

        return

    @pyqtSlot()
    def hideDocTable(self):
        if self.doc_table.isVisible():
            self.doc_table.setVisible(False)
        return

    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem)
    def searchResultCurrentChange(self,current,previous):

        if current:
            docid=int(current.data(5,0))

            print('# <searchResultCurrentChange>: current=%s' %docid)
            self.logger.info('current=%s' %docid)

            self.loadMetaTab(docid)
            self.loadBibTab(docid)
            self.loadNoteTab(docid)

        return






