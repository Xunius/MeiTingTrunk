from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
from lib import sqlitedb


class MainFrameFilterListSlots:

    #######################################################################
    #                          Filter list slots                          #
    #######################################################################

    @pyqtSlot(QtWidgets.QListWidgetItem)
    def filterItemClicked(self,item):

        self.logger.info('Clicked filter item.text() = %s' %item.text())

        filter_type=self.filter_type_combbox.currentText()
        filter_text=item.text()
        current_folder=self._current_folder
        if current_folder:
            folderid=current_folder[1]

            filter_docids=sqlitedb.filterDocs(self.meta_dict,self.folder_data,
                    filter_type,filter_text,folderid)

            if len(filter_docids)>0:
                self.loadDocTable(None,filter_docids,sortidx=4,sel_row=0)

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

        # remove duplicate frame
        self.clearDuplicateButtonClicked()

        # remove search result frame
        self.clearSearchResButtonClicked()

        sel=self.filter_type_combbox.currentText()
        current_folder=self._current_folder

        self.logger.info('Filter type combobox select = %s' %sel)

        if current_folder:

            self.logger.info('current_folder = %s, folderid_d = %s'\
                    %(current_folder[0], current_folder[1]))

            #---------------Get items in folder---------------
            foldername,folderid=current_folder
            if folderid=='-1':
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




