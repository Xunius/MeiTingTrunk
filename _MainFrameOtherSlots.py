from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot



class MainFrameOtherSlots:


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

        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

        current_folder=self._current_folder
        if current_folder:
            folder,folderid=current_folder

            # TODO: keep a record of previous sortidx?
            if folder=='All' and folderid=='-1':
                self.loadDocTable(None,sortidx=4,sel_row=0)
            else:
                self.loadDocTable((folder,folderid),sortidx=4,sel_row=0)
            self.doc_table.selectRow(0)


        return

    def clearDuplicateButtonClicked(self):

        if self.duplicate_result_frame.isVisible():
            self.duplicate_result_frame.setVisible(False)

        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

            current_folder=self._current_folder
            if current_folder:
                folder,folderid=current_folder

                # TODO: keep a record of previous sortidx?
                if folder=='All' and folderid=='-1':
                    self.loadDocTable(None,sortidx=4,sel_row=0)
                else:
                    self.loadDocTable((folder,folderid),sortidx=4,sel_row=0)
                self.doc_table.selectRow(0)




    def searchBarClicked(self):
        print('search term:', self.search_bar.text())

    def copyBibButtonClicked(self):
        self.bib_textedit.selectAll()
        self.bib_textedit.copy()


    def clearData(self):

        self.clearMetaTab()
        self.doc_table.model().arraydata=[]
        self.libtree.clear()
        self.filter_item_list.clear()

        self.add_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.duplicate_check_button.setEnabled(False)

        print('# <clearData>: Data cleared.')
        self.logger.info('Data cleared.')
