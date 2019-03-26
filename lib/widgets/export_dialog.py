import os
import shutil
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt,\
        pyqtSignal,\
        pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialogButtonBox
import resources
from .. import sqlitedb
from .. import bibparse
from .. import risparse
from ..tools import getHLine, createFolderTree, iterTreeWidgetItems, autoRename
from .threadrun_dialog import ThreadRunDialog
from .fail_dialog import FailDialog

LOGGER=logging.getLogger(__name__)




class ExportDialog(QtWidgets.QDialog):
    def __init__(self,settings,parent):

        super(ExportDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(900,600)
        self.setWindowTitle('Bulk Export')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Choose Export Type')
        title_label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(title_label)

        v_layout.addLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        #self.list.setSizePolicy(getXMinYExpandSizePolicy())
        self.cate_list.setMaximumWidth(200)
        h_layout.addWidget(self.cate_list)

        #self.cate_list.setStyleSheet('''
            #QListWidget::item { border: 0px solid rgb(235,235,240);
            #font: 14px;
            #background-color: rgb(205,205,245);
            #color: rgb(100,10,13) };
            #background-color: rgb(230,234,235);
            #''')

        self.cate_list.addItems(['Copy Document Files', 'Export to bibtex',
            'Export to RIS', 'Export to Zotero'])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        if self.parent.is_loaded:
            # What if database if empty

            folder_dict=self.parent.main_frame.folder_dict
            self.folder_tree=createFolderTree(folder_dict,self)
        else:
            self.folder_tree=None

        self.buttons=QDialogButtonBox(QDialogButtonBox.Close,
            Qt.Horizontal, self)
        self.export_button=self.buttons.addButton('Export',
                QDialogButtonBox.ApplyRole)

        #self.buttons.accepted.connect(self.doExport)
        self.export_button.clicked.connect(self.doExport)
        self.buttons.rejected.connect(self.reject)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)



    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):

        item_text=item.text()
        LOGGER.debug('item.text() = %s' %item_text)

        if self.content_vlayout.count()>1:
            self.content_vlayout.removeWidget(self.content_frame)

        if item_text=='Copy Document Files':
            self.content_frame=self.loadCopyFileOptions()
        elif item_text=='Export to bibtex':
            self.content_frame=self.loadExportBibOptions()
        elif item_text=='Export to RIS':
            self.content_frame=self.loadExportRISOptions()
        elif item_text=='Export to Zotero':
            self.content_frame=self.loadExportZoteroOptions()

        self.content_vlayout.insertWidget(0,self.content_frame)

        return


    def createFrame(self,title):

        frame=QtWidgets.QWidget(self)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        va=QtWidgets.QVBoxLayout()
        frame.setLayout(va)
        va.setSpacing(int(va.spacing()*2))

        label=QtWidgets.QLabel(title)
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        va.addWidget(label)
        #va.addWidget(getHLine(self))

        return scroll, va


    def clearFolderTreeState(self):

        for item in iterTreeWidgetItems(self.folder_tree):
            item.setCheckState(0,False)

        return


    def createOmitKeyGroup(self):

        grid=QtWidgets.QGridLayout()

        self.groupbox=QtWidgets.QGroupBox('Omit these fields in the exported bib entry.')
        self.groupbox.setCheckable(True)

        omittable_keys=[
            'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
            'lastName_l', 'deletionPending', 'folders_l', 'type', 'id',
            'abstract', 'advisor', 'month', 'language', 'confirmed',
            'deletionPending', 'note', 'publicLawNumber', 'sections',
            'reviewedArticle', 'userType', 'shortTitle', 'sourceType',
            'code', 'codeNumber', 'codeSection', 'codeVolume', 'citationKey',
            'day', 'dateAccessed', 'internationalAuthor', 'internationalUserType',
            'internationalTitle', 'internationalNumber', 'genre', 'lastUpdate',
            'legalStatus', 'length', 'medium'
            ]
        omittable_keys.sort()

        omit_keys=self.settings.value('export/bib/omit_fields', [], str)
        # likely something wrong with qt. When list is set empty by
        # settings.setValue('key',[]), on the NEXT load of the program,
        # settings.value('export/bib/omit_fields', [], str) gives ''
        if isinstance(omit_keys,str) and omit_keys=='':
            omit_keys=[]

        for ii,keyii in enumerate(omittable_keys):
            checkboxii=QtWidgets.QCheckBox(keyii,self.groupbox)
            if keyii in omit_keys:
                checkboxii.setChecked(True)
            checkboxii.stateChanged.connect(self.omitKeyChanged)
            grid.addWidget(checkboxii,int(ii/3),ii%3)

        self.groupbox.toggled.connect(lambda on: self.omitKeysGroupChanged(on,
            self.groupbox))

        self.groupbox.setLayout(grid)


        return self.groupbox


    def loadCopyFileOptions(self):

        scroll,va=self.createFrame('Copy Document Files')
        self.current_task='copy_file'

        #---------------Folder choice section---------------
        label=QtWidgets.QLabel('''
        Choose folders to export documents. <br/>
        This will copy documents (e.g. PDFs) from the
        <span style="font:bold;">"_collections"</span>
        folder to a separate folder under <span style="font:bold;">"%s/"</span>
        ''' %self.settings.value('saving/current_lib_folder',str))
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        va.addWidget(label)

        if self.folder_tree:
            self.clearFolderTreeState()
            va.addWidget(self.folder_tree)
        else:
            va.addWidget(QtWidgets.QLabel('Library empty'))
            self.export_button.setEnabled(False)

        return scroll


    def loadExportBibOptions(self):

        scroll,va=self.createFrame('Export to bibtex')
        self.bib_settings={}

        self.current_task='bib_export'

        #--------------Folder choice section--------------
        label=QtWidgets.QLabel('Choose folder(s) to export.')
        va.addWidget(label)

        if self.folder_tree:
            self.folder_tree.setMinimumHeight(300)
            self.clearFolderTreeState()
            va.addWidget(self.folder_tree)
        else:
            va.addWidget(QtWidgets.QLabel('Library empty'))
            self.export_button.setEnabled(False)

        #--------------Export manner section--------------
        self.radio_groupbox=QtWidgets.QGroupBox('Saving manner')
        ha2=QtWidgets.QHBoxLayout()
        self.radio_groupbox.setLayout(ha2)

        choices=['All in one', 'Per folder', 'Per document']
        for ii in choices:
            radioii=QtWidgets.QRadioButton(ii)
            if ii=='Per folder':
                radioii.setChecked(True)
            ha2.addWidget(radioii)

        va.addWidget(self.radio_groupbox)

        #----------------Omit keys section----------------
        self.omitkey_groupbox=self.createOmitKeyGroup()
        va.addWidget(self.omitkey_groupbox)

        return scroll


    def getExportManner(self):

        for box in self.radio_groupbox.findChildren(QtWidgets.QRadioButton):
            if box.isChecked():
                choice=box.text()
                break

        return choice


    def omitKeyChanged(self,on):

        self.bib_settings['omit_keys']=self.getOmitKeys()
        LOGGER.debug('omit keys = %s' %self.bib_settings['omit_keys'])

        return


    def omitKeysGroupChanged(self, on, groupbox):

        omit_keys=[]

        for box in groupbox.findChildren(QtWidgets.QCheckBox):
            box.stateChanged.disconnect()
            box.setChecked(on)
            box.setEnabled(True)
            box.stateChanged.connect(self.omitKeyChanged)
            if box.isChecked():
                omit_keys.append(box.text())

        return


    def getOmitKeys(self):

        omit_keys=[]

        for box in self.omitkey_groupbox.findChildren(QtWidgets.QCheckBox):
            if box.isChecked():
                omit_keys.append(box.text())

        return omit_keys


    def loadExportRISOptions(self):

        scroll,va=self.createFrame('Export to RIS')
        self.current_task='ris_export'

        self.ris_settings={}

        #--------------Folder choice section--------------
        label=QtWidgets.QLabel('Choose folder(s) to export.')
        va.addWidget(label)

        if self.folder_tree:
            self.folder_tree.setMinimumHeight(300)
            self.clearFolderTreeState()
            va.addWidget(self.folder_tree)
        else:
            va.addWidget(QtWidgets.QLabel('Library empty'))
            self.export_button.setEnabled(False)

        #--------------Export manner section--------------
        self.radio_groupbox=QtWidgets.QGroupBox('Saving manner')
        ha2=QtWidgets.QHBoxLayout()
        self.radio_groupbox.setLayout(ha2)

        choices=['All in one', 'Per folder', 'Per document']
        for ii in choices:
            radioii=QtWidgets.QRadioButton(ii)
            if ii=='Per folder':
                radioii.setChecked(True)
            ha2.addWidget(radioii)

        va.addWidget(self.radio_groupbox)

        return scroll


    def loadExportZoteroOptions(self):

        scroll,va=self.createFrame('Export to Zotero')
        self.current_task='zotero_export'

        return scroll


    def doExportFiles(self):

        folder_dict=self.parent.main_frame.folder_dict
        folder_data=self.parent.main_frame.folder_data
        meta_dict=self.parent.main_frame.meta_dict
        #storage_folder=self.settings.value('saving/storage_folder',str)
        lib_folder=self.settings.value('saving/current_lib_folder',str)

        if not os.path.exists(lib_folder):
            LOGGER.warning('Cant find storage folder (%s) when exporting files.'\
                    %lib_folder)

            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setWindowTitle('Critical Error!')
            msg.setText("Can not find storage folder.")
            msg.setInformativeText("I can't find the storage folder at %s. Data lost."\
                    %lib_folder)
            msg.exec_()
            return

        folders=[]
        for item in iterTreeWidgetItems(self.folder_tree):
            if item.checkState(0):
                folders.append(item)
        if len(folders)==0:
            self.popUpChooseFolder()
            return

        LOGGER.debug('Current lib folder = %s' %lib_folder)

        job_list=[] # (jobid, source_path, target_path)
        for item in folders:
            folderid=item.data(1,0)

            docids=folder_data[folderid]

            tree=sqlitedb.getFolderTree(folder_dict,folderid)[1]

            LOGGER.debug('Process folder %s, id = %s, tree = %s'\
                    %(item.data(0,0), item.data(1,0), tree))

            folderii=os.path.join(lib_folder,tree)
            if not os.path.exists(folderii):
                os.makedirs(folderii)
                LOGGER.info('Create folder %s' %folderii)

            for idii in docids:
                if meta_dict[idii]['has_file']:
                    for fjj in meta_dict[idii]['files_l']:
                        filenamejj=sqlitedb.renameFile(fjj,meta_dict[idii])
                        newfjj=os.path.join(folderii,filenamejj)
                        # prepend lib_folder to rel file path
                        oldjj=os.path.join(lib_folder,fjj)
                        job_list.append((len(job_list), oldjj, newfjj))

        #import time
        def copyFunc(jobid,s,t):
            try:
                shutil.copy(s,t)
                LOGGER.debug('Copied file %s to %s' %(s,t))
                rec=0
                result=None
            except:
                LOGGER.exception('Failed to copy %s to %s' %(s,t))
                rec=1
                result=None

            #time.sleep(0.5)
            return rec,jobid,result

        if len(job_list)>0:

            thread_run_dialog=ThreadRunDialog(copyFunc,job_list,
                    show_message='Exporting Files...',max_threads=4,
                    get_results=False,
                    close_on_finish=False,
                    progressbar_style='classic',parent=self)

        return


    def doBibExport(self):

        #---------------Get selected folders---------------
        folders=[]
        for item in iterTreeWidgetItems(self.folder_tree):
            if item.checkState(0):
                folderid=item.data(1,0)
                foldername=item.data(0,0)
                folders.append((foldername, folderid))
        if len(folders)==0:
            self.popUpChooseFolder()
            return

        #------------Popup for saving location------------
        manner=self.getExportManner()
        if manner=='All in one':
            default_path='bibtex_export.bib'
            fname = QtWidgets.QFileDialog.getSaveFileName(self,
                    'Save Citaitons to bib File',
                    default_path,
                    "bib Files (*.bib);; All files (*)")[0]
        else:
            fname=QtWidgets.QFileDialog.getExistingDirectory(self,
                'Choose a folder to save bibtex files')

        if not fname:
            return

        LOGGER.info('Selected folders = %s' %folders)
        LOGGER.info('Saving manner = %s' %manner)
        LOGGER.info('Chosen bib file = %s' %fname)

        #-----------------Prepare job list-----------------
        folder_data=self.parent.main_frame.folder_data
        meta_dict=self.parent.main_frame.meta_dict
        omit_keys=self.getOmitKeys()

        LOGGER.debug('omit keys = %s' %omit_keys)

        #-----------------Create job list-----------------
        job_list=[]
        citationkeys=[]
        docs=[]

        if manner in ['All in one', 'Per document']:

            for folderii in folders:
                docs.extend(folder_data[folderii[1]])

            docs=list(set(docs))
            n=0

            for docii in docs:
                cii=meta_dict[docii]['citationkey']
                if cii=='':
                    cii=str(docii)
                citationkeys.append(cii)
                job_list.append((n, meta_dict[docii], omit_keys))
                n+=1

            #---------------Sort by citationkey---------------
            if manner=='All in one':
                job_list=[x for _,x in sorted(zip(citationkeys,job_list))]
                citationkeys=sorted(citationkeys)

        elif manner=='Per folder':

            n=0
            for foldernameii,fidii in folders:

                jobsii=[]
                #----------------Loop through docs----------------
                docids=folder_data[fidii]
                citationkeysii=[]
                for docii in docids:
                    if docii in docs:
                        # remove duplicates
                        continue

                    cii=meta_dict[docii]['citationkey']
                    if cii=='':
                        cii=str(docii)
                    citationkeysii.append(cii)
                    jobsii.append((n, meta_dict[docii], omit_keys))
                    n+=1
                    docs.append(docii)

                #---------------Sort by citationkey---------------
                jobsii=[x for _,x in sorted(zip(citationkeysii,jobsii))]
                citationkeysii=sorted(citationkeysii)
                job_list.extend(jobsii)
                citationkeys.extend(citationkeysii)

        #------------------Run in thread------------------
        thread_run_dialog=ThreadRunDialog(bibparse.metaDictToBib, job_list,
                show_message='Processing...', max_threads=1, get_results=False,
                close_on_finish=False,
                progressbar_style='classic',
                post_process_func=self.saveBib,
                post_process_func_args=(folders, manner, fname, folder_data,
                    meta_dict,citationkeys),
                parent=self)

        return


    def saveBib(self,results,folders,manner,fname,folder_data,meta_dict,citationkeys):

        faillist=[]

        if manner=='All in one':
            text=''
            for recii,jobii,textii,docii in results:
                if recii==0:
                    text=text+textii+'\n'
                elif recii==1:
                    faillist.append(docii)

            with open(fname,'w') as fout:
                fout.write(text)

            LOGGER.info('Saved combined outputs to file %s' %fname)

        elif manner=='Per document':
            for recii,jobii,textii,docii in results:
                if recii==0:
                    citationkey=citationkeys[jobii]
                    fnameii='%s.bib' %citationkey
                    fnameii=os.path.join(fname,fnameii)
                    fnameii=autoRename(fnameii)

                    with open(fnameii,'w') as fout:
                        fout.write(textii)

                    LOGGER.info('Saved per doc output to file %s' %fnameii)

                elif recii==1:
                    faillist.append(docii)

        elif manner=='Per folder':

            #-------------Prepare result counting-------------
            folder_counts={}
            folder_results={}
            for foldernameii,fidii in folders:
                folder_results[fidii]=[]
                folder_counts[fidii]=0

            for recii,jobii,textii,docii in results:
                if recii==1:
                    faillist.append(docii)

                for fnamejj,fidjj in folders:
                    if docii in folder_data[fidjj]:
                        folder_counts[fidjj]+=1
                        if recii==0:
                            folder_results[fidjj].append(textii)

                        if folder_counts[fidjj]==len(folder_data[fidjj]):
                            LOGGER.debug('folder %s got all data. Save.' %fnamejj)

                            fnamejj=os.path.join(fname,'%s.bib' %fnamejj)
                            text='\n'.join(folder_results[fidjj])

                            with open(fnamejj,'w') as fout:
                                fout.write(text)

                            LOGGER.info('Saved per folder output to file %s' %fnamejj)

        #-----------------Show failed jobs-----------------
        if len(faillist)>0:

            fail_entries=[]
            for docii in faillist:
                metaii=meta_dict[docii]
                entryii='* %s_%s_%s' %(', '.join(metaii['authors_l']),
                        metaii['year'],
                        metaii['title'])

                LOGGER.warning('Failed export job: %s' %entryii)

                fail_entries.append(entryii)

            '''
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Error')
            msg.setText('Oopsie.')
            msg.setInformativeText('Failed to export some entries')
            msg.setDetailedText('\n'.join(fail_entries))
            msg.exec_()
            '''
            msg=FailDialog()
            msg.setText('Oopsie.')
            msg.setInformativeText('Failed to export some entries.')
            msg.setDetailedText('\n'.join(fail_entries))
            msg.create_fail_summary.connect(lambda:\
                    self.parent.main_frame.createFailFolder('bibtex export',
                        faillist))
            msg.exec_()

        return


    def doRISExport(self):

        #---------------Get selected folders---------------
        folders=[]
        for item in iterTreeWidgetItems(self.folder_tree):
            if item.checkState(0):
                folderid=item.data(1,0)
                foldername=item.data(0,0)
                folders.append((foldername, folderid))
        if len(folders)==0:
            self.popUpChooseFolder()
            return

        #------------Popup for saving location------------
        manner=self.getExportManner()
        if manner=='All in one':
            default_path='RIS_export.ris'
            fname = QtWidgets.QFileDialog.getSaveFileName(self,
                    'Save Citaitons to RIS File',
                    default_path,
                    "ris Files (*.ris);; All files (*)")[0]
        else:
            fname=QtWidgets.QFileDialog.getExistingDirectory(self,
                'Choose a folder to save RIS files')

        if not fname:
            return

        LOGGER.info('Selected folders = %s' %folders)
        LOGGER.info('Saving manner = %s' %manner)
        LOGGER.info('Chosen ris file = %s' %fname)

        #-----------------Prepare job list-----------------
        folder_data=self.parent.main_frame.folder_data
        meta_dict=self.parent.main_frame.meta_dict

        #-----------------Create job list-----------------
        job_list=[]
        citationkeys=[]
        docs=[]

        if manner in ['All in one', 'Per document']:

            for folderii in folders:
                docs.extend(folder_data[folderii[1]])

            docs=list(set(docs))
            n=0
            for docii in docs:
                cii=meta_dict[docii]['citationkey']
                if cii=='':
                    cii=str(docii)
                citationkeys.append(cii)
                job_list.append((n, meta_dict[docii]))
                n+=1

            #---------------Sort by citationkey---------------
            if manner=='All in one':
                job_list=[x for _,x in sorted(zip(citationkeys,job_list))]
                citationkeys=sorted(citationkeys)

        elif manner=='Per folder':

            n=0
            for foldernameii,fidii in folders:

                jobsii=[]
                #----------------Loop through docs----------------
                docids=folder_data[fidii]
                citationkeysii=[]
                for docii in docids:
                    if docii in docs:
                        # remove duplicates
                        continue

                    cii=meta_dict[docii]['citationkey']
                    if cii=='':
                        cii=str(docii)
                    citationkeysii.append(cii)
                    jobsii.append((n, meta_dict[docii]))
                    n+=1
                    docs.append(docii)

                #---------------Sort by citationkey---------------
                jobsii=[x for _,x in sorted(zip(citationkeysii,jobsii))]
                citationkeysii=sorted(citationkeysii)
                job_list.extend(jobsii)
                citationkeys.extend(citationkeysii)

        #------------------Run in thread------------------
        thread_run_dialog=ThreadRunDialog(risparse.metaDictToRIS, job_list,
                show_message='Processing...', max_threads=1, get_results=False,
                close_on_finish=False,
                progressbar_style='classic',
                post_process_func=self.saveRIS,
                post_process_func_args=(folders, manner, fname, folder_data,
                    meta_dict,citationkeys),
                parent=self)

        return


    def saveRIS(self,results,folders,manner,fname,folder_data,meta_dict,citationkeys):
        faillist=[]

        if manner=='All in one':
            text=''
            for recii,jobii,textii,docii in results:
                if recii==0:
                    text=text+textii
                elif recii==1:
                    faillist.append(docii)

            with open(fname,'w') as fout:
                fout.write(text)

            LOGGER.info('Saved combined outputs to file %s' %fname)

        elif manner=='Per document':
            for recii,jobii,textii,docii in results:
                if recii==0:
                    citationkey=citationkeys[jobii]
                    fnameii='%s.ris' %citationkey
                    fnameii=os.path.join(fname,fnameii)
                    fnameii=autoRename(fnameii)

                    with open(fnameii,'w') as fout:
                        fout.write(textii)

                    LOGGER.info('Saved per doc output to file %s' %fnameii)

                elif recii==1:
                    faillist.append(docii)

        elif manner=='Per folder':

            #-------------Prepare result counting-------------
            folder_counts={}
            folder_results={}
            for foldernameii,fidii in folders:
                folder_results[fidii]=[]
                folder_counts[fidii]=0

            for recii,jobii,textii,docii in results:
                if recii==1:
                    faillist.append(docii)

                for fnamejj,fidjj in folders:
                    if docii in folder_data[fidjj]:
                        folder_counts[fidjj]+=1
                        if recii==0:
                            folder_results[fidjj].append(textii)

                        # save if folder got all its doc processed, even if failed
                        if folder_counts[fidjj]==len(folder_data[fidjj]):

                            fnamejj=os.path.join(fname,'%s.ris' %fnamejj)
                            text='\n'.join(folder_results[fidjj])

                            with open(fnamejj,'w') as fout:
                                fout.write(text)

                            LOGGER.info('Folder %s got all data. Saved.'\
                                    %fnamejj)

        #-----------------Show failed jobs-----------------
        if len(faillist)>0:
            fail_entries=[]
            for docii in faillist:
                metaii=meta_dict[docii]
                entryii='* %s_%s_%s' %(', '.join(metaii['authors_l']),
                        metaii['year'],
                        metaii['title'])
                fail_entries.append(entryii)

                LOGGER.warning('Failed export job %s' %entryii)

            msg=FailDialog()
            msg.setText('Oopsie.')
            msg.setInformativeText('Failed to export some entries.')
            msg.setDetailedText('\n'.join(fail_entries))
            msg.create_fail_summary.connect(lambda:\
                    self.parent.main_frame.createFailFolder('RIS export',
                        faillist))
            msg.exec_()

        return



    def doExport(self):

        LOGGER.info('task = %s' %self.current_task)

        if self.current_task=='copy_file':
            self.doExportFiles()
        elif self.current_task=='bib_export':
            self.doBibExport()
        elif self.current_task=='ris_export':
            self.doRISExport()
        elif self.current_task=='zotero_export':
            pass

        return


    def popUpChooseFolder(self):

        msg=QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle('Input Needed')
        msg.setText("Choose at least one folder to process.")
        msg.exec_()

        return

