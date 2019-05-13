'''
This part contains some functions dealing with hide/show if widgets, clipboard
copying and clearing data of widgets.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import glob
import resource
import subprocess
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QTimer
from .lib.tools import hasPoppler


class SettingsThread(QThread):
    '''A separate thread for writing settings'''
    def __init__(self, setting, key, value):
        super(SettingsThread,self).__init__()
        self.setting=setting
        self.key=key
        self.value=value

    def __del__(self):
        self.wait()

    def run(self):
        self.setting.setValue(self.key,self.value)
        return



class MainFrameOtherSlots:


    view_change_sig=pyqtSignal(str,bool)

    #######################################################################
    #                             Other slots                             #
    #######################################################################

    @pyqtSlot()
    def foldFilterButtonClicked(self):
        '''Hide/show the filter list widget

        This is a slot to the clicked signal of the fold button underneath
        the folder tree.

        It is also called when user toggle view changes in the View menu,
        see ViewChangeTriggered() in _MainWindow.py
        '''

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

        # write change to settings
        self.setting_thread=SettingsThread(self.settings,
                'view/show_widgets', show_widgets)
        self.setting_thread.start()

        return


    @pyqtSlot()
    def foldTabButtonClicked(self):
        '''Hide/show the tab pane

        This is a slot to the clicked signal of the fold button to the right
        of the doc table.

        It is also called when user toggle view changes in the View menu,
        see ViewChangeTriggered() in _MainWindow.py

        Individual tabs in the tab pane can also be toggled. If all tabs
        are toggled off, hide the tab pane as well.
        '''

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        self.logger.debug('Before show_widgets = %s' %show_widgets)

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

            # check if any tab page still visible
            has_tab=False

            for kk, vv in self.tab_dict.items():
                tabii, tabnameii=vv
                idx=self.tabs.indexOf(tabii)
                if idx!=-1:
                    # -1 idx means not there
                    has_tab=True

            # if no tab page is still visible, remove tab pane as well.
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

        self.logger.debug('After show_widgets = %s' %show_widgets)

        return


    def metaTabViewChange(self, view_name='Toggle Tab Pane'):
        '''Hide/show the meta data tab in the tab pane

        It is called when user toggle view changes in the View menu,
        see ViewChangeTriggered() in _MainWindow.py
        '''

        show_widgets=self.settings.value('view/show_widgets',[],str)
        if isinstance(show_widgets,str) and show_widgets=='':
            show_widgets=[]

        self.logger.debug('Before show_widgets = %s' %show_widgets)

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

        self.logger.debug('has_tab = %s' %has_tab)

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

        self.logger.debug('After show_widgets = %s' %show_widgets)

        return


    def statusbarViewChange(self):
        '''Hide/show the status bar in the main_frame

        It is called when user toggle view changes in the View menu,
        see ViewChangeTriggered() in _MainWindow.py
        '''

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
                show_widgets.append('Toggle Status bar')

        self.setting_thread=SettingsThread(self.settings,
                'view/show_widgets', show_widgets)
        self.setting_thread.start()

        return


    @pyqtSlot()
    def clearDuplicateButtonClicked(self):
        '''Hide the duplicate result header frame above the doc table

        This is a slot to the clicked signal of the clear_duplicate_button
        shown in the duplicate_result_frame.

        It is also called in filterTypeCombboxChange(), which is called
        on selecting a folder. Therefore selecting/switching to a folder
        will automatically hide the duplicate_result_frame.
        '''

        if self.duplicate_result_frame.isVisible():
            self.duplicate_result_frame.setVisible(False)

        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

            current_folder=self._current_folder
            if current_folder:
                folder,folderid=current_folder

                # TODO: keep a record of previous sortidx?
                if folder=='All' and folderid=='-1':
                    self.loadDocTable(None,sortidx=None,sel_row=0)
                else:
                    self.loadDocTable((folder,folderid),sortidx=None,sel_row=0)
                #self.doc_table.selectRow(0)

        return


    @pyqtSlot()
    def clearSearchResButtonClicked(self):
        '''Hide the search result header frame above the doc table

        This is a slot to the clicked signal of the clear_searchres_button
        shown in the search_res_frame.

        It is also called in filterTypeCombboxChange(), which is called
        on selecting a folder. Therefore selecting/switching to a folder
        will automatically hide the search_res_frame.
        '''

        if self.search_res_frame.isVisible():
            self.search_res_frame.setVisible(False)

        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

            current_folder=self._current_folder
            if current_folder:
                folder,folderid=current_folder

                # TODO: keep a record of previous sortidx?
                if folder=='All' and folderid=='-1':
                    self.loadDocTable(None,sortidx=None,sel_row=0)
                else:
                    self.loadDocTable((folder,folderid),sortidx=None,sel_row=0)
                #self.doc_table.selectRow(0)

        return


    @pyqtSlot()
    def copyBibButtonClicked(self):
        '''Copy texts in bibtex tab to clipboard'''

        self.bib_textedit.selectAll()
        self.bib_textedit.copy()

        return


    def clearData(self):
        '''Clear data from meta tab, doc table, folder tree and filter list

        This is called when closing a library.
        '''

        self.clearMetaTab()
        # hide duplicate frame and search frame.
        if self.duplicate_result_frame.isVisible():
            self.duplicate_result_frame.setVisible(False)
        if self.search_res_frame.isVisible():
            self.search_res_frame.setVisible(False)
        if not self.doc_table.isVisible():
            self.doc_table.setVisible(True)

        self.doc_table.model().arraydata=[]
        self.doc_table.model().layoutChanged.emit()
        self.libtree.clear()
        self.filter_item_list.clear()

        self.add_button.setEnabled(False)
        self.add_folder_button.setEnabled(False)
        self.duplicate_check_button.setEnabled(False)

        self.logger.info('Data cleared.')

        return


    def createThumbnails(self):
        '''Create PDF thumbnails in the background.

        This is supposed to run in a separate thread when a library is opened,
        and stopped when a library is closed. See

        _MainWindow._openDatabase()
        _MainWindow.closeDatabaseTriggered()
        '''

        if not hasPoppler():
            return

        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        cache_folder=os.path.join(lib_folder, '_cache')
        file_folder=os.path.join(lib_folder, '_collections')
        dpi=self.settings.value('view/thumbnail_dpi', type=str)

        files=os.listdir(file_folder)

        def setlimits():
            # Set maximum CPU time to n second in child process,
            # after fork() but before exec()
            #print("Setting resource limit in child (pid %d)" % os.getpid())
            resource.setrlimit(resource.RLIMIT_CPU, (0.2, 0.3))

        def _createTN():

            if len(files)==0:
                return

            fii=files.pop()

            #-----------Try finding saved thumbnail-----------
            glob_paths=os.path.join(cache_folder, '%s-%s*.jpg' %(fii, dpi))
            outfiles=glob.glob(glob_paths)
            if len(outfiles)>0:
                # if exists, call itself after short delay
                QTimer.singleShot(5, lambda : _createTN())
                return

            pii=os.path.join(file_folder, fii)
            outfileii=os.path.join(cache_folder, '%s-%s' %(fii, dpi))
            cmd=['pdftoppm', pii, outfileii, '-jpeg', '-r', dpi]

            try:
                proc=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=setlimits)
                proc.wait()
            except Exception as e:
                self.logger.exception('e = %s' %e)
                # if fail, call itself after short delay
                QTimer.singleShot(5, lambda : _createTN())
                return
            else:
                self.logger.debug('Generated a new thumbnail for %s' %fii)
                # if success, call itself after longer delay
                QTimer.singleShot(4000, lambda : _createTN())
                return

        # stop on lib closing
        if not self.parent.is_loaded:
            return

        # the setlimits() doesn't seem to be enough, this is taking
        # too much resource and then fan goes crazy.
        # Can't use sleep which will block
        QTimer.singleShot(5, lambda : _createTN())

        return






