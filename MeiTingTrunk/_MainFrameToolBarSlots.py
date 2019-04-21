'''
This part contains functions handling actions triggered from the tool bar
buttons or search bar, including adding new doc, new folder, duplicate checking
and searching.


MeiTing Trunk

An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QBrush
from PyQt5 import QtWidgets
from .lib import sqlitedb
from .lib import bibparse, risparse
from .lib import retrievepdfmeta
from .lib.widgets import FailDialog, ThreadRunDialog
import logging


def _addPDF(jobid, abpath):
    """Retrieve meta data from PDF file

    Args:
        jobid (int): job id.
        abpath (str): abspath to a PDF file

    Returns:
        rec (int): 0 for success, 1 otherwise.
        jobid (int): the input jobid returned as it is.
        pdfmetaii (DocMeta): dict storing meta data retrieved from PDF.
    """

    try:
        pdfmetaii=retrievepdfmeta.getPDFMeta_pypdf2(abpath)
        pdfmetaii=retrievepdfmeta.prepareMeta(pdfmetaii)
        pdfmetaii['files_l']=[abpath,]
        rec=0
    except:
        pdfmetaii={}
        rec=1
    return rec,jobid,pdfmetaii


def checkFolderName(foldername, folderid, folder_dict):
    """Check for folder name conflicts

    Args:
        foldername (str): proposed name for folder.
        folderid (str): id of folder.
        folder_dict (dict): dict of folder info. key = folder_id,
                            value = (foldername, parent_id)

    Returns:
        0 if proposed name <foldername> doesn't confict with other folders
        with the same parent. 1 otherwise.
    """

    logger=logging.getLogger(__name__)

    toplevelids=[kk for kk,vv in folder_dict.items() if vv[1]=='-1']

    logger.debug('toplevelids = %s. folderid = %s' \
            %(toplevelids, folderid))

    if folderid in toplevelids:
        siblings=[folder_dict[ii][0] for ii in toplevelids if ii!=folderid]
    else:
        parentid=folder_dict[folderid][1]
        siblings=[]
        for kk,vv in folder_dict.items():
            if kk!=folderid and vv[1]==parentid:
                siblings.append(vv[0])

    if foldername in siblings:
        logger.info('foldername in siblings. foldername = %s. siblings = %s'\
                %(foldername, siblings))
        return 1

    return 0



class MainFrameToolBarSlots:

    #######################################################################
    #                        Tool bar button slots                        #
    #######################################################################


    @pyqtSlot(QtWidgets.QAction)
    def addActionTriggered(self, action):
        """Add new document to current folder

        Args:
            action (QAction): QAction sent by menu button.

        This is a slot to the triggered signal of the Add button in the tool
        bar, and is responsible for handling adding new document to the current
        folder via PDF, bibtex, RIS or manual inputs.
        """

        # action.data() is used in labelling the default add action.
        # if it's not None, return
        if action.data() is not None:
            self.logger.debug('action.data() = %s is not None. Return.' %action.data())
            return

        action_text=action.text()

        self.logger.info('action.text() = %s. action.data() = %s'\
                %(action_text, action.data()))

        #---------------------Add PDF---------------------
        if action_text=='Add PDF File':

            fname = QtWidgets.QFileDialog.getOpenFileNames(self,
                    'Choose a PDF file', '',
                    "PDF files (*.pdf);; All files (*)")[0]

            self.logger.info('Chosen PDF file = %s' %fname)

            if fname:
                self.doc_table.clearSelection()
                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.MultiSelection)

                joblist=list(zip(range(len(fname)), fname))

                t_dialog=ThreadRunDialog(_addPDF, joblist,
                        show_message='Adding PDF Files...',
                        max_threads=1,
                        get_results=True,
                        close_on_finish=True,
                        progressbar_style='classic',
                        parent=self)

                t_dialog.exec_()

                # collect failures
                faillist=[]
                for recii,jobidii,meta_dictii in t_dialog.results:

                    self.logger.debug('rec of t_dialog = %s. jobid = %s. meta_dict = %s'\
                            %(recii, jobidii, meta_dictii))

                    if recii==0:
                        self.updateTableData(None,meta_dictii)
                    else:
                        faillist.append(jobidii)

                fail_files=[jii[1] for jii in joblist if jii[0] in faillist]

                if len(fail_files)>0:

                    fail_docids=[]
                    for fii in fail_files:
                        metaii=sqlitedb.DocMeta()
                        metaii['files_l']=[fii,]
                        docidii=self.updateTableData(None,metaii)
                        fail_docids.append(docidii)

                    msg=FailDialog()
                    msg.setText('Oopsie.')
                    msg.setInformativeText('Failed to retrieve metadata from some files.')
                    msg.setDetailedText('\n'.join(fail_files))
                    msg.create_fail_summary.connect(lambda: self.createFailFolder(
                        'Add PDFs', fail_docids))
                    msg.exec_()

                self.logger.warning('failed list for PDF import = %s' %faillist)

                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.ExtendedSelection)


        #--------------------Add bibtex--------------------
        elif action_text=='Add Bibtex File':
            fname = QtWidgets.QFileDialog.getOpenFileName(self,
                    'Choose a bibtex file',
                    '',
                    "Bibtex files (*.bib);; All files (*)")[0]
            self.logger.info('Chosen bib file = %s' %fname)

            if fname:
                try:
                    bib_entries=bibparse.readBibFile(fname)
                    self.doc_table.clearSelection()
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.MultiSelection)
                    for eii in bib_entries:
                        self.updateTableData(None,eii)
                except Exception as e:
                    self.logger.exception('Failed to parse bib file.')

                    msg=QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setWindowTitle('Error')
                    msg.setText('Oopsie. Failed to parse bib file.')
                    msg.setInformativeText('bibtexparser complaints:\n\n%s' %str(e))
                    msg.exec_()
                finally:
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.ExtendedSelection)


        #---------------------Add RIS---------------------
        elif action_text=='Add RIS File':

            fname = QtWidgets.QFileDialog.getOpenFileName(self,
                    'Choose an RIS file',
                    '',
                    "RIS files (*.ris);; All files (*)")[0]
            self.logger.info('Chosen ris file = %s' %fname)

            if fname:
                try:
                    ris_entries=risparse.readRISFile(fname)
                    self.doc_table.clearSelection()
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.MultiSelection)
                    for eii in ris_entries:
                        self.updateTableData(None,eii)
                except Exception as e:
                    self.logger.exception('Failed to parse RIS file.')

                    msg=QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setWindowTitle('Error')
                    msg.setText('Oopsie. Failed to parse RIS file.')
                    msg.setInformativeText('RISparser complaints:\n\n%s' %str(e))
                    msg.exec_()
                finally:
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.ExtendedSelection)


        #-------------------Add manually-------------------
        elif action_text=='Add Entry Manually':

            dummy=sqlitedb.DocMeta()
            self.updateTableData(None, dummy)

        return


    @pyqtSlot(QtWidgets.QAction)
    def addFolderButtonClicked(self, action):
        """Add new folder

        Args:
            action (QAction): QAction sent by menu button.

        This is a slot to the triggered signal of the Add Folder button in the
        tool bar, and is responsible for handling adding new folder to the
        folder tree.
        """

        item=self._current_folder_item
        if item:
            folderid=item.data(1,0)

            # create new item
            if len(self.folder_dict.keys())==0:
                newid='0'
            else:
                current_ids=map(int,self.folder_dict.keys())
                newid=str(max(current_ids)+1)
            newitem=QtWidgets.QTreeWidgetItem(['New folder',str(newid)])
            style=QtWidgets.QApplication.style()
            diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
            newitem.setIcon(0,diropen_icon)
            newitem.setFlags(newitem.flags() | Qt.ItemIsEditable)

            action_text=action.text().replace('&','') # remove shortcut symbol

            if action_text=='Create Folder':
                toplevelids=[self.libtree.topLevelItem(jj).data(1,0) for jj\
                        in range(self.libtree.topLevelItemCount())]

                if folderid in toplevelids:
                    self.libtree.addTopLevelItem(newitem)
                    parentid='-1'
                    self.logger.info('action.text() = %s. As top level folder' %action.text())
                else:
                    item.parent().addChild(newitem)
                    parentid=item.parent().data(1,0)
                    self.logger.info('action.text() = %s. As subfolder' %action.text())

            elif action_text=='Create Sub Folder':
                item.addChild(newitem)
                parentid=folderid
                self.logger.info('action.text() = %s. As subfolder' %action.text())

            self.libtree.scrollToItem(newitem)
            self.folder_dict[newid]=('New folder',parentid)
            if newid not in self.folder_data:
                self.folder_data[newid]=[]

            # let user edit folder name
            self.libtree.editItem(newitem)

            self.logger.info('New folder id = %s' %newid)

        return


    @pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def addNewFolderToDict(self, item, column):
        """Add newly create folder to folder dict

        Args:
            item (QTreeWidgetItem): newly created item for folder.
            column (int): column of change. Not used.

        This is a slot to the libtree.itemChanged signal, which is emitted when
        data associated with a QTreeWidgetItem is changed. NOTE that by default
        this covers ANY data change in an item, including its text, icon,
        background color etc.. I need to restrict this signal firing to only
        text changes (renaming folders). This is achieved by connecting
        this signal in the commitData() method of the QTreeWidget (see
        lib/widgets/folder_tree.py), and after emitting, disconnect immediately.
        Therefore this is called whenever libtree.editItem() is called, for
        instance in addFolderButtonClicked(), to update the changed folder
        name to the folder_dict.
        """

        foldername,folderid=item.data(0,0), item.data(1,0)
        self.logger.info('foldername = %s. folder id = %s'\
                %(foldername, folderid))

        if folderid not in ['-1', '-2', '-3']:
            fnameold,parentid=self.folder_dict[folderid]
            self.logger.debug('Old folder name = %s. parentid = %s'\
                    %(fnameold, parentid))

            # add new folder
            if folderid not in self.folder_data:
                self.folder_data[folderid]=[]

            # check validity of new name
            valid=checkFolderName(foldername,folderid,self.folder_dict)
            if valid!=0:

                self.logger.warning('Found invalid folder name: %s' %foldername)
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle('Name conflict')
                msg.setText('Name conflict.')
                msg.setInformativeText('The given name\n\t%s\nconflicts with another folder name.\nPlease choose another name.' %foldername)
                msg.exec_()

                item.setData(0,0,fnameold)
                # let user input again
                self.libtree.editItem(item)

                return

            # if name valid, update to dict
            self.folder_dict[folderid]=[foldername,parentid]
            self.logger.info('Added new folder name = %s. parentid = %s'\
                    %(self.folder_dict[folderid][0], self.folder_dict[folderid][1]))

        self.sortFolders()
        self.libtree.setCurrentItem(item)
        self.changed_folder_ids.append(folderid)

        return


    def sortFolders(self):
        '''Sort folders in alphabetic order while keeping sys folder at top'''

        def moveItemToTop(item):
            idx=self.libtree.indexOfTopLevelItem(item)
            item=self.libtree.takeTopLevelItem(idx)
            self.libtree.insertTopLevelItem(0,item)

        self.libtree.sortItems(0,Qt.AscendingOrder)

        # move system folders to back to top
        for itemii in reversed(self.sys_folders):
            moveItemToTop(itemii)

        return


    @pyqtSlot()
    def checkDuplicateClicked(self):
        """Check duplicates within current folder

        This is a slot to the triggered signal of the Check Duplicate button in
        the tool bar.
        """

        docids=self._current_docids
        self.doc_table.setVisible(False)

        current_folder=self._current_folder[0]
        self.duplicate_result_frame.clear_duplicate_label.setText(
                'Checking duplicates in folder "%s".' %current_folder)

        self.duplicate_result_frame.checkDuplicates(self.meta_dict,
                self.folder_dict,
                self._current_folder,
                docids,
                None)

        return


    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem)
    def duplicateResultCurrentChange(self, current, previous):
        """Select a doc in the result of duplicate checking

        Args:
            current (QTreeWidgetItem): item for a doc in the result tree widget.
            previous (QTreeWidgetItem): not used.

        """

        if current:
            docid=int(current.data(6,0))
            self.logger.info('current doc id = %s' %docid)
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


    @pyqtSlot()
    def searchBarClicked(self):
        """Start search in the database

        This is a slot to the clicked signal of the search button in the tool
        bar, and to the returnPressed signal of the search_bar.

        Search text is retrieved from the search bar, and search options
        are collected from the states of the search button menu. Then
        these are passed as input args to the search function defined in
        lib/widgets/search_res_frame.py

        NOTE that as search is done in the sqlite data, a saving is first
        called.
        """

        text=self.search_bar.text()
        self.logger.info('Searched term = %s' %text)

        if len(text)==0:
            return

        #-----------Get search fields and option-----------
        menu=self.search_button.menu()
        actions=menu.findChildren(QtWidgets.QWidgetAction)
        new_search_fields=[]

        for actii in actions:
            wii=actii.defaultWidget()
            self.logger.info('action %s isChecked() = %s'\
                    %(actii.text(), wii.isChecked()))

            if actii.text()=='Include sub-folders':
                desend=wii.isChecked()
            else:
                if wii.isChecked():
                    new_search_fields.append(actii.text())

        self.settings.setValue('search/search_fields',new_search_fields)
        self.settings.setValue('search/desend_folder',desend)

        if len(new_search_fields)==0:
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Information')
            msg.setText('Input needed')
            msg.setInformativeText('Select at least one field to search')
            msg.exec_()
            return

        current_folder=self._current_folder

        # NOTE: need to write to sqlite before searching
        self.saveToDatabase()

        # NOTE: order matters here:
        self.status_bar.showMessage('Searching ...')
        self.doc_table.setVisible(False)
        self.search_res_frame.search(self.db, text, new_search_fields,
                current_folder[1], self.meta_dict, self.folder_data, desend)

        return


    def enablePDFSearch(self):

        self.pdf_search_action.setEnabled(True)

        search_fields=self.settings.value('search/search_fields',[],str)
        if isinstance(search_fields,str) and search_fields=='':
            search_fields=[]
        if 'PDF' in search_fields:
            self.pdf_search_checkbox.setChecked(True)

        return


    @pyqtSlot(str,list)
    def createFolderFromSearch(self, search_text, docids):
        """Create a folder and populate with docs selected from search results

        Args:
            search_text (str): searched text in the search bar.
            docids (list): ids of docs to add to the new folder


        This is a slot to the create_folder_sig emitted by the
        search_res_frame. It will create a top level folder with the name
        'search_<search_text>', and add selected docs to it for later use.
        """

        foldername='search_%s' %search_text
        toplevelfolders=[vv[0] for kk,vv in self.folder_dict.items() if\
                vv[1] in ['-1',]]

        self.logger.info('foldername = %s' %foldername)
        self.logger.debug('toplevel folders = %s' %toplevelfolders)

        # rename till no conflict
        append=1
        while foldername in toplevelfolders:
            foldername='%s_%d' %(foldername,append)
            append+=1
            self.logger.debug('new foldername after renaming = %s' %foldername)

        # create new item
        current_ids=map(int,self.folder_dict.keys())
        newid=str(max(current_ids)+1)
        newitem=QtWidgets.QTreeWidgetItem([foldername,str(newid)])
        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        newitem.setIcon(0,diropen_icon)
        newitem.setFlags(newitem.flags() | Qt.ItemIsEditable)

        # add folder
        self.folder_dict[newid]=(foldername,'-1')
        self.folder_data[newid]=docids

        # add folder to docs
        for idii in docids:
            foldersii=self.meta_dict[idii]['folders_l']
            if (newid, foldername) not in foldersii:
                foldersii.append((newid, foldername))
            self.meta_dict[idii]['folders_l']=foldersii

        self.libtree.addTopLevelItem(newitem)
        self.libtree.scrollToItem(newitem)
        self.libtree.setCurrentItem(newitem)

        self.logger.info('New folder id=%s' %newid)
        self.changed_folder_ids.append(newid)
        self.changed_doc_ids.extend(docids)

        return


    @pyqtSlot()
    def hideDocTable(self):
        '''Not in use'''
        if self.doc_table.isVisible():
            self.doc_table.setVisible(False)
        return


    @pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem)
    def searchResultCurrentChange(self,current,previous):
        """Select a doc in the search results

        Args:
            current (QTreeWidgetItem): item for a doc in the result tree widget.
            previous (QTreeWidgetItem): not used.

        """

        if current:
            docid=int(current.data(5,0))
            self.logger.info('current doc id = %s' %docid)
            self.loadMetaTab(docid)
            self.loadBibTab(docid)
            self.loadNoteTab(docid)

        return






