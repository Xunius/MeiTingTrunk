from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor, QFontMetrics,\
        QCursor
from lib import sqlitedb

class MainFrameSlots:

    def clickSelFolder(self,item,column):
        '''Select folder by clicking'''
        folder=item.data(0,0)
        folderid=item.data(1,0)
        #folder=item.text(column)
        #print('clickSelfolder:', 'item.data', item.data(0,0), item.data(1,0), 'colunm', column)
        self.status_bar.showMessage('Select folder %s, id: %s' %(folder, folderid))
        if folder=='All' and folderid=='0':
            #folder=None
            self.loadDocTable(None)
        else:
            self.loadDocTable((folder,folderid))

        # Refresh filter list
        self.filterTypeCombboxChange(item)


    def selFolder(self,selected,deselected):
        '''Select folder by changing current'''
        item=self.libtree.selectedItems()
        if item:
            item=item[0]
            #print('selFolder:','item', item)
            #column=selected.indexes()[0].column()
            column=0
            #print('selFolder:',item.data(0,0), item.data(1,0))
            print('selFolder:','selected column', column)
            self.clickSelFolder(item,column)


    #######################################################################
    #                          Filter list slots                          #
    #######################################################################
    
    def filterItemClicked(self,item):

        print('filteritemclicked:, item:', item, item.text())
        filter_type=self.filter_type_combbox.currentText()
        filter_text=item.text()
        current_folder=self.libtree.selectedItems()
        if current_folder:
            folderid=current_folder[0].data(1,0)

            filter_docids=sqlitedb.filterDocs(self.meta_dict,self.folder_data,
                    filter_type,filter_text,folderid)

            if len(filter_docids)>0:
                self.loadDocTable(None,filter_docids)

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
        current_folder=self.libtree.selectedItems()
        print('filter type cb select:',sel)
        if current_folder:
            current_folder=current_folder[0]
            print('filtertypecombochange: currentfolder:',\
                    current_folder.data(0,0), current_folder.data(1,0))

            #---------------Get items in folder---------------
            foldername=current_folder.data(0,0)
            folderid=current_folder.data(1,0)
            if foldername=='All' and folderid=='0':
                docids=list(self.meta_dict.keys())
            else:
                docids=self.folder_data[current_folder.data(1,0)]

            if sel=='Filter by keywords':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'keywords',docids,
                        unique=True,sort=True)
            elif sel=='Filter by authors':
                '''
                firsts=sqlitedb.fetchMetaData(self.meta_dict,'firstNames',docids,
                        unique=False,sort=False)
                last=sqlitedb.fetchMetaData(self.meta_dict,'lastName',docids,
                        unique=False,sort=False)
                folderdata=['%s, %s' %(last[ii],firsts[ii]) for ii in range(len(firsts))]
                #folderdata=sqlitedb.getAuthors(self.meta_dict,docids)

                '''
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'authors',docids,
                        unique=False,sort=False)

                #print('filterTypeCombboxChange:', folderdata)
                #print('filterTypeCombboxChange:', aa)
                #print(folderdata==aa)
                #__import__('pdb').set_trace()
            elif sel=='Filter by publications':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'publication',docids,
                        unique=True,sort=True)
            elif sel=='Filter by tags':
                folderdata=sqlitedb.fetchMetaData(self.meta_dict,'tags',docids,
                        unique=True,sort=True)

        folderdata=list(set(folderdata))
        folderdata.sort()
        self.filter_item_list.clear()
        self.filter_item_list.addItems(folderdata)

        return




    #######################################################################
    #                           Doc table slots                           #
    #######################################################################
    

    def selDoc(self,current,previous):
        '''Actions on selecting a document in doc table
        '''
        rowid=current.row()
        docid=self.tabledata[rowid][0]
        self.loadMetaTab(docid)
        self.loadBibTab(docid)

        #-------------------Get folders-------------------
        metaii=self.meta_dict[docid]
        folders=metaii['folder']
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
        for item in iterItems(self.libtree, root):
            item.setBackground(0, ori_color)

        #------------Search folders in libtree------------
        for fii in folders:
            mii=self.libtree.findItems(fii, Qt.MatchExactly | Qt.MatchRecursive)
            if len(mii)>0:
                for mjj in mii:
                    mjj.setBackground(0, hi_color)






    #######################################################################
    #                            Meta tab slots                           #
    #######################################################################

    def clearMetaTab(self):
        for kk,vv in self.t_meta.fields_dict.items():
            vv.clear()
            vv.setReadOnly(True)

        for tii in [self.note_textedit, self.bib_textedit]:
            tii.clear()
            tii.setReadOnly(True)

        return

    def enableMetaTab(self):
        for kk,vv in self.t_meta.fields_dict.items():
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
        #print('foldTabButtonClicked: is checked:', self.fold_tab_button.isChecked())
        #height=self.tabs.height()
        #self.tab_max_width=max(width,self.tab_max_width)
        #print('tabs width',width,'tab_max_width',self.tab_max_width)
        width=self.tabs.width()
        if width>0:
            #self.tabs.setMinimumWidth(0)
            #self.tabs.setMaximumWidth(0)
            #self.tabs.resize(0,height)
            self.tabs.setVisible(not self.tabs.isVisible())
            self.fold_tab_button.setArrowType(Qt.LeftArrow)
        else:
            #self.tabs.resize(self.tab_max_width,height)
            self.tabs.setVisible(not self.tabs.isVisible())
            self.fold_tab_button.setArrowType(Qt.RightArrow)
            #self.tabs.setMinimumWidth(self.tab_max_width)
            #self.tabs.setMaximumWidth(self.tab_max_width)
            #self.tabs.setFixedWidth(self.tab_max_width)
            #self.tabs.setFixedWidth(self.tabs.maximumWidth())
        return

    def clearFilterButtonClicked(self):

        self.clear_filter_frame.setVisible(False)

        current_folder=self.libtree.selectedItems()
        if current_folder:
            folderid=current_folder[0].data(1,0)
            folder=current_folder[0].data(0,0)

            if folder=='All' and folderid=='0':
                self.loadDocTable(None)
            else:
                self.loadDocTable((folder,folderid))

        return






    def addDocButtonClicked(self):
        print('add')

    def searchBarClicked(self):
        print('search term:', self.search_bar.text())

    def copyBibButtonClicked(self):
        self.bib_textedit.selectAll()
        self.bib_textedit.copy()


