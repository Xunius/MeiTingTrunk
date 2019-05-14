'''
Dialog giving settings to create zim notebook from library.

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
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QModelIndex
from PyQt5.QtGui import QFont, QBrush, QFontMetrics
from PyQt5.QtWidgets import QDialogButtonBox
from ..tools import getHLine, dfsCC, getSqlitePath, createDelButton
from .threadrun_dialog import ThreadRunDialog
from .. import sqlitedb
from ..._MainFrameLoadData import prepareDocs

LOGGER=logging.getLogger(__name__)


FOLDER_NAME_SUB_PATTERN=re.compile(r'[\ ./\\?,:=!@#$%^&*+]')
COLLAPSE_UNDERSCORE=re.compile(r'_+')


def getZimHeader(title):

    tnow=datetime.today()
    tstr=datetime.strftime(tnow, '%A %d %B %Y')

    text=\
'''Content-Type: text/x-zim-wiki
Wiki-Format: zim 0.4

====== %s ======
Created %s
''' %(title, tstr)

    return text


def removeInvalidChar(text):

    new=re.sub(FOLDER_NAME_SUB_PATTERN, '_', text)
    new=re.sub(COLLAPSE_UNDERSCORE, '_', new)
    new=new.strip('_')

    return new


def createNote(folder, title, contents=None):

    #note_fname=title.replace(' ', '_')
    note_fname=removeInvalidChar(title)
    note_folder=os.path.join(folder, note_fname)
    if not os.path.exists(note_folder):
        os.makedirs(note_folder)

    note_path='%s.txt' %note_folder

    header=getZimHeader(title)
    print('# <createNote>: folder=', folder)
    print('# <createNote>: note_folder=', note_folder)
    print('# <createNote>: note_path=', note_path)
    with open(note_path, 'w') as fout:
        fout.write(header)
        if contents is not None:
            fout.write('\n')
            fout.write(contents)

    return note_path


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



class CreateZimDialog(QtWidgets.QDialog):

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

        self.cate_list.addItems(['Zim Structure',
            'xxxx',
            ])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Close,
            Qt.Horizontal, self)
        self.apply_button=self.buttons.addButton('Apply',
                QDialogButtonBox.ApplyRole)

        self.apply_button.clicked.connect(self.doCreate)
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

        if item_text=='Zim Structure':
            self.content_frame=self.loadZimStructureOptions()
        elif item_text=='xxxx':
            pass

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


    def loadZimStructureOptions(self):

        scroll,va=self.createFrame('Note Title')

        label=QtWidgets.QLabel('Use "Author_year_title" as note title.')
        va.addWidget(label,0,Qt.AlignLeft)


        return scroll


    @pyqtSlot()
    def doCreate(self):
        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        lib_name=os.path.split(lib_folder)[1]
        print('# <doCreate>: lib_folder=',lib_folder)
        print('# <doCreate>: lib_name=',lib_name)

        zim_folder=os.path.join(lib_folder, '_zim')

        #----------------Create zim folder----------------
        if not os.path.exists(zim_folder):
            os.makedirs(zim_folder)
            LOGGER.info('Created zim folder at %s' %zim_folder)

        #-----------------Create notebook file-----------------
        notebook_file=os.path.join(zim_folder, 'notebook.zim')
        if not os.path.exists(notebook_file):
            with open(notebook_file, 'w') as fout:

                text='''[Notebook]
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
''' %lib_name
                fout.write(text)

            print('# <doCreate>: notebook file wrote')


        #-----------------Create Home note-----------------
        def addFolder(parent, parent_folder, folderid, folder_dict):

            foldername,parentid=folder_dict[folderid]
            sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
            print('# <addFolder>: parent=', parent, 'folderid=', folderid, 'foldername=',foldername)

            pname, pid=parent
            #if pid=='-1':
                #parent_path=zim_folder
            #else:
                #parent_path=os.path.join(zim_folder, pname.replace(' ','_'))

            #sub_strs=[]
            #for fii in sub_ids:
                #snameii=folder_dict[fii][0]
                #snameii=removeInvalidChar(snameii)
                #sub_strs.append('[[+%s]]\n' %snameii)
            #sub_strs=['[[+%s]]\n' %folder_dict[fii][0] for fii in \
                    #sub_ids]
            #sub_strs='\n'.join(sub_strs)
            sub_strs=getSubFolderStr(sub_ids, folder_dict, 'sub')

            # find docs with notes
            doc_ids=self.folder_data[folderid]
            print('# <addFolder>: docs=', doc_ids)

            doc_ids=[dii for dii in doc_ids if self.meta_dict[dii]['notes']]
            print('# <addFolder>: docs after =', doc_ids)

            doc_strs=[]
            p_folder=os.path.join(parent_folder, removeInvalidChar(foldername))
            for dii in doc_ids:
                #getDocsWithNotes(dii, self.meta_dict)
                citationkey=self.meta_dict[dii]['citationkey']
                title=self.meta_dict[dii]['title']
                author=self.meta_dict[dii]['lastName_l']
                if len(author)==0:
                    print('# <addFolder>: ###########', author)
                    author=''
                else:
                    author=author[0]

                year=self.meta_dict[dii]['year']
                notes=self.meta_dict[dii]['notes']

                notetitle='%s_%s_%s' %(author, year, title)
                notetitle=removeInvalidChar(notetitle)

                doc_strs.append('[[+%s]]' %notetitle)

                createNote(p_folder, notetitle, notes)

            #if pid=='49':
                #print('# <addFolder>: parent=',parent,parent_path)

            doc_strs.sort()
            doc_strs='\n'.join(doc_strs)
            createNote(parent_folder, foldername, sub_strs+'\n#####\n'+doc_strs)

            if len(sub_ids)>0:
                #p_folder=os.path.join(parent_folder,
                        #removeInvalidChar(foldername))
                for sii in sub_ids:
                    addFolder((foldername, folderid), p_folder, sii,
                            folder_dict)

            return

        homenote_file=os.path.join(zim_folder, 'Home.txt')
        if not os.path.exists(homenote_file):

            #-----------------Get folder tree-----------------
            # Get all level 1 folders
            folders1=[kk for kk,vv in self.folder_dict.items() if\
                    vv[1]=='-1']
            folders1.sort()
            print('# <doCreate>: folders1', folders1)

            #header=getZimHeader('Home')
            #folders1_strs=['[[:%s]]\n' %self.folder_dict[fii[1]][0] for fii in \
                    #folders1]
            #folders1_strs='\n'.join(folders1_strs)
            line1='\nNotes created for library %s.\n' %lib_name
            folders1_strs=getSubFolderStr(folders1, self.folder_dict, 'base')
            folders1_strs=line1+'\n'+folders1_strs


            createNote(zim_folder, 'Home', contents=folders1_strs)

            #with open(homenote_file, 'w') as fout:
                #fout.write(header)
                #fout.write('Notes created for library %s\n' %lib_name)

                #for fnameii, fidii in folders1:
                    #s_str='[[:%s]]\n' %fnameii
                    #fout.write(s_str)

            # walk down
            for fidii in folders1:
                #print('# <doCreate>: f1ii=', fnameii, repr(fidii))

                #subsii=sqlitedb.getChildFolders(self.folder_dict, fidii)
                #print('    ', subsii)
                addFolder(('All', '-1'), zim_folder, fidii, self.folder_dict)



