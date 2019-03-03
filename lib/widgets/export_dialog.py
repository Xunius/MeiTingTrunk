import os
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
from ..tools import getHLine, createFolderTree, iterTreeWidgetItems

LOGGER=logging.getLogger('default_logger')




class ExportDialog(QtWidgets.QDialog):
    def __init__(self,settings,parent):

        super(ExportDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(800,600)
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

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)



    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):

        item_text=item.text()
        print('# <cateSelected>: item.text()=%s' %item_text)

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
        va.addWidget(getHLine(self))

        return scroll, va


    def createOmitKeyGroup(self):

        grid=QtWidgets.QGridLayout()

        self.groupbox=QtWidgets.QGroupBox('Omit these fields in the exported bib entry.')
        self.groupbox.setCheckable(True)

        omittable_keys=[
            'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
            'lastName_l', 'pend_delete', 'folders_l', 'type', 'id',
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
        self.copyfile_settings={}


        #---------------Fold choice section---------------
        va.addWidget(getHLine())

        label=QtWidgets.QLabel('''
        Choose folders to export documents. <br/>
        This will copy documents (e.g. PDFs) from the
        <span style="font:bold;">"Collections"</span>
        folder to a separate folder under <span style="font:bold;">"%s"</span>
        ''' %self.settings.value('/saving/storage_folder',str))
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        va.addWidget(label)

        # create folder list
        if self.parent.is_loaded:
            # What if database if empty

            folder_dict=self.parent.main_frame.folder_dict
            self.folder_tree=createFolderTree(folder_dict,self)
            va.addWidget(self.folder_tree)

        va.addWidget(getHLine())

        do_button=QtWidgets.QPushButton('Export')
        do_button.clicked.connect(self.doExportFiles)

        va.addWidget(do_button,0, Qt.AlignLeft)

        return scroll



    def loadExportBibOptions(self):

        scroll,va=self.createFrame('Export to bibtex')
        self.bib_settings={}

        #--------------Export manner section--------------
        groupbox=QtWidgets.QGroupBox('Export documents')
        va2=QtWidgets.QVBoxLayout()
        groupbox.setLayout(va2)

        choices=['All in one', 'Per folder', 'Per document']
        for ii in choices:
            radioii=QtWidgets.QRadioButton(ii)
            if ii=='Per folder':
                radioii.setChecked(True)
            radioii.toggled.connect(lambda on: self.bibExportMannerChanged(on,groupbox))
            va2.addWidget(radioii)

        va.addWidget(groupbox)

        #----------------Omit keys section----------------
        self.groupbox=self.createOmitKeyGroup()
        va.addWidget(self.groupbox)

        va.addWidget(getHLine())

        do_button=QtWidgets.QPushButton('Export')
        do_button.clicked.connect(self.doBibExport)

        va.addWidget(do_button,0, Qt.AlignLeft)

        return scroll


    def bibExportMannerChanged(self,on,groupbox):

        for box in groupbox.findChildren(QtWidgets.QRadioButton):
            if box.isChecked():
                choice=box.text()
                break

        self.bib_settings['manner']=choice
        print('# <bibExportMannerChanged>: choice',choice,on,self.bib_settings)
        return


    def omitKeyChanged(self,on):
        self.bib_settings['omit_keys']=self.getOmitKeys()
        print('# <omitKeyChanged>: omit keys=',self.bib_settings['omit_keys'])
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

        self.bib_settings['omit_keys']=omit_keys
        print('# <omitKeyChanged>: omit keys=',self.bib_settings['omit_keys'])

        return

    def getOmitKeys(self):

        omit_keys=[]

        for box in self.groupbox.findChildren(QtWidgets.QCheckBox):
            if box.isChecked():
                omit_keys.append(box.text())

        return omit_keys



    def loadExportRISOptions(self):

        scroll,va=self.createFrame('Export to RIS')

        return scroll

    def loadExportZoteroOptions(self):

        scroll,va=self.createFrame('Export to Zotero')

        return scroll

    def doExportFiles(self):
        folder_dict=self.parent.main_frame.folder_dict
        folder_data=self.parent.main_frame.folder_data
        meta_dict=self.parent.main_frame.meta_dict
        storage_folder=self.settings.value('saving/storage_folder',str)

        if not os.path.exists(storage_folder):
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setWindowTitle('Critical Error!')
            msg.setText("Can not find storage folder.")
            msg.setInformativeText("I can't find the storage folder at %s. Data lost."\
                    %storage_folder)
            msg.exec_()
            return

        job_list=[] # (jobid, source_path, target_path)
        for item in iterTreeWidgetItems(self.folder_tree):
            if item.checkState(0):
                folderid=item.data(1,0)
                docids=folder_data[folderid]
                print('# <doExportFiles>: choose folder', item.data(0,0),
                        item.data(1,0))
                tree=sqlitedb.getFolderTree(folder_dict,folderid)[1]
                print('# <doExportFiles>: tree',tree)
                print('# <doExportFiles>: docids in folder', docids)

                folderii=os.path.join(storage_folder,tree)
                if not os.path.exists(folderii):
                    os.makedirs(folderii)
                    print('# <doExportFiles>: Create folder %s' %folderii)
                    LOGGER.info('Create folder %s' %folderii)

                for idii in docids:
                    if meta_dict[idii]['has_file']:
                        for fjj in meta_dict[idii]['files_l']:
                            filenamejj=sqlitedb.renameFile(fjj,meta_dict[idii])
                            newfjj=os.path.join(folderii,filenamejj)
                            job_list.append((len(job_list), fjj, newfjj))

        import time
        def copyFunc(jobid,s,t):
            try:
                #shutil.copy(s,t)
                rec=0
                result=None
            except:
                rec=1
                result=None
            
            time.sleep(0.5)
            return rec,jobid,result

        if len(job_list)>0:
            self.parent.main_frame.threadedFuncCall2(
                    copyFunc,job_list,'Exporting Files...')

        return



    def doBibExport(self):
        return

