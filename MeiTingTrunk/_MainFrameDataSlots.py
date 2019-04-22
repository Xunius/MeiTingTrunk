'''
Handles data updating, including updates of the in-memory data dictionary from
editings in  the meta data tabs and from DOI querying; adding docs to folders,
and saving the in-memory data to sqlite database.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QBrush
from PyQt5 import QtWidgets
from .lib import sqlitedb
from .lib import widgets



class MainFrameDataSlots:


    def threadedFuncCall2(self,func,joblist,show_message='',max_threads=4,
            get_results=False,close_on_finish=True,progressbar_style='classic'):
        '''Call function in another thread.
        See threadrun_dialog.py for more details
        NOT in use any more.
        '''

        thread_run_dialog=widgets.ThreadRunDialog(func,joblist,
                show_message,max_threads,get_results,close_on_finish,
                progressbar_style,parent=self)
        thread_run_dialog.exec_()
        if get_results:
            return thread_run_dialog.results
        else:
            return



    #######################################################################
    #                      Meta data update functions                      #
    #######################################################################

    def updateTableData(self,docid,meta_dict,field_list=None):
        """Update the in-memory dictionary self.meta_dict

        Args:
            docid (int): id of doc to update.
            meta_dict (DocMeta dict): dict containing the updated meta data for
                                      doc with id = <docid>.
        Kwargs:
            field_list (None or list): if list of str, giving the keys in
                                       <meta_dict> that needs update.
                                       if None, adding a new doc (<docid> not in
                                       self.meta_dict).

        Returns:
            docid (int): id assigned to added doc. If <docid> was None, this
                         gives the id assigned to it. Otherwise it return
                         <docid>.
        """

        if docid is None:

            if len(self.meta_dict)==0:
                docid=1
            else:
                docid=max(self.meta_dict.keys())+1

            self.logger.info('Add new doc. Given id=%s' %docid)

            # update folder_data
            foldername,folderid=self._current_folder
            if folderid not in ['-1', '-2', '-3']:
                self.folder_data[folderid].append(docid)

                if (folderid, foldername) not in meta_dict['folders_l']:
                    meta_dict['folders_l'].append((folderid,foldername))
                    self.logger.debug('Add new doc to folder %s. meta_dict["folders_l"]=%s'\
                            %(foldername, meta_dict['folders_l']))

            # update meta_dict
            self.meta_dict[docid]=meta_dict
            meta_dict['id']=docid
            # add to needs review folder
            self.folder_data['-2'].append(docid)
            # scroll to and select row in doc table
            self.doc_table.scrollToBottom()
            self.loadDocTable(docids=self._current_docids+[docid,],
                    sel_row=None, sortidx=False)

            # use sortidx=False to signal don't do sorting. This is
            # for adding new docs to the folder and I want the new docs to
            # appear at the end, so scrolling to and selecting them is easier,
            # and makes sense.

            #xx=self.doc_table.model().rowCount(None)
            # NOTE that the below method may not work when table was empty before
            # adding, as I connected doc_table.currentChanged to selDoc.
            # When table was empty, the index for previous current isnt defined
            # UPDATE: never mind the above.
            self.doc_table.selectRow(self.doc_table.model().rowCount(None)-1)

        else:
            if docid in self.meta_dict:
                self.logger.info('Updating existing doc. docid=%s' %docid)

                for kk in field_list:
                    if kk=='authors_l':
                        self.meta_dict[docid]['firstNames_l']=meta_dict['firstNames_l']
                        self.meta_dict[docid]['lastName_l']=meta_dict['lastName_l']
                    else:
                        self.meta_dict[docid][kk]=meta_dict[kk]
            else:
                self.logger.debug('wtf?')

                self.meta_dict[docid]=meta_dict

            # reload doc table
            self.loadDocTable(docids=self._current_docids,
                    sel_row=self.doc_table.currentIndex().row())

        self.changed_doc_ids.append(docid)

        return docid


    @pyqtSlot(sqlitedb.DocMeta)
    def updateByDOI(self, meta_dict):
        """update in-memory dictionary self.meta_dict via doi query

        args:
            meta_dict (docmeta dict): new dict containing meta data from doi
                                      query.
        """

        docid=self._current_doc
        self.logger.info('Update doc %s by doi' %docid)

        if docid:
            self.meta_dict[docid]=meta_dict
            self.changed_doc_ids.append(docid)
            self.loadDocTable(docids=self._current_docids,
                    sel_row=self.doc_table.currentIndex().row())

        return


    @pyqtSlot()
    def updateNotes(self, docid, note_text):
        """update notes in the in-memory dictionary

        args:
            docid (int): id of doc to update.
            note_text (str): new note texts.
        """

        if docid is None:
            return

        self.meta_dict[docid]['notes']=note_text
        self.changed_doc_ids.append(docid)
        self.logger.info('New notes for docid=%s: %s' %(docid,note_text))

        return


    @pyqtSlot(int,str)
    def addDocToFolder(self, docid, folderid):
        """Add a doc to a folder

        Args:
            docid (int): id of doc.
            folderid (str): id of folder to accept doc.
        """

        self.logger.info('docid=%s, folderid=%s' %(docid,folderid))

        #----------Add folder to doc's folders_l----------
        docfolders=self.meta_dict[docid]['folders_l']
        # note folderid here is an int
        newfolder=(int(folderid), self.folder_dict[folderid][0])
        if newfolder not in docfolders:
            docfolders.append(newfolder)
            self.meta_dict[docid]['folders_l']=docfolders

        #-------------Add docid to folder_data-------------
        if docid not in self.folder_data[folderid]:
            self.folder_data[folderid].append(docid)

        self.logger.debug('Updated meta_dict["folders_l"] = %s'\
                %self.meta_dict[docid]['folders_l'])
        self.logger.debug('Updated folder_data = %s' %self.folder_data[folderid])

        #-------------Restoring a trashed doc-------------
        current_folderid=self._current_folder[1]
        trashed_folders=self._trashed_folder_ids+['-3']
        if current_folderid in trashed_folders and folderid not in trashed_folders:
            self.logger.info('Restoring a trashed doc.')
            self.logger.debug('Updated deletionPending = %s'\
                    %self.meta_dict[docid]['deletionPending'])
            self.meta_dict[docid]['deletionPending']=='false'

            # remove doc from current folder when restoring
            if docid in self.folder_data[current_folderid]:
                self.folder_data[current_folderid].remove(docid)
                self.loadDocTable(folder=self._current_folder,
                        sel_row=None,sortidx=None)

        # add highlight to folder
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        mii=self.libtree.findItems(folderid, Qt.MatchExactly | Qt.MatchRecursive,
                column=1)
        if len(mii)>0:
            for mjj in mii:
                mjj.setBackground(0, hi_color)

        self.changed_doc_ids.append(docid)


        return


    @pyqtSlot()
    def saveToDatabase(self):
        """Save in-memory data to sqlite file

        self.changed_folder_ids contains ids of folder to update.
        self.changed_doc_ids contains ids of docs to update.
        Clear these two after saving.
        """

        mtime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        self.logger.info('Save called. %s' %mtime)

        if len(self.changed_folder_ids)==0 and len(self.changed_doc_ids)==0:
            return

        # remove duplicates
        self.changed_folder_ids=list(set(self.changed_folder_ids))
        self.changed_doc_ids=list(set(self.changed_doc_ids))

        self.logger.debug('Folders to save: %s' %self.changed_folder_ids)
        self.logger.debug('Docs to save: %s' %self.changed_doc_ids)

        self.status_bar.setVisible(True)
        self.status_bar.showMessage('Saving. Please standby ...')
        # progressbar doesn't work in the main thread?
        self.progressbar.setVisible(True)
        self.progressbar.setMaximum(0)
        QtWidgets.QApplication.processEvents()

        #----------------Save folders first----------------
        if len(self.changed_folder_ids)>0:

            sqlitedb.saveFoldersToDatabase(self.db,
                    self.changed_folder_ids, self.folder_dict,
                    self.settings.value('saving/current_lib_folder'))

            self.changed_folder_ids=[]
            self.logger.info('Folder changes saved to database.')

        #--------------------Save docs--------------------
        any_reload_doc=False
        for docid in self.changed_doc_ids:
            self.logger.info('Saving doc %s' %docid)
            rec, reload_doc=sqlitedb.metaDictToDatabase(self.db, docid,
                    self.meta_dict,
                    self.meta_dict.get(docid),
                    self.settings.value('saving/current_lib_folder'),
                    self.settings.value('saving/rename_files', type=int),
                    self.settings.value('saving/file_move_manner', type=str)
                    )
            any_reload_doc=any_reload_doc or reload_doc

        self.changed_doc_ids=[]
        self.settings.sync()
        self.status_bar.clearMessage()
        self.progressbar.setVisible(False)

        self.logger.info('Saving completed.')

        #current_folder=self._current_folder
        current_doc_ids=self._current_docids
        #if any_reload_doc and current_folder is not None:
        if any_reload_doc and current_doc_ids:
            current_row=self.doc_table.currentIndex().row()
            self.logger.debug('Reloading doc table after save. current_row = %s' %(current_row))
            self.loadDocTable(docids=current_doc_ids, sortidx=None,
                    sel_row=current_row)


        return


    @pyqtSlot()
    def createFailFolder(self, show_text, docids):
        """Show in the doc table docs in a failed task

        Args:
            show_text (str): info texts to show in the label describing the task.
            docids (list): list of doc ids (int) to load in the doc table.

        NOTE: this is a misnomer, no folder is created. rename later
        """

        self.clear_filter_label.setText('Failed tasks in %s' %show_text)
        self.clear_filter_frame.setVisible(True)
        self.loadDocTable(docids=docids)

        return



    @pyqtSlot(sqlitedb.DocMeta)
    def addDocFromDuplicateMerge(self, meta_dict):

        docid=max(self.meta_dict.keys())+1
        self.logger.info('Add new doc. Given id=%s' %docid)

        # update folder_data
        folders=meta_dict['folders_l']
        for folderid, foldername in folders:
            self.folder_data[folderid].append(docid)

        # add to needs review folder
        self.folder_data['-2'].append(docid)

        # update meta_dict
        self.meta_dict[docid]=meta_dict

        self.changed_doc_ids.append(docid)

        msg=QtWidgets.QMessageBox()
        msg.resize(600,500)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Merge completed')
        msg.setText('                New document created.                  ')
        msg.setInformativeText('''
        New document has been created from duplicate merge, <br/>
        and added to folder(s): <br/>
        <br/>
            <span style="font: bold;"> %s </span>
        ''' %(', '.join([fii[1] for fii in folders])))
        msg.exec_()

        return


