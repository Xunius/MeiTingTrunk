'''
Contains a few functions manipulating the meta tab.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from PyQt5.QtCore import pyqtSlot


class MainFrameMetaTabSlots:

    #######################################################################
    #                            Meta tab slots                           #
    #######################################################################

    def clearMetaTab(self):

        for kk,vv in self._current_meta_dict.items():
            if kk=='files_l':
                self.t_meta.delFileField()
            else:
                vv.clear()
                vv.setReadOnly(True)

        for tii in [self.note_textedit, self.bib_textedit]:
            tii.clear()
            tii.setReadOnly(True)

        self.confirm_review_frame.setVisible(False)

        self.logger.debug('Meta tab cleared.')

        return


    def enableMetaTab(self):

        for kk,vv in self._current_meta_dict.items():
            if kk!='files_l':
                vv.setReadOnly(False)

        for tii in [self.note_textedit, ]:
            tii.setReadOnly(False)

        return


    @pyqtSlot()
    def confirmReviewButtonClicked(self):
        """Confirm meta data of a doc is correct

        This involves:
            * set DocMeta['confirmed']='true'
            * hide self.confirm_reivew_frame.
            * update current doc table
            * remove docid from the Needs Review folder (id='-2')
        """

        docid=self._current_doc

        self.meta_dict[docid]['confirmed']='true'

        self.logger.debug("doc id = %s. meta_dict[docid]['confirmed'] = %s"\
                %(docid, self.meta_dict[docid]['confirmed']))

        self.confirm_review_frame.setVisible(False)
        idx=self.doc_table.currentIndex()
        self.doc_table.model().dataChanged.emit(idx,idx)

        # del doc from needs review folder
        if docid in self.folder_data['-2']:
            self.folder_data['-2'].remove(docid)

        self.loadDocTable(folder=self._current_folder,sortidx=None,
                sel_row=idx.row())

        return


