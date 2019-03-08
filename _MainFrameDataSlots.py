from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QBrush
from queue import Queue
from lib import sqlitedb
from lib import widgets
from lib.tools import WorkerThread



class MainFrameDataSlots:

    #######################################################################
    #                      Meta data update functions                      #
    #######################################################################


    def threadedFuncCall2(self,func,joblist,show_message='',max_threads=4,
            get_results=False,close_on_finish=True,progressbar_style='classic'):

        thread_run_dialog=widgets.ThreadRunDialog(func,joblist,
                show_message,max_threads,get_results,close_on_finish,
                progressbar_style,parent=self)
        #thread_run_dialog.exec_()
        if get_results:
            #print('# <threadedFuncCall2>: results',thread_run_dialog.results)
            return thread_run_dialog.results
        else:
            return






    #######################################################################
    #                      Meta data update functions                      #
    #######################################################################

    def updateTabelData(self,docid,meta_dict,field_list=None):

        if docid is None:

            newid=max(self.meta_dict.keys())+1

            # update folder_data
            foldername,folderid=self._current_folder
            if folderid not in ['-1', '-2', '-3']:
                self.folder_data[folderid].append(newid)

                if (folderid, foldername) not in meta_dict['folders_l']:
                    meta_dict['folders_l'].append((folderid,foldername))
                    print('# <updateTabelData>: Add new doc to folder %s. meta_dict["folders_l"]=%s' %(foldername, meta_dict['folders_l']))
                    self.logger.info('Add new doc to folder %s. meta_dict["folders_l"]=%s' %(foldername, meta_dict['folders_l']))

            # update meta_dict
            print('# <updateTabelData>: Add new doc. Given id=%s' %newid)
            self.logger.info('Add new doc. Given id=%s' %newid)
            docid=newid

            self.meta_dict[newid]=meta_dict
            self.loadDocTable(docids=self._current_docids+[newid,],sel_row=None)
            self.doc_table.scrollToBottom()
            self.doc_table.selectRow(self.doc_table.model().rowCount(None)-1)

        else:
            if docid in self.meta_dict:
                print('# <updateTabelData>: Updating existing doc. docid=%s' %docid)
                self.logger.info('Updating existing doc. docid=%s' %docid)

                for kk in field_list:
                    if kk=='authors_l':
                        self.meta_dict[docid]['firstNames_l']=meta_dict['firstNames_l']
                        self.meta_dict[docid]['lastName_l']=meta_dict['lastName_l']
                    else:
                        self.meta_dict[docid][kk]=meta_dict[kk]
            else:
                print('wtf?')
                self.meta_dict[docid]=meta_dict

            self.loadDocTable(docids=self._current_docids,
                    sel_row=self.doc_table.currentIndex().row())


        #self.saveToDatabase(docid)
        self.changed_doc_ids.append(docid)

        return

    @pyqtSlot(sqlitedb.DocMeta)
    def updateByDOI(self,meta_dict):
        docid=self._current_doc
        print('# <updateByDOI>: Update doc %s' %docid)
        self.logger.info('Update doc %s' %docid)

        if docid:
            self.meta_dict[docid]=meta_dict
            self.loadDocTable(docids=self._current_docids,
                    sel_row=self.doc_table.currentIndex().row())
        return



    def updateNotes(self,docid,note_text):
        if docid is None:
            return

        self.meta_dict[docid]['notes']=note_text
        print('# <updateNotes>: New notes for docid=%s: %s' %(docid,note_text))
        self.logger.info('New notes for docid=%s: %s' %(docid,note_text))

        self.changed_doc_ids.append(docid)

        return


    @pyqtSlot(int,str)
    def addDocToFolder(self,docid,folderid):

        print('# <addDocToFolder>: docid=%s, folderid=%s' %(docid,folderid))
        self.logger.info('docid=%s, folderid=%s' %(docid,folderid))

        docfolders=self.meta_dict[docid]['folders_l']
        # note folderid here is an int
        newfolder=(int(folderid), self.folder_dict[folderid][0])
        if newfolder not in docfolders:
            docfolders.append(newfolder)
            self.meta_dict[docid]['folders_l']=docfolders

        if docid not in self.folder_data[folderid]:
            self.folder_data[folderid].append(docid)

        print('# <addDocToFolder>: Updated meta_dict["folders_l"]=%s' %self.meta_dict[docid]['folders_l'])
        self.logger.info('Updated meta_dict["folders_l"]=%s' %self.meta_dict[docid]['folders_l'])

        print('# <addDocToFolder>: Updated folder_data=%s' %self.folder_data[folderid],
                type(self.folder_data[folderid][0]))
        self.logger.info('Updated folder_data=%s' %self.folder_data[folderid])

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




    def saveToDatabase(self,docid):

        print('# <saveToDatabase>: Saving folders to database.')
        self.logger.info('Saving folders to database')

        #----------------Save folders first----------------
        sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                #self.settings.value('saving/storage_folder'))
                self.settings.value('saving/current_lib_folder'))

        sqlitedb.metaDictToDatabase(self.db,docid,self.meta_dict[docid],
                #self.settings.value('saving/storage_folder'),
                self.settings.value('saving/current_lib_folder'),
                self.settings.value('saving/rename_files'))

        if docid in self.changed_doc_ids:
            self.changed_doc_ids.remove(docid)

        return

    def autoSaveToDatabase(self):
        from datetime import datetime
        mtime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        print('# <autoSaveToDatabase>: Auto save called. %s' %mtime)
        self.logger.info('Auto save called. %s' %mtime)

        for ii in self.changed_doc_ids:
            print('# <autoSaveToDatabase>: Save doc %s' %ii)
            self.logger.info('Save doc %s' %ii)

        self.changed_doc_ids=[]
        self.settings.sync()

        return


    def createFailFolder(self,show_text,docids):
        self.clear_filter_label.setText('Failed tasks in %s' %show_text)
        self.clear_filter_frame.setVisible(True)
        self.loadDocTable(docids=docids)

        return





