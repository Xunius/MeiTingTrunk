import os
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor, QFontMetrics,\
        QCursor
from queue import Queue
from lib import sqlitedb
from lib import widgets
from lib import bibparse
from lib import retrievepdfmeta
from lib.tools import getXExpandYMinSizePolicy, WorkerThread
#from _MainFrameLoadData import addFolder





def addPDF(abpath):
    print('addPDF. abpath=',abpath)
    try:
        pdfmetaii=retrievepdfmeta.getPDFMeta_pypdf2(abpath)
        pdfmetaii=retrievepdfmeta.prepareMeta(pdfmetaii)
        pdfmetaii['files_l']=[abpath,]
        rec=0
    except:
        pdfmetaii={}
        rec=1
    return rec,pdfmetaii


def walkFolderTree(folder_dict,folder_data,folderid,docids=None,folderids=None):

    if docids is None:
        docids=[]
    if folderids is None:
        folderids=[]

    docids.extend(folder_data[folderid])
    folderids.append(folderid)

    subfolderids=sqlitedb.getChildFolders(folder_dict,folderid)
    for sii in subfolderids:
        folderids,docids=walkFolderTree(folder_dict,folder_data,sii,
                docids,folderids)

    folderids=list(set(folderids))
    docids=list(set(docids))

    return folderids,docids


class MainFrameSlots:

    #######################################################################
    #                        Tool bar button slots                        #
    #######################################################################
    

    def addActionTriggered(self,action):
        print('addActionTriggered:', action)
        action_text=action.text()
        print(action.text())


        if action_text=='Add PDF File':
            fname = QtWidgets.QFileDialog.getOpenFileNames(self, 'Choose a PDF file',
         '',"PDF files (*.pdf);; All files (*)")
            print('addActionTriggered: chosen PDF file:', fname)
            if fname:
                faillist=[]
                self.doc_table.clearSelection()
                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.MultiSelection)

                jobqueue=Queue()
                resqueue=Queue()

                # add progress bar
                #if len(fname[0])>2:
                pb=QtWidgets.QProgressBar(self)
                pb.setSizePolicy(getXExpandYMinSizePolicy())
                #pb.setGeometry(0,0,10,100)
                pb.setMaximum(len(fname[0]))
                self.status_bar.showMessage('Adding PDF files...')
                self.status_bar.addPermanentWidget(pb)

                for ii,fii in enumerate(fname[0]):
                    jobqueue.put((fii,))

                threads=[]
                for ii in range(min(3,len(fname[0]))):
                    tii=WorkerThread(addPDF,jobqueue,resqueue,self)
                    threads.append(tii)
                    tii.start()

                jobqueue.join()

                #-------------------Get results-------------------
                results=[]
                while resqueue.qsize():
                    try:
                        resii=resqueue.get()
                        if resii[0]==0:
                            results.append(resii[1])
                            pb.setValue(len(results))
                            self.update_tabledata(None,resii[1])
                        else:
                            faillist.append(resii[1])
                    except:
                        break




                '''
                for ii,fii in enumerate(fname[0]):
                    try:
                        pb.setValue(ii+1)

                        pdfmetaii=retrievepdfmeta.getPDFMeta_pypdf2(fii)
                        pdfmetaii=retrievepdfmeta.prepareMeta(pdfmetaii)
                        pdfmetaii['files_l']=[fii,]
                        print('pdfmetaii',pdfmetaii)
                        self.update_tabledata(None,pdfmetaii)

                    except:
                        faillist.append(fii)
                '''

                print('faillist:',faillist)
                pb.hide()
                self.status_bar.clearMessage()
                self.doc_table.setSelectionMode(
                        QtWidgets.QAbstractItemView.ExtendedSelection)


        elif action_text=='Add BibTex File':
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a bibtex file',
         '',"Bibtex files (*.bib);; All files (*)")
            print('addActionTriggered: chosen bib file:', fname)
            if fname:
                try:
                    bib_entries=bibparse.readBibFile(fname[0])
                    print('parsed bib file:', bib_entries)
                    self.doc_table.clearSelection()
                    self.doc_table.setSelectionMode(
                            QtWidgets.QAbstractItemView.MultiSelection)
                    for eii in bib_entries:
                        self.update_tabledata(None,eii)
                except Exception as e:
                    print('failed to parse bib file')
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
            dialog=widgets.MetaDataEntryDialog(self.font_dict,self)
            dl_ret,dl_dict=dialog.exec_()
            print('addActionTriggered:, dl_ret',dl_ret)
            if dl_ret:
                print('addActionTriggered: return value:',dl_dict)
                #print(ret['title'].toPlainText())
                self.update_tabledata(None, dl_dict)

        return


    def addFolderButtonClicked(self):

        print('addFolderButtonClicked:')
        item=self.libtree.selectedItems()
        if item:
            item=item[0]

            folderid=item.data(1,0)
            current_ids=map(int,self.folder_dict.keys())
            newid=str(max(current_ids)+1)

            fitem=QtWidgets.QTreeWidgetItem(['New folder',str(newid)])
            style=QtWidgets.QApplication.style()
            diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
            fitem.setIcon(0,diropen_icon)
            fitem.setFlags(fitem.flags() | Qt.ItemIsEditable)

            if folderid=='0' or folderid=='-1':
                self.libtree.addTopLevelItem(fitem)
            else:
                item.setExpanded(True)
                item.addChild(fitem)


            self.libtree.scrollToItem(fitem)
            self.libtree.editItem(fitem)
            self.folder_dict[newid]=('New folder',folderid)

    def addNewFolderToDict(self,item,column):
        #NOTE: probably have to use a treemodel+view for lib tree
        # this is called for color changes as well
        print('addNewFolderToDict','item=',item,'column=',column)
        print('item.data',item.data(0,0),item.data(1,0))

        foldername,folderid=item.data(0,0), item.data(1,0)
        if folderid not in ['0', '-1', '-2']:
            fnameold,parentid=self.folder_dict[folderid]
            print('old foldername=',fnameold,'parentid=',parentid)
            self.folder_dict[folderid]=[foldername,parentid]
            print('new foldername and parentid =',self.folder_dict[folderid])
            if folderid not in self.folder_data:
                self.folder_data[folderid]=[]





    #######################################################################
    #                            Libtree slots                            #
    #######################################################################



    def clickSelFolder(self,item,column):
        '''Select folder by clicking'''
        folder=item.data(0,0)
        folderid=item.data(1,0)
        print('clickSelFolder: folder', folder,'folderid',folderid)
        if folder=='All' and folderid=='0':
            self.loadDocTable(folder=None,sortidx=4)
        else:
            self.loadDocTable((folder,folderid),sortidx=4)


        if folder=='Needs Review' and folderid=='-2':
            self.add_button.setDisabled(True)
        else:
            self.add_button.setEnabled(True)
        #self.doc_table.selectRow(0)

        # Refresh filter list
        self.filterTypeCombboxChange(item)


    def selFolder(self,selected,deselected):
        '''Select folder by changing current'''
        item=self.libtree.selectedItems()
        if item:
            item=item[0]
            column=0
            print('selFolder:',item.data(0,0),item.data(1,0),'selected column', column)
            self.clickSelFolder(item,column)


    def libTreeMenu(self,pos):

        menu=QtWidgets.QMenu()
        add_action=menu.addAction('Add folder')
        del_action=menu.addAction('Delete')
        rename_action=menu.addAction('Rename')

        action=menu.exec_(QCursor.pos())
        print('libTreeMenu: action:',action)
        if action==add_action:
            self.addFolderButtonClicked()
        elif action==del_action:
            self.delFolder()

    def delFolder(self):

        choice=QtWidgets.QMessageBox.question(self, 'Confirm deletion',
                'Deleting a folder will delete all sub-folders and documents inside.\n\nConfirm?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)


        if choice==QtWidgets.QMessageBox.Yes:

            item=self.libtree.selectedItems()
            if item:
                item=item[0]

                folderid=item.data(1,0)
                #TODO: has to walk through child folders

                delfolderids,deldocids=walkFolderTree(self.folder_dict,
                        self.folder_data,folderid)

                print('delfolderids:',delfolderids)
                print('docs to del', deldocids)

                for idii in deldocids:
                    del self.meta_dict[idii]
                    #print(idii,'in meta_dict?',idii in self.meta_dict)

                for fii in delfolderids:
                    #print('del folder',fii,self.folder_dict[fii])
                    del self.folder_data[fii]
                    del self.folder_dict[fii]
                    #print(fii,'in folder_data?',fii in self.folder_data)
                    #print(fii,'in folder_dict?',fii in self.folder_dict)

                root=self.libtree.invisibleRootItem()
                (item.parent() or root).removeChild(item)





    #######################################################################
    #                          Filter list slots                          #
    #######################################################################
    
    def filterItemClicked(self,item):

        print('filteritemclicked:, item:', item, item.text())
        filter_type=self.filter_type_combbox.currentText()
        filter_text=item.text()
        current_folder=self._current_folder
        if current_folder:
            folderid=current_folder[1]

            filter_docids=sqlitedb.filterDocs(self.meta_dict,self.folder_data,
                    filter_type,filter_text,folderid)

            if len(filter_docids)>0:
                self.loadDocTable(None,filter_docids,sortidx=4)
                self.doc_table.selectRow(0)

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
        print('filter type cb select:',sel)
        if current_folder:
            print('filtertypecombochange: currentfolder:',\
                    current_folder[0], current_folder[1])

            #---------------Get items in folder---------------
            foldername,folderid=current_folder
            if foldername=='All' and folderid=='0':
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
        print('docTableClicked: clicked, set to extendedselection')
        self.doc_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)


    def selDoc(self,current,previous):
        '''Actions on selecting a document in doc table
        '''
        rowid=current.row()
        docid=self._tabledata[rowid][0]
        print('selDoc: rowid', rowid, 'docid', docid)
        self.loadMetaTab(docid)
        self.loadBibTab(docid)

        #-------------------Get folders-------------------
        metaii=self.meta_dict[docid]
        folders=metaii['folders_l']
        folders=[fii[1] for fii in folders]
        print('folders of docid', folders, docid)

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
        self.libtree.itemChanged.disconnect()
        for item in iterItems(self.libtree, root):
            item.setBackground(0, ori_color)

        #------------Search folders in libtree------------
        for fii in folders:
            mii=self.libtree.findItems(fii, Qt.MatchExactly | Qt.MatchRecursive)
            if len(mii)>0:
                for mjj in mii:
                    mjj.setBackground(0, hi_color)

        # re-connect libtree item change signal
        self.libtree.itemChanged.connect(self.addNewFolderToDict)


    def docTableMenu(self,pos):

        menu=QtWidgets.QMenu()
        add_action1=menu.addAction('Open file')
        add_action2=menu.addAction('Delete')
        add_action3=menu.addAction('Export citation')

        menu.exec_(QCursor.pos())







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
            current_folder=self._current_folder
            if current_folder:
                folder,folderid=current_folder

                # TODO: keep a record of previous sortidx?
                if folder=='All' and folderid=='0':
                    self.loadDocTable(None,sortidx=4)
                else:
                    self.loadDocTable((folder,folderid),sortidx=4)
                self.doc_table.selectRow(0)

        return




    def searchBarClicked(self):
        print('search term:', self.search_bar.text())

    def copyBibButtonClicked(self):
        self.bib_textedit.selectAll()
        self.bib_textedit.copy()


