from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5 import QtWidgets


class MainFrameMetaTabSlots:

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

        self.confirm_review_frame.setVisible(False)

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



