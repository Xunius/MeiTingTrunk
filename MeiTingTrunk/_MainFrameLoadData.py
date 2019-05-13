'''
This part contains methods that load data into various widgets.

loadLibTree() is the major entrance of data loaded from sqlite.
Folders in the library are created in this function, plus 3 preserved system
folders:

    * All (id='-1'): contains all documents. It can not contain sub-folders.
                     You can not add directly new documents in All, new
                     documents can only be added in a normal folder.
    * Needs Review (id='-2'): contains all documents whose 'confirmed' dict
                              value is 'false', indicating an uncertain
                              state in the correctness of meta-data. Needs-
                              review docs are shown in bold font in the doc
                              table. This folder doesn't contain sub-folders,
                              and does not accept new documents.
    * Trash (id='-3'): can contain sub-folders. Folders in trash, or any other
                       folder inside trash are identified by the _trashed_folder_ids
                       property (see _MainFrameProperties.py). As a document
                       can appear in more than one folder, trashing a folder
                       doesn't necessarily trash a doc within, as the doc may
                       still appear in one or more normal folders. Docs that
                       ONLY appear in folders in _trashed_folder_ids are
                       labelled "orphan" and is denoted by the 'deletionPending'==
                       'true' dict value. Orphan docs won't appear in the All
                       folder. Orphan docs are restored by moving into any
                       normal folder, when their 'deletionPending' value is set
                       to 'false'. Orphan docs that don't belong to any folder
                       inside Trash will be put to the Trash folder itself.

System folders are static in that they can't be deleted, renamed or changed in
the order of appearance. They are not saved in the sqlite database file, but
created everytime a library is loaded.

Folders are defined by their name (str) and id (str). Folder info in a library
is stored in the dict self.folder_dict, with the following structure:

    self.folder_dict[folder_id_in_str] = (folder_name, parentid)

Parentid of a folder points to the id of the parent. All top level folders,
including <Needs Review> and <Trash>, have a parentid of '-1'. <All> folder
doesn't have parentid.  Currently there is no limit on the level of folder
nesting.

Valid characters for folder names include alphanumeric characters plus '_' and
'-'. Name confliction is allowed as long as they don't share the same parent.

A <Default> (id='0') folder is created in a newly created library.

After the folder tree creation, the <All> folder is selected.

Upon selecting a folder, documents within, not including those in its
sub-folders, are loaded into the doc table. This is done in loadDocTable(). Ids
of docs in a folder are stored in the dict self.folder_data, with the following
format:

    self.folder_data[folder_id_in_str] = [doc1_id_in_int, doc2_id_in_int, ...]

Meanwhile, each doc stores a list of folder ids that the doc resides in:

    self.meta_dict[docid_in_int]['folders_l'] = [folder1_id_in_int,
                                                 folder2_id_in_int,
                                                 ...
                                                 ]
    forgive me about the int/str type confusion, I haven't got time to fix this.

Upon calling loadDocTable(), a row is selected (if there is any).

Upon selecting a row in doc table, the meta data tab is populated, in
loadMetaTab(). Note texts are loaded in loadNoteTab(), and bibtex string
is loaded in loadBibTab().


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import subprocess
import glob
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from .lib import sqlitedb
from .lib import bibparse
from .lib.tools import getHLine, hasPoppler, hasImageMagic



def addFolder(parent, folderid, folder_dict):
    """Add a new folder item to the folder tree

    Args:
        parent (QTreeWidgetItem or QTreeWidget): parent widget/item onto which
                                                 to add a new folder.
        folderid (str): id of the new folder.
        folder_dict (dict): dict containing folder defs:

            self.folder_dict[folder_id_in_str] = (folder_name, parentid)

    Sub-folders are added by recursive calls of the function.
    """

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


def prepareDocs(meta_dict, docids):
    """Format meta data of docs for display in the doc table

    Args:
        meta_dict (dict): dict containing meta data of all docs in the library,
                          in the format:

                    self.meta_dict[doc_id_in_int] = DocMeta

                          where DocMeta is a dict. See sqlitedb.py for details.
        docids (list): list of doc ids to format.

    Returns: data (list): each element is a list containing 10 fields of a
                          doc to feed into the doc_table QTableView.
    """

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


    #######################################################################
    #                       Load data into widgets                        #
    #######################################################################


    def loadLibTree(self, db, meta_dict, folder_data, folder_dict):
        """Load folders in a library

        Args:
            db (sqlite connection): sqlite connection of the library.
            meta_dict (dict): dict containing meta data of all docs in the library.
            folder_data (dict): dict containing doc ids in a folder.
            folder_dict (dict): dict containing folder info in the library.
        """

        self.db=db
        self.meta_dict=meta_dict
        self.folder_data=folder_data
        self.folder_dict=folder_dict
        #self.inv_folder_dict={v[0]:k for k,v in self.folder_dict.items()}

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
                vv[1]=='-1']
        folders1.sort()

        self.logger.debug('Level 1 folder ids = %s' %folders1)

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
        trashed_folders=[(vv[0],kk) for kk,vv in self.folder_dict.items()\
                if vv[1]=='-3']

        self.logger.debug('Ids of folders in Trash = %s' %trashed_folders)

        for fnameii,idii in trashed_folders:
            addFolder(self.trash_folder,idii,self.folder_dict)

        self.sortFolders()
        self.libtree.setCurrentItem(self.all_folder)

        self.changed_doc_ids=[] # store ids of changed docs
        self.changed_folder_ids=[] # store ids of changed folders

        return


    def loadDocTable(self, folder=None, docids=None, sortidx=None,
            sortorder=0, sel_row=None):
        """Load the doc table

        Kwargs:
            folder ((fname_in_str, fid_in_str) or None ): if tuple, load docs
                   within the folder. If None, load the <All> folder.
            docids (list or None): if list, a list of doc ids to load. If None,
                                   load according to the <folder> arg.
            sortidx (int or None or False): int in [0,9], index of the column
                to sort the table. If None, use current sortidx.
                If False, don't do sorting. This last case is for adding new
                docs to the folder and I want the new docs to appear at the
                end, so scrolling to and selecting them is easier, and makes
                sense.
            sortorder (int): sort order, Qt.AscendingOrder (0), or
                             Qt.DescendingOrder (1), order to sort the columns.
                           with.
            sel_row (int or None): index of the row to select after loading.
                                   If None, don't change selection.
        """

        tablemodel=self.doc_table.model()
        hh=self.doc_table.horizontalHeader()

        self.logger.debug('Load folder = %s. sort indicator section = %s. sort order = %s'\
                %(folder, hh.sortIndicatorSection(), hh.sortIndicatorOrder()))

        #-----------Get list of doc ids to load-----------
        if docids is None:

            # load All folder
            if folder is None or folder[1]=='-1':
                docids=self.meta_dict.keys()

                self.logger.debug('NO. before subtracting orphan docs: %d'\
                        %len(docids))

                docids=list(set(docids).difference(self._orphan_doc_ids))

                self.logger.info('NO. after subtracting orphan docs: %d'\
                        %len(docids))

            # load any other folder
            else:
                docids=self.folder_data[folder[1]]
                self.logger.info('NO. in folder %s = %d' %(folder[1], len(docids)))

        #-------------Format data to table rows-------------
        data=prepareDocs(self.meta_dict,docids)
        tablemodel.arraydata=data

        #--------------------Sort rows--------------------
        if sortidx != False:
            if sortidx is None:
                sortidx=self.settings.value('view/sortidx', 4, type=int)
                sortorder=self.settings.value('view/sortorder', 0, type=int)
                tablemodel.sort(sortidx, sortorder)
            else:
                #if sortidx is not None and sortidx in range(tablemodel.columnCount(None)):
                self.logger.info('sort idx = %s. sortorder = %s' %(sortidx, sortorder))
                tablemodel.sort(sortidx, sortorder)

        if len(data)>0:
            self.enableMetaTab()

            #-------------------Select a given row-------------------
            if sel_row is not None:
                current_row=self.doc_table.currentIndex().row()
                docid=self._current_doc

                self.logger.info('Selected row = %s, docid = %s'\
                        %(current_row, docid))

                self.doc_table.selectRow(sel_row)

                if current_row==sel_row:
                    self.logger.info('@@@@@row not change. force sel doc')
                    self.selDoc(self.doc_table.currentIndex(),None)
            else:
                self.selDoc(self.doc_table.currentIndex(),None)

            self.status_bar.showMessage('%d rows' %len(data))
        else:
            #------------------Clear meta tab------------------
            self.logger.info('No data to be loaded. Clear meta tab.')
            self.removeFolderHighlights()
            self.clearMetaTab()

        #self.doc_table.viewport().update()
        tablemodel.layoutChanged.emit()

        return


    def loadMetaTab(self, docid=None):
        """Load meta data tab of a doc

        Kwargs:
            docid (int or None): if int, the id of the doc to load.
        """

        self.logger.info('docid = %s' %docid)

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

        #---------Loop through fields in meta tab---------
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
                    # fold long texts
                    self._current_meta_dict[fii].foldText()

        return


    def loadBibTab(self, docid=None):
        """Load bibtex tab of a doc

        Kwargs:
            docid (int or None): if int, the id of the doc to load.
        """

        self.logger.info('docid = %s' %docid)
        if docid is None:
            return

        metaii=self.meta_dict[docid]
        omit_keys=self.settings.value('export/bib/omit_fields', [], str)
        if isinstance(omit_keys,str) and omit_keys=='':
            omit_keys=[]

        path_type=self.settings.value('export/bib/path_type',type=str)
        if path_type=='absolute':
            prefix=self.settings.value('saving/current_lib_folder',type=str)
        elif path_type=='relative':
            prefix=''

        text=bibparse.metaDictToBib(0,metaii,omit_keys,prefix)[2]
        self.bib_textedit.setText(text)

        return


    def loadNoteTab(self, docid=None):
        """Load note tab of a doc

        Kwargs:
            docid (int or None): if int, the id of the doc to load.
        """

        self.logger.info('docid = %s' %docid)
        if docid is None:
            return

        noteii=self.meta_dict[docid]['notes']

        self.logger.debug('noteii = %s' %noteii)
        self.note_textedit.clear()
        self.note_textedit.setText(noteii)

        return


    def loadPDFThumbnail(self, docid=None):
        """Load a thumbnail of the 1st page of a pdf

        Kwargs:
            docid (int or None): if int, the id of the doc to load.
        """

        if docid is None:
            return

        files=self.meta_dict[docid]['files_l']
        if len(files)==0:
            self.pdf_viewer.clearLayout()
            return

        dpi=self.settings.value('view/thumbnail_dpi', type=str)

        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        cache_folder=os.path.join(lib_folder, '_cache')

        # get the 1st file
        filepath=files[0]
        filepath=os.path.join(lib_folder, filepath)
        filename=os.path.split(filepath)[1]
        outfile=os.path.join(cache_folder, '%s-%s' %(filename, dpi))

        self.logger.debug('outfile = %s' %outfile)

        # prefer poppler over imagemagic
        # NO, imagemagic for some reason doesn't allow pdf conversion, so f it.
        if hasPoppler():
            cmd=['pdftoppm', filepath, outfile, '-jpeg',
                    '-r', dpi]
        else:
            #if hasImageMagic():
                #cmd=['convert', '-density', dpi, filepath, outfile]
            #else:
                #return
            label=QtWidgets.QLabel()
            poppler='https://poppler.freedesktop.org/'
            label.setText('''Requires 'poppler' to create previews. See <a href="%s"> %s </a> for installation details
            ''' %(poppler, poppler))
            label.setTextFormat(Qt.RichText)
            label.setWordWrap(True)
            self.pdf_viewer.clearLayout()
            self.pdf_viewer.layout.addWidget(label)
            return

        #-----------Try finding saved thumbnail-----------
        glob_paths=os.path.join(cache_folder, '%s-%s*.jpg' %(filename, dpi))
        outfiles=glob.glob(glob_paths)
        if len(outfiles)>0:
            outfiles.sort()
            tb_imgs=(QtGui.QPixmap(fii) for fii in outfiles)
            self.logger.debug('Using cached thumbnail.')
        else:
            try:
                proc=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                proc.wait()
            except:
                return
            else:
                outfiles=glob.glob(glob_paths)
                outfiles.sort()
                tb_imgs=(QtGui.QPixmap(fii) for fii in outfiles)
                self.logger.debug('Generate a new thumbnail.')

        #--------------------Add images--------------------
        self.pdf_viewer.clearLayout()
        for pii in tb_imgs:
            labelii=QtWidgets.QLabel(self)
            labelii.setPixmap(pii)
            self.pdf_viewer.layout.addWidget(labelii)

        return



