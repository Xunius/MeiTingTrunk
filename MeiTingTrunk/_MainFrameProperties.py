'''
Defines getters for the current states of various widgets.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from .lib import sqlitedb


class MainFrameProperties:

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
                self.logger.critical('_current_doc: current row > row number. current_row = %s, len(self._tabledata) = %d' %(current_row, len(self._tabledata)))
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

    @property
    def _orphan_doc_ids(self):
        if hasattr(self,'meta_dict'):
            return [kk for kk in self.meta_dict if self.meta_dict[kk]['deletionPending']=='true']
