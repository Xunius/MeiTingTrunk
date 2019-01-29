from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from lib import sqlitedb
from lib import export2bib




def addFolder(parent,folderid,folder_dict):

    foldername,parentid=folder_dict[folderid]
    fitem=QtWidgets.QTreeWidgetItem([foldername,str(folderid)])
    style=QtWidgets.QApplication.style()
    diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
    fitem.setIcon(0,diropen_icon)
    sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
    if parentid=='0' or parentid=='-1':
        parent.addTopLevelItem(fitem)
    else:
        parent.addChild(fitem)
    if len(sub_ids)>0:
        for sii in sub_ids:
            addFolder(fitem,sii,folder_dict)

    return

def prepareDocs(meta_dict,docids):

    data=[]
    for ii in docids:
        entryii=meta_dict[ii]
        aii=[ii,
            QtWidgets.QCheckBox(entryii['favourite']),
            QtWidgets.QCheckBox(entryii['read']),
            entryii['has_file'],
            '; '.join(entryii['authors_l']),
            entryii['title'],
            entryii['publication'],
            entryii['year'],
            entryii['added']
            ]

        data.append(aii)

    return data



class MainFrameLoadData:

    @property
    def _tabledata(self):
        if hasattr(self,'doc_table'):
            return self.doc_table.model().arraydata
        else:
            return None

    @property
    def _current_doc(self):
        if hasattr(self,'doc_table'):
            current_row=self.doc_table.currentIndex().row()
            if current_row < len(self._tabledata):
                docid=self._tabledata[current_row][0]
                return docid
            else:
                print('_current_doc: current_row > row number',current_row,\
                        len(self._tabledata))
                return None
        else:
            return None

    @property
    def _current_meta_dict(self):
        if hasattr(self,'t_meta'):
            if hasattr(self.t_meta,'fields_dict'):
                return self.t_meta.fields_dict
        return None

    @property
    def _current_folder(self):
        if hasattr(self,'libtree'):
            item=self.libtree.selectedItems()
            if item:
                item=item[0]
                return item.data(0,0), item.data(1,0) # folder name, folderid
        return None

    @property
    def _current_docids(self):
        if hasattr(self,'doc_table'):
            docid=[ii[0] for ii in self._tabledata]
            return docid
        else:
            return None


    def update_tabledata(self,docid,meta_dict):
        # need to update 'added' time
        print('update_tabledata')
        if docid is None:

            newid=max(self.meta_dict.keys())+1

            # update folder_data
            foldername,folderid=self._current_folder
            if folderid not in ['0', '-2']:
                self.folder_data[folderid].append(newid)

                if (folderid, foldername) not in meta_dict['folders_l']:
                    meta_dict['folders_l'].append((folderid,foldername))
                    print('update_tabledata:, add current_folder', foldername,\
                            meta_dict['folders_l'])
            #self.inv_folder_dict={v[0]:k for k,v in self.folder_dict.items()}

            # update meta_dict
            print('update_tabledata: add new doc, give id:',newid)
            self.meta_dict[newid]=meta_dict
            #self.loadDocTable(folder=(foldername,folderid),sortidx=4)
            #self.doc_table.model().rowsInserted.emit()
            self.loadDocTable(docids=self._current_docids+[newid,])
            self.doc_table.scrollToBottom()
            self.doc_table.selectRow(self.doc_table.model().rowCount(None)-1)

        else:
            if docid in self.meta_dict:
                self.meta_dict[docid].update(meta_dict)
            else:
                self.meta_dict[docid]=meta_dict
            self.loadDocTable(docids=self._current_docids)



    def loadLibTree(self):

        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        needsreview_icon=style.standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)

        #-------------Get all level 1 folders-------------
        folders1=[(vv[0],kk) for kk,vv in self.folder_dict.items() if\
                vv[1]=='0' or vv[1]=='-1']
        folders1.sort()

        allitem=QtWidgets.QTreeWidgetItem(['All','0'])
        allitem.setIcon(0,diropen_icon)
        self.libtree.addTopLevelItem(allitem)

        needsreviewitem=QtWidgets.QTreeWidgetItem(['Needs Review','-2'])
        needsreviewitem.setIcon(0,needsreview_icon)
        self.libtree.addTopLevelItem(needsreviewitem)

        for fnameii,idii in folders1:
            addFolder(self.libtree,idii,self.folder_dict)

        self.libtree.setCurrentItem(allitem)
        self.libtree.itemChanged.connect(self.addNewFolderToDict)

        return



    def loadDocTable(self,folder=None,docids=None,sortidx=None):
        '''Load doc table given folder'''

        tablemodel=self.doc_table.model()

        print('load tabel', folder)
        hh=self.doc_table.horizontalHeader()
        print('sort indicator section:', hh.sortIndicatorSection())
        print('sort indicator order:', hh.sortIndicatorOrder())

        #-----------Get list of doc ids to load-----------
        if docids is None:

            if folder is None:
                docids=self.meta_dict.keys()
            elif folder is not None and folder[0]=='All' and folder[1]=='0':
                docids=self.meta_dict.keys()
            #elif folder is not None and folder[0]=='Needs Review' and folder[1]=='-2':
                #docids=self.folder_data['-2']
            else:
                folderid=folder[1]
                docids=self.folder_data[folderid]

        '''
        if docids is None:
            if folder is None:
                docids=self.meta_dict.keys()
            else:
                folderid=folder[1]
                docids=self.folder_data[folderid]
            data=prepareDocs(self.meta_dict,docids)
        else:
            data=prepareDocs(self.meta_dict,docids)
        '''
        data=prepareDocs(self.meta_dict,docids)

        print('num of docs in folder',len(docids))
        tablemodel.arraydata=data
        if sortidx is not None and sortidx in range(tablemodel.columnCount(None)):
            print('loaddoctable:, sort idx', sortidx)
            tablemodel.sort(sortidx,Qt.AscendingOrder)

        print('loadDocTable: -----------', len(data))
        #------------Load meta data on 1st row------------
        if len(data)>0:
            self.enableMetaTab()
            #self.doc_table.selectRow(0)
            current_row=self.doc_table.currentIndex().row()
            docid=self._current_doc
            print('current_row',current_row, docid)
            #self.loadMetaTab(docid)
        else:
            # clear meta tab
            self.clearMetaTab()

        #self.doc_table.viewport().update()
        tablemodel.layoutChanged.emit()


    def loadMetaTab(self,docid=None):
        print('loadMetaTab',docid)
        if docid is None:
            return

        fields=self._current_meta_dict.keys()
        if fields is None:
            return

        metaii=self.meta_dict[docid]
        def conv(text):
            if isinstance(text,(str)):
                return text
            else:
                return str(text)

        for fii in fields:
            tii=metaii[fii]
            if tii is None:
                #self.t_meta.fields_dict[fii].clear()
                self._current_meta_dict[fii].clear()
                continue
            elif fii=='files_l':
                # show only file name
                self.t_meta.delFileField()
                for fjj in tii:
                    self.t_meta.createFileField(fjj)
            else:
                if isinstance(tii,(list,tuple)):
                    tii=u'; '.join(tii)
                self._current_meta_dict[fii].setText(conv(tii))

        return




    def loadBibTab(self,docid=None):
        print('loadBibTab',docid)
        if docid is None:
            return

        metaii=self.meta_dict[docid]
        #import bibtexparser
        #bb=bibtexparser.bibdatabase.BibDatabase()

        text=export2bib.parseMeta(metaii,'',metaii['folders_l'],True,False,
                True)

        self.bib_textedit.setText(text)

        return


