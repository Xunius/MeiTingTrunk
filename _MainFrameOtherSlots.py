from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread


class SettingsThread(QThread):
    def __init__(self, setting, key, value):
        super(SettingsThread,self).__init__()
        self.setting=setting
        self.key=key
        self.value=value

    def __del__(self):
        self.wait()

    def run(self):
        self.setting.setValue(self.key,self.value)
        print('# <SettingsThread>: Settings saved.')
        return



class MainFrameOtherSlots:


    view_change_sig=pyqtSignal(str,bool)


    #######################################################################
    #                             Other slots                             #
    #######################################################################

    def foldFilterButtonClicked(self):

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        if self.filter_list.isVisible():
            self.filter_list.setVisible(False)
            self.fold_filter_button.setArrowType(Qt.UpArrow)
            self.view_change_sig.emit('Toggle Filter List',False)
            if 'Toggle Filter List' in show_widgets:
                show_widgets.remove('Toggle Filter List')
        else:
            self.filter_list.setVisible(True)
            self.fold_filter_button.setArrowType(Qt.DownArrow)
            self.view_change_sig.emit('Toggle Filter List',True)
            if 'Toggle Filter List' not in show_widgets:
                show_widgets.append('Toggle Filter List')

        self.setting_thread=SettingsThread(self.settings,
                'view/show_widgets', show_widgets)
        self.setting_thread.start()

        return


    @pyqtSlot()
    def foldTabButtonClicked(self):

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        if self.tab_pane.isVisible():
            self.tab_pane.setVisible(False)
            self.fold_tab_button.setArrowType(Qt.LeftArrow)
            self.view_change_sig.emit('Toggle Tab Pane',False)

            if 'Toggle Tab Pane' in show_widgets:
                show_widgets.remove('Toggle Tab Pane')
        else:
            self.tab_pane.setVisible(True)
            self.fold_tab_button.setArrowType(Qt.RightArrow)
            self.view_change_sig.emit('Toggle Tab Pane',True)

            if 'Toggle Tab Pane' not in show_widgets:
                show_widgets.append('Toggle Tab Pane')

            has_tab=False

            for kk, vv in self.tab_dict.items():
                tabii, tabnameii=vv
                idx=self.tabs.indexOf(tabii)
                if idx!=-1:
                    has_tab=True

            if not has_tab:
                for kk, vv in self.tab_dict.items():
                    tabii, tabnameii=vv
                    idx=self.tabs.indexOf(tabii)
                    self.tabs.addTab(tabii, tabnameii)
                    self.view_change_sig.emit(kk,True)

                    if kk not in show_widgets:
                        show_widgets.append(kk)

                if 'Toggle Tab Pane' not in show_widgets:
                    show_widgets.append('Toggle Tab Pane')

        self.setting_thread=SettingsThread(self.settings,
                'view/show_widgets', show_widgets)
        self.setting_thread.start()

        return

    @pyqtSlot()
    def metaTabViewChange(self, view_name='Toggle Tab Pane'):

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        has_tab=False
        for kk, vv in self.tab_dict.items():

            tabii, tabnameii=vv
            idx=self.tabs.indexOf(tabii)
            if idx==-1:
                if view_name==kk:
                    tabii.setVisible(True)
                    self.tabs.addTab(tabii, tabnameii)
                    self.view_change_sig.emit(view_name,True)
                    has_tab=True
                    if view_name not in show_widgets:
                        show_widgets.append(view_name)
            else:
                if view_name==kk:
                    tabii.setVisible(False)
                    self.tabs.removeTab(idx)
                    self.view_change_sig.emit(view_name,False)
                    if view_name in show_widgets:
                        show_widgets.remove(view_name)
                else:
                    has_tab=True

        print('# <metaTabViewChange>: has_tab:',has_tab)
        if not has_tab:
            self.tab_pane.setVisible(False)
            self.fold_tab_button.setArrowType(Qt.LeftArrow)
            self.view_change_sig.emit('Toggle Tab Pane',False)
            if 'Toggle Tab Pane' in show_widgets:
                show_widgets.remove('Toggle Tab Pane')
        else:
            self.tab_pane.setVisible(True)
            self.fold_tab_button.setArrowType(Qt.RightArrow)
            self.view_change_sig.emit('Toggle Tab Pane',True)
            if 'Toggle Tab Pane' not in show_widgets:
                show_widgets.append('Toggle Tab Pane')

        self.setting_thread=SettingsThread(self.settings,
                'view/show_widgets', show_widgets)
        self.setting_thread.start()

        return

    def statusbarViewChange(self):
        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        if self.status_bar.isVisible():
            self.status_bar.setVisible(False)
            if 'Toggle Status bar' in show_widgets:
                show_widgets.remove('Toggle Status bar')
        else:
            self.status_bar.setVisible(True)
            if 'Toggle Status bar' not in show_widgets:
                show_widgets.append('Toggle status bar')

        self.setting_thread=SettingsThread(self.settings,
                'view/show_widgets', show_widgets)
        self.setting_thread.start()

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

        return

    def clearSearchResButtonClicked(self):

        if self.search_res_frame.isVisible():
            self.search_res_frame.setVisible(False)

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



    def copyBibButtonClicked(self):
        self.bib_textedit.selectAll()
        self.bib_textedit.copy()


    def clearData(self):

        self.clearMetaTab()
        self.doc_table.model().arraydata=[]
        self.doc_table.model().layoutChanged.emit()
        self.libtree.clear()
        self.filter_item_list.clear()

        self.add_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.duplicate_check_button.setEnabled(False)

        print('# <clearData>: Data cleared.')
        self.logger.info('Data cleared.')
