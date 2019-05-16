'''
Dialog controlling creating zim notebook from library.

MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import re
from datetime import datetime
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialogButtonBox
from ..tools import getHLine, ZimNoteNotFoundError
from .threadrun_dialog import ThreadRunDialog
from .. import sqlitedb

LOGGER=logging.getLogger(__name__)


# invalid chars in zim note filename
FOLDER_NAME_SUB_PATTERN=re.compile(r'[\ ./\\?,:=!@#$%^&*+]')
# to replace consecutive underscores with one
COLLAPSE_UNDERSCORE=re.compile(r'_+')
# max length beyond which to use elided title
TITLE_LEN=60

# zim note book header?
ZIM_HOME_BASE='''[Notebook]
version=0.4
name=%s
interwiki=
home=Home
icon=
document_root=
shared=True
endofline=unix
disable_trash=False
profile=
'''

ZIM_HEADER_PATTERN=re.compile(r'^====== (.*?) ======(?:\n|\r\n?)^Created ',
        re.DOTALL | re.MULTILINE)



def getZimHeader(title):
    '''Create a zim note header

    Args:
        title (str): note title

    Returns:
        text (str): zim header
    '''

    tnow=datetime.today()
    tstr=datetime.strftime(tnow, '%A %d %B %Y')

    #text=\
            #'''Content-Type: text/x-zim-wiki
#Wiki-Format: zim 0.4
#
#====== %s ======
#Created %s
#''' %(title, tstr)
    text='''====== %s ======
Created %s
''' %(title, tstr)

    return text


def removeInvalidChar(text):

    new=re.sub(FOLDER_NAME_SUB_PATTERN, '_', text)
    new=re.sub(COLLAPSE_UNDERSCORE, '_', new)
    new=new.strip('_')

    return new


def createNote(folder, title, filename=None, contents=None, overwrite=False):

    # get note file path
    note_fname=filename or title
    note_fname=removeInvalidChar(note_fname)
    note_folder=os.path.join(folder, note_fname)
    note_path='%s.txt' %note_folder

    # create content folder
    if not os.path.exists(note_folder):
        os.makedirs(note_folder)

    if not overwrite and os.path.exists(note_path):
        return

    # fill in content
    if contents is not None:
        match=ZIM_HEADER_PATTERN.match(contents)
        if match:
            header=''
        else:
            header=getZimHeader(title)
    else:
        header=getZimHeader(title)
    print('# <createNote>: folder=', folder)
    print('# <createNote>: note_folder=', note_folder)
    print('# <createNote>: note_path=', note_path)
    with open(note_path, 'w') as fout:
        if len(header)>0:
            fout.write(header)
            fout.write('\n')
        if contents is not None:
            fout.write(contents)

    return note_path


def getFolderTree(folder_dict, folderid):
    """Get a str representation of a given folder in the folder tree

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        folderid (str): id of given folder.

    Returns:
        folderid (str): input folder id.
        folder (str): path of the given folder in the tree.
    """

    getFolderName=lambda folder_dict,id: removeInvalidChar(folder_dict[id][0])
    getParentId=lambda folder_dict,id: folder_dict[id][1]

    folder=getFolderName(folder_dict,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=str(getParentId(folder_dict,cid))
        if pid=='-1':
            break
        else:
            pfolder=getFolderName(folder_dict,pid)
            folder=os.path.join(pfolder,folder)
        cid=pid

    return folderid,folder


def getSubFolderStr(sub_ids, folder_dict, level):

    if level=='base':
        level_str=':'
    elif level=='sub':
        level_str='+'
    else:
        raise Exception("<level> not recognized.")

    sub_strs=[]
    for fii in sub_ids:
        snameii=folder_dict[fii][0]
        snameii=removeInvalidChar(snameii)
        sub_strs.append('[[%s%s]]\n' %(level_str, snameii))
    sub_strs.sort()
    sub_strs='\n'.join(sub_strs)

    return sub_strs


def createFolderNote(parent_folder, folderid, folder_dict, overwrite):

    if folderid=='-1':
        foldername='Home'
        sub_ids=[kk for kk,vv in folder_dict.items() if\
                vv[1]=='-1']

        filename='Home'
        line1='Notes created for library'
        sub_strs=getSubFolderStr(sub_ids, folder_dict, 'base')
        sub_strs=line1+'\n\n'+sub_strs
        p_folder=parent_folder

    else:
        foldername,parentid=folder_dict[folderid]
        filename=None
        sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
        sub_strs=getSubFolderStr(sub_ids, folder_dict, 'sub')
        p_folder=os.path.join(parent_folder, removeInvalidChar(foldername))

    print('# <createFolderNote>: folderid=', folderid, 'foldername=',foldername)

    texts='===== Sub-topics =====\n\n'
    texts2='\n\n===== Doc notes =====\n\n'
    createNote(parent_folder, foldername, filename=filename,
            contents=texts+sub_strs+texts2, overwrite=overwrite)

    if len(sub_ids)>0:
        for sii in sub_ids:
            createFolderNote(p_folder, sii, folder_dict, overwrite=overwrite)

    return



def createNoteTitle(meta):

    #citationkey=meta['citationkey']
    title=meta['title']
    if len(title)>TITLE_LEN:
        title=title[:TITLE_LEN]
    author=meta['lastName_l']
    if len(author)==0:
        author=''
    else:
        author=author[0]

    year=meta['year']

    notetitle='%s_%s_%s' %(author, year, title)
    notetitle=removeInvalidChar(notetitle)

    return notetitle


def createDocNote(zim_folder, meta_dict, docid, overwrite=False):

    notes_folder=os.path.join(zim_folder, 'all_notes')
    notetitle=createNoteTitle(meta_dict[docid])
    notes=meta_dict[docid]['notes']
    filenameii=str(docid)
    rec=createNote(notes_folder, notetitle, filename=filenameii,
            contents=notes, overwrite=overwrite)
    if rec is None:
        return 0
    else:
        return 1


def linkDocNote(zim_folder, meta_dict, folder_dict, folder_data, docid):

    if len(meta_dict[docid]['notes'])==0:
        return

    trashed_folders=sqlitedb.getTrashedFolders(folder_dict)
    notes_folder=os.path.join(zim_folder, 'all_notes')
    notepath=os.path.join(notes_folder, '%s.txt' %str(docid))

    if not os.path.exists(notepath):
        print('# <linkDocNote>: note file not found %s' %notepath)
        createDocNote(zim_folder, meta_dict, docid, overwrite=True)

    note_title=createNoteTitle(meta_dict[docid])
    folders=meta_dict[docid]['folders_l']

    for fidii, _ in folders:
        fidii=str(fidii)
        if fidii in trashed_folders:
            continue

        relpathii=getFolderTree(folder_dict, fidii)[1]
        target_folder=os.path.join(zim_folder, relpathii)

        pnote_file='%s.txt' %target_folder
        print('# <linkDocNotes>: pntoe_file', pnote_file)

        target_path=os.path.join(target_folder, '%s.txt' %note_title)
        if not os.path.exists(target_path):
            os.symlink(notepath, target_path)

        if os.path.exists(pnote_file):
            print('# <linkDocNotes>: found parent note!')
            with open(pnote_file, 'a') as fout:
                #fout.write('\n[[:all_notes:%s|%s]]\n' %(str(docid), note_title))
                fout.write('\n[[+%s]]\n' %(note_title))

    return



def locateZimNote(zim_folder, docid):

    notes_folder=os.path.join(zim_folder, 'all_notes')
    notepath=os.path.join(notes_folder, '%s.txt' %str(docid))

    if not os.path.exists(notepath):
        raise ZimNoteNotFoundError("Note for doc %s not found." %str(docid))

    return notepath


def readZimNote(zim_folder, docid):

    notepath=locateZimNote(zim_folder, docid)

    with open(notepath, 'r') as fin:
        lines=fin.read()

    print('# <readZimNote>: lines=', lines)

    return lines


def saveToZimNote(zim_folder, docid, text, overwrite=False):

    notes_folder=os.path.join(zim_folder, 'all_notes')
    notepath=os.path.join(notes_folder, '%s.txt' %str(docid))

    if os.path.exists(notepath) and not overwrite:
        return

    with open(notepath, 'w') as fout:
        fout.write(text)

    return



class ZimDialog(QtWidgets.QDialog):

    #update_note_sig=pyqtSignal(int, str) # docid, note text

    def __init__(self, meta_dict, folder_dict, folder_data, settings, parent):
        '''
        Args:
            db (sqlite connection): sqlite connection.
            meta_dict (dict): meta data of all documents. keys: docid,
                values: DocMeta dict.
            scores_dict (dict): a caching dict to save fuzzy matching scores:
                keys: (str1, str2), values: fuzzy ratio in int.
                This dict is passed in from the main window so compuations
                done during software running can be cached.
            settings (QSettings): application settings. See _MainWindow.py
            parent (QWidget): parent widget.
        '''

        super().__init__(parent=parent)

        #self.db=db
        self.meta_dict=meta_dict
        self.folder_dict=folder_dict
        self.folder_data=folder_data
        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(900,600)
        self.setWindowTitle('Create Zim Notebook')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Choose Field')
        title_label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(title_label)

        v_layout.addLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        self.cate_list.setMaximumWidth(200)
        h_layout.addWidget(self.cate_list)

        #self.cate_list.setStyleSheet('''
            #QListWidget::item { border: 0px solid rgb(235,235,240);
            #font: 14px;
            #background-color: rgb(205,205,245);
            #color: rgb(100,10,13) };
            #background-color: rgb(230,234,235);
            #''')

        self.cate_list.addItems(['Create Zim Notebook',
            'Update from Zim Notes',
            ])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Close,
            Qt.Horizontal, self)
        #self.apply_button=self.buttons.addButton('Apply',
                #QDialogButtonBox.ApplyRole)

        #self.apply_button.clicked.connect(self.doApply)
        self.buttons.rejected.connect(self.reject)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)


    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):
        '''Load widgets for a selected category

        Args:
            item (QListWidgetItem): selected category item.
        '''

        item_text=item.text()
        LOGGER.info('item.text() = %s' %item.text())

        if self.content_vlayout.count()>1:
            self.content_vlayout.removeWidget(self.content_frame)

        if item_text=='Create Zim Notebook':
            self.content_frame=self.loadCreateZimOptions()
        elif item_text=='Update from Zim Notes':
            self.content_frame=self.loadUpdateFromZimOptions()

        self.content_vlayout.insertWidget(0,self.content_frame)


    def createFrame(self,title):
        '''Create a template frame for a category page

        Args:
            title (str): title of the category

        Returns:
            scroll (QScrollArea): a scroll area.
            va (QVBoxLayout): the vertical box layout used in scroll.
        '''

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


    def loadCreateZimOptions(self):

        scroll,va=self.createFrame('Note Title Format')

        #---------------title format section---------------
        label=QtWidgets.QLabel('Use "Author_year_title" as note title.')
        va.addWidget(label,0,Qt.AlignLeft)

        #---------------create doc notes section---------------
        va.addWidget(getHLine())
        label1=QtWidgets.QLabel("Create a zim file for each document's note")
        label1.setStyleSheet(self.label_color)
        label1.setFont(self.title_label_font)
        self.overwrite_note_cb=QtWidgets.QCheckBox('Overwrite Existing Doc Notes?')
        self.create_notes_button=QtWidgets.QPushButton('Do')
        self.create_notes_button.clicked.connect(self.doCreateDocNotes)
        va.addWidget(label1)
        va.addWidget(self.overwrite_note_cb)
        va.addWidget(self.create_notes_button, 0, Qt.AlignRight)

        #---------------create folder notes section---------------
        va.addWidget(getHLine())
        label2=QtWidgets.QLabel('Create a zim file for each folder')
        label2.setStyleSheet(self.label_color)
        label2.setFont(self.title_label_font)
        self.overwrite_folder_cb=QtWidgets.QCheckBox('Overwrite Existing Folder Notes?')
        self.create_folders_button=QtWidgets.QPushButton('Do')
        self.create_folders_button.clicked.connect(self.doCreateFolderNotes)
        va.addWidget(label2)
        va.addWidget(self.overwrite_folder_cb)
        va.addWidget(self.create_folders_button, 0, Qt.AlignRight)

        va.addStretch()
        self.current_task='create'

        return scroll


    def loadUpdateFromZimOptions(self):

        scroll,va=self.createFrame('Update document notes from Zim')

        va.addWidget(getHLine())
        self.use_zim_default_cb=QtWidgets.QCheckBox('Use zim notes as default note source?')
        if self.settings.value('saving/use_zim_default', type=bool):
            self.use_zim_default_cb.setChecked(True)

        va.addWidget(self.use_zim_default_cb)
        label=QtWidgets.QLabel('''Zim notes saved in %s will be first examined
                when loading the "Notes" tab. If a zim file is not found, it
                will then load data saved in the sqlite database. Changes
                made to the zim files are reflected inside MTT, and also
                get saved into sqlite database.''')
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        va.addWidget(label)

        self.update_from_zim_button=QtWidgets.QPushButton('Save')
        self.update_from_zim_button.clicked.connect(self.doUpdate)
        va.addWidget(self.update_from_zim_button, 0, Qt.AlignRight)

        va.addStretch()
        self.current_task='update'

        return scroll



    @pyqtSlot()
    def doApply(self):

        if self.current_task=='create':
            self.doCreate()
        if self.current_task=='update':
            self.doUpdate()

        return


    def doCreateDocNotes(self):
        print('# <doCreateDocNotes>: ')

        zim_folder=self.createZimBase()

        #-----------------Create doc notes-----------------
        # find docs with notes
        doc_ids=[kk for kk,vv in self.meta_dict.items() if vv['notes']]
        overwrite_notes=self.overwrite_note_cb.isChecked()
        if overwrite_notes:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm Overwrite',
                    'Overwrite contents in the zim files with document notes in MeiTingTrunk? This may result in overwriting your notes made in zim.',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice==QtWidgets.QMessageBox.No:
                overwrite_notes=False
        LOGGER.info('Choose overwrite notes.')

        rec_sum=0
        for dii in doc_ids:
            recii=createDocNote(zim_folder, self.meta_dict, dii, overwrite_notes)
            rec_sum+=recii

        QtWidgets.QMessageBox.information(self, 'Done',
                '%d new Zim notes created.' %rec_sum,
                QtWidgets.QMessageBox.Yes)

        return


    def doCreateFolderNotes(self):
        print('# <doCreateFolderNotes>: ')

        zim_folder=self.createZimBase()

        #--------------Build folder structure--------------
        overwrite_folder=self.overwrite_folder_cb.isChecked()
        if overwrite_folder:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm Overwrite',
                    'Overwrite contents in existing zim files for folders? This will re-create zim notes that correspond to folders in MeiTingTrunk. You may want to do this after folder structure change or document movements.',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice==QtWidgets.QMessageBox.No:
                overwrite_folder=False
        LOGGER.info('Choose overwrite folders.')

        createFolderNote(zim_folder, '-1', self.folder_dict, overwrite_folder)

        #-------------Link doc nots to folder notes-------------
        if overwrite_folder:
            doc_ids=[kk for kk,vv in self.meta_dict.items() if vv['notes']]
            for dii in doc_ids:
                linkDocNote(zim_folder, self.meta_dict, self.folder_dict,
                        self.folder_data, dii)

        QtWidgets.QMessageBox.information(self, 'Done',
                'Zim notes created.',
                QtWidgets.QMessageBox.Yes)

        return

    def createZimBase(self):

        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        lib_name=os.path.split(lib_folder)[1]
        zim_folder=os.path.join(lib_folder, '_zim')

        #----------------Create zim folder----------------
        if not os.path.exists(zim_folder):
            os.makedirs(zim_folder)
            LOGGER.info('Created zim folder at %s' %zim_folder)

        #-----------------Create notebook file-----------------
        notebook_file=os.path.join(zim_folder, 'notebook.zim')
        if not os.path.exists(notebook_file):
            with open(notebook_file, 'w') as fout:
                text=ZIM_HOME_BASE %lib_name
                fout.write(text)
            LOGGER.info('Created notebook.zim.')

        return zim_folder


    def doCreate(self):

        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        lib_name=os.path.split(lib_folder)[1]
        zim_folder=os.path.join(lib_folder, '_zim')

        #----------------Create zim folder----------------
        if not os.path.exists(zim_folder):
            os.makedirs(zim_folder)
            LOGGER.info('Created zim folder at %s' %zim_folder)

        #-----------------Create notebook file-----------------
        notebook_file=os.path.join(zim_folder, 'notebook.zim')
        if not os.path.exists(notebook_file):
            with open(notebook_file, 'w') as fout:
                text=ZIM_HOME_BASE %lib_name
                fout.write(text)
            LOGGER.info('Created notebook.zim.')

        #-----------------Create doc notes-----------------
        # find docs with notes
        doc_ids=[kk for kk,vv in self.meta_dict.items() if vv['notes']]
        overwrite_notes=self.overwrite_note_cb.isChecked()
        if overwrite_notes:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm Overwrite',
                    'Overwrite contents in the zim files with document notes in MeiTingTrunk? This may result in overwriting your notes made in zim.',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice==QtWidgets.QMessageBox.No:
                overwrite_notes=False
        LOGGER.info('Choose overwrite notes.')

        for dii in doc_ids:
            createDocNote(zim_folder, self.meta_dict, dii, overwrite_notes)

        #--------------Build folder structure--------------
        overwrite_folder=self.overwrite_folder_cb.isChecked()
        if overwrite_folder:
            choice=QtWidgets.QMessageBox.question(self, 'Confirm Overwrite',
                    'Overwrite contents in existing zim files for folders? This will re-create zim notes that correspond to folders in MeiTingTrunk. You may want to do this after folder structure change or document movements.',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice==QtWidgets.QMessageBox.No:
                overwrite_folder=False
        LOGGER.info('Choose overwrite folders.')

        createFolderNote(zim_folder, '-1', self.folder_dict, overwrite_folder)

        #-------------Link doc nots to folder notes-------------
        if overwrite_folder:
            for dii in doc_ids:
                linkDocNote(zim_folder, self.meta_dict, self.folder_dict,
                        self.folder_data, dii)

        QtWidgets.QMessageBox.information(self, 'Done',
                'Zim notebook created.',
                QtWidgets.QMessageBox.Yes)

        return


    def doUpdate(self):

        print('# <doUpdate>: ')

        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        #lib_name=os.path.split(lib_folder)[1]
        zim_folder=os.path.join(lib_folder, '_zim')

        zim_default=self.use_zim_default_cb.isChecked()
        self.settings.setValue('saving/use_zim_default', zim_default)

        if not os.path.exists(zim_folder):
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Zim folder not found')
            msg.setText("Zim folder not found.")
            msg.setInformativeText("It seems that there isn't a zim note folder. You need to create one before updating from it.")
            msg.exec_()

            return

        '''
        doc_ids=[kk for kk,vv in self.meta_dict.items() if vv['notes']]

        for dii in doc_ids:
            print('# <doUpdate>: dii=', dii)
            try:
                nii=readZimNote(zim_folder, dii)
            except ZimNoteNotFoundError:
                LOGGER.warning('zim file not found for docid = %s' %dii)
            except Exception as e:
                LOGGER.exception('e = %s' %e)
            else:
                if nii!=self.meta_dict[dii]['notes']:
                    self.update_note_sig.emit(dii, nii)
        '''

        return



