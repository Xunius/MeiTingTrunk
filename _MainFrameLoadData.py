from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from lib import sqlitedb
from lib import bibparse
from lib.tools import getHLine




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

def prepareDocs(meta_dict,docids):

    data=[]
    for ii in docids:
        entryii=meta_dict[ii]
        fav_check=QtWidgets.QCheckBox()
        read_check=QtWidgets.QCheckBox()
        fav_check.setChecked(True if entryii['favourite']=='true' else False)
        read_check.setChecked(True if entryii['read']=='true' else False)
        aii=[ii,
            fav_check,
            read_check,
            entryii['has_file'],
            '; '.join(entryii['authors_l']),
            entryii['title'],
            entryii['publication'],
            entryii['year'],
            entryii['added'],
            entryii['confirmed']
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
            if len(self._tabledata)==0:
                return None
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
    def _current_folder_item(self):
        if hasattr(self,'libtree'):
            item=self.libtree.selectedItems()
            if item:
                return item[0]
            else:
                return None
        return None

    @property
    def _current_folder(self):
        if hasattr(self,'libtree'):
            item=self._current_folder_item
            if item:
                return item.data(0,0), item.data(1,0) # folder name, folderid
        return None

    @property
    def _current_docids(self):
        if hasattr(self,'doc_table'):
            docid=[ii[0] for ii in self._tabledata]
            return docid
        else:
            return None

    @property
    def _trashed_folder_ids(self):
        if hasattr(self,'folder_dict'):
            #return self.libtree._trashed_folder_ids
            return sqlitedb.getTrashedFolders(self.folder_dict)



    def loadLibTree(self,db,meta_dict,folder_data,folder_dict):

        self.db=db
        self.meta_dict=meta_dict
        self.folder_data=folder_data
        self.folder_dict=folder_dict
        self.inv_folder_dict={v[0]:k for k,v in self.folder_dict.items()}

        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        needsreview_icon=style.standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
        trash_icon=style.standardIcon(QtWidgets.QStyle.SP_TrashIcon)

        #-------------Create preserved folders-------------
        self.all_folder=QtWidgets.QTreeWidgetItem(['All','-1'])
        self.all_folder.setIcon(0,diropen_icon)
        self.libtree.addTopLevelItem(self.all_folder)

        self.needsreview_folder=QtWidgets.QTreeWidgetItem(['Needs Review','-2'])
        self.needsreview_folder.setIcon(0,needsreview_icon)
        self.libtree.addTopLevelItem(self.needsreview_folder)

        self.trash_folder=QtWidgets.QTreeWidgetItem(['Trash','-3'])
        self.trash_folder.setIcon(0,trash_icon)
        self.libtree.addTopLevelItem(self.trash_folder)

        self.sys_folders=[self.all_folder,self.needsreview_folder,self.trash_folder]

        #-------------Get all level 1 folders-------------
        folders1=[(vv[0],kk) for kk,vv in self.folder_dict.items() if\
                vv[1] in ['-1',]]
        folders1.sort()

        #------------------Add separator------------------
        separator=QtWidgets.QTreeWidgetItem([' ',None])
        separator.setFlags(Qt.NoItemFlags)
        self.libtree.addTopLevelItem(separator)
        h_line=getHLine(None)
        self.libtree.setItemWidget(separator,0,h_line)

        #------------Add folders from database------------
        for fnameii,idii in folders1:
            addFolder(self.libtree,idii,self.folder_dict)

        #---------------Add folders in trash---------------
        #self.libtree._trashed_folder_ids=sqlitedb.getTrashedFolders(self.folder_dict)
        #self.libtree._trashed_folder_ids=[kk for kk,vv in self.folder_dict.items()\
                #if vv[1]=='-3']
        trashed_folders=[(self.folder_dict[kk][0], kk) for kk in \
                self._trashed_folder_ids]
        print('# <loadLibTree>: trashed_folder_ids',self._trashed_folder_ids)
        print('# <loadLibTree>: trashed_folders',trashed_folders)

        for fnameii,idii in trashed_folders:
            addFolder(self.trash_folder,idii,self.folder_dict)

        orphan_docs=sqlitedb.findOrphanDocs2(self.db)
        self._orphan_doc_ids=orphan_docs

        #self.libtree.itemChanged.connect(self.addNewFolderToDict, Qt.QueuedConnection)
        self.libtree.itemDoubleClicked.connect(self.renameFolder)
        self.libtree.add_doc_to_folder_signal.connect(self.addDocToFolder)

        self.sortFolders()
        self.libtree.setCurrentItem(self.all_folder)

        self.changed_doc_ids=[] # store ids of changed docs, for auto save

        return



    def loadDocTable(self,folder=None,docids=None,sortidx=None,sel_row=None):
        '''Load doc table given folder'''

        tablemodel=self.doc_table.model()

        hh=self.doc_table.horizontalHeader()

        print('# <loadDocTable>: load table %s. sort indicator section=%s. sort order=%s'\
                %(folder, hh.sortIndicatorSection(), hh.sortIndicatorOrder()))
        self.logger.info('load table %s. sort indicator section=%s. sort order=%s'\
                %(folder, hh.sortIndicatorSection(), hh.sortIndicatorOrder()))

        #-----------Get list of doc ids to load-----------
        if docids is None:

            # load All folder
            if folder is None:
                docids=self.meta_dict.keys()

                print('# <loadDocTable>: NO before difference orphan docs: %d'\
                        %len(docids))
                self.logger.info('NO before difference orphan docs: %d'\
                        %len(docids))

                docids=list(set(docids).difference(self._orphan_doc_ids))

                print('# <loadDocTable>: NO after difference orphan docs: %d'\
                        %len(docids))
                self.logger.info('NO after difference orphan docs: %d'\
                        %len(docids))

            elif folder is not None and folder[0]=='All' and folder[1]=='-1':
                docids=self.meta_dict.keys()
            else:
                folderid=folder[1]
                print('# <loadDocTable>: folderid=',folderid, len(self.folder_data[folderid]))
                docids=self.folder_data[folderid]

        data=prepareDocs(self.meta_dict,docids)
        tablemodel.arraydata=data

        if sortidx is not None and sortidx in range(tablemodel.columnCount(None)):
            print('# <loadDocTable>: sort idx=%s' %sortidx)
            self.logger.info('sort idx=%s' %sortidx)

            tablemodel.sort(sortidx,Qt.AscendingOrder)

        print('# <loadDocTable>: len(data)=%d' %len(data))
        self.logger.info('len(data)=%d' %len(data))

        #------------Load meta data on 1st row------------
        if len(data)>0:
            self.enableMetaTab()
            if sel_row is not None:
                #self.doc_table.selectRow(0)
            #else:
                self.doc_table.selectRow(sel_row)
                current_row=self.doc_table.currentIndex().row()
                docid=self._current_doc

                print('# <loadDocTable>: current_row=%s, docid=%s'\
                        %(current_row, docid))
                self.logger.info('current_row=%s, docid=%s'\
                        %(current_row, docid))
                self.selDoc(self.doc_table.currentIndex(),None)
        else:
            # clear meta tab
            self.clearMetaTab()

        #self.doc_table.viewport().update()
        tablemodel.layoutChanged.emit()


    def loadMetaTab(self,docid=None):

        print('# <loadMetaTab>: docid=%s' %docid)
        self.logger.info('docid=%s' %docid)

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

            if fii in ['authors_l','abstract','tags_l','keywords_l']:
                if self.t_meta.fold_dict[fii]:
                    self._current_meta_dict[fii].foldText()


        return




    def loadBibTab(self,docid=None):
        print('# <loadBibTab>: docid=%s' %docid)
        self.logger.info('docid=%s' %docid)
        if docid is None:
            return

        metaii=self.meta_dict[docid]
        omit_keys=self.settings.value('export/bib/omit_fields', [], str)
        if isinstance(omit_keys,str) and omit_keys=='':
            omit_keys=[]
        text=bibparse.metaDictToBib(0,metaii,omit_keys)[2]

        self.bib_textedit.setText(text)

        return


    def loadNoteTab(self,docid=None):
        print('# <loadNoteTab>: docid=%s' %docid)
        self.logger.info('docid=%s' %docid)
        if docid is None:
            return

        noteii=self.meta_dict[docid]['notes']

        print('# <loadNoteTab>: noteii=%s' %noteii)
        self.logger.info('noteii=%s' %noteii)

        self.note_textedit.clear()
        self.note_textedit.setText(noteii)
        return



