'''
General purpose functions.


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
import time
import platform
import logging
import subprocess
from functools import reduce
from fuzzywuzzy import fuzz
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, QObject, QMutex, pyqtSignal, pyqtSlot, Qt
try:
    from . import sqlitedb
except:
    import sqlitedb

LOGGER=logging.getLogger(__name__)


def getMinSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum)
    return sizePolicy


def getXMinYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy


def getXExpandYMinSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum)
    return sizePolicy


def getXExpandYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy


def getHSpacer():
    h_spacer = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum)
    return h_spacer


def getVSpacer():
    v_spacer = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
    return v_spacer


def getHLine(parent=None):
    h_line = QtWidgets.QFrame(parent)
    h_line.setFrameShape(QtWidgets.QFrame.HLine)
    h_line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return h_line


def getVLine(parent=None):
    v_line = QtWidgets.QFrame(parent)
    v_line.setFrameShape(QtWidgets.QFrame.VLine)
    v_line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return v_line


class WorkerThread(QThread):
    '''NOT IN USE'''

    jobdone_signal=pyqtSignal()
    def __init__(self,func,jobqueue,outqueue,parent=None):
        QThread.__init__(self,parent)

        self.func=func
        self.jobqueue=jobqueue
        self.outqueue=outqueue

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            print('\n# <WorkThread>: Thread start processing ... Remaining queue size: %d.'\
                %(self.jobqueue.qsize()))
            args=self.jobqueue.get()
            rec=self.func(*args)
            self.jobqueue.task_done()
            self.outqueue.put(rec)
            self.jobdone_signal.emit()
            time.sleep(0.1)


class Worker(QObject):
    '''NOT IN USE'''
    sgnFinished = pyqtSignal()

    def __init__(self, parent, func, jobq, outq):
        QObject.__init__(self, parent)
        self._mutex = QMutex()
        self._running = True
        self.jobq=jobq
        self.outq=outq
        self.func=func

    @pyqtSlot()
    def stop(self):
        print('switching while loop condition to false')
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()

    def running(self):
        try:
            self._mutex.lock()
            return self._running
        finally:
            self._mutex.unlock()

    @pyqtSlot()
    def work(self):
        while self.running():
            args=self.jobq.get()
            rec=self.func(*args)
            self.jobq.task_done()
            self.outq.put(rec)
            #time.sleep(0.1)
            print('doing work...')

        self.sgnFinished.emit()


class Client(QObject):
    '''NOT IN USE'''
    clientDone = pyqtSignal()

    def __init__(self, parent, func, jobq, outq, callback):
        QObject.__init__(self, parent)
        self.jobq=jobq
        self.outq=outq
        self.func=func
        self.callback=callback
        self.clientDone.connect(callback)
        self._thread = QThread()
        self._worker = Worker(None,self.func,self.jobq,self.outq)
        self._worker.sgnFinished.connect(self.on_worker_done)

    def start(self):
        self._thread.started.connect(self._worker.work)
        self._worker.moveToThread(self._thread)
        self._thread.start()

    def stop(self):
        print('stopping the worker object')
        self._worker.stop()

    @pyqtSlot()
    def on_worker_done(self):
        print('workers job was interrupted manually')
        self._thread.quit()
        self.clientDone.emit()


def parseAuthors(authorlist):
    """Parse a list of author names

    Args:
        authorlist (list): list of author names: ['firname, lastname', ...]

    Returns:
        firstnames (list): list of first names.
        lastnames (list): list of last names.
        authorlist (list): list of author names.

    """
    firstnames=[]
    lastnames=[]
    for nii in authorlist:
        nii=nii.split(',',1)
        lastnames.append(nii[0].strip() if len(nii)>1 else nii[0])
        firstnames.append(nii[1].strip() if len(nii)>1 else '')
    #authors=sqlitedb.zipAuthors(firstnames,lastnames)

    return firstnames,lastnames,authorlist


def removeInvalidPathChar(path):
    '''Make dir and remove invalid windows path characters

    ':' is illegal in Mac and windows. Strategy: remove, although legal in Linux.
    '''
    path=os.path.abspath(path)

    if platform.system().lower()=='windows':
        drive,remain=os.path.splitdrive(path)
        remain=re.sub(r'[<>:"|?*]','_',remain)
        remain=remain.strip()
        path=os.path.join(drive,remain)
    else:
        path=re.sub(r'[<>:"|?*]','_',path)

    return path


def fuzzyMatchPrepare(docid, meta_dict):
    """Get meta data in a document and prepare strings for fuzzy matching

    Args:
        docid (int): doc id.
        meta_dict (DocMeta): meta data dict of doc.

    Returns:
        docid (int): doc id.
        authors1 (str): author list string.
        title1 (str): title.
        jy1 (str): journal+year string.
    """

    authors1=meta_dict['authors_l'] or ''
    authors1=', '.join(authors1)

    title1=meta_dict['title'] or ''

    journal1=meta_dict['publication'] or ''
    year1=meta_dict['year'] or ''

    jy1='%s %s' %(journal1, year1)

    return docid, authors1, title1, jy1


def fuzzyMatch(jobid, doc1_list, doc2_list, min_score):
    """Compute similarity score between 2 docs using fuzzy matching

    Args:
        jobid (int): job id.
        doc1_list (list): strings to compare in doc 1.
        doc2_list (list): strings to compare in doc 2.
        min_score (int): minimum score to flag a match.

    Returns:
        rec (int): 0 for success.
        jobid (int): input jobid.
        match_result (tuple): in the format ((id1, id2), score). Where score
                              is an int in [0,100], higher means more similar.

    """

    id1, authors1, title1, jy1 = doc1_list
    id2, authors2, title2, jy2 = doc2_list

    len_authors=(len(authors1)+len(authors2))//2
    len_title=(len(title1)+len(title2))//2
    len_other=(len(jy1)+len(jy2))//2
    A=min_score*(len_authors+len_title+len_other)

    ratio_authors=fuzz.ratio(authors1, authors2)

    # a short cut for authors score
    if len_authors>0:
        min_ratio_authors=A/len_authors - 100*(len_title+len_other)/len_authors
        if ratio_authors<min_ratio_authors:
            return 0,jobid, ((id1,id2), 0)

    ratio_title=fuzz.ratio(title1, title2)

    # a short cut for authors score
    if len_title>0:
        min_ratio_title=A/len_title - (ratio_authors*len_authors+100*len_other)/len_title
        if ratio_title<min_ratio_title:
            return 0,jobid, ((id1,id2), 0)

    ratio_other=fuzz.ratio(jy1, jy2)

    score=(len_authors*ratio_authors + len_title*ratio_title + len_other*ratio_other)//\
            (len_authors+len_title+len_other)

    '''
    LOGGER.debug('authors1 = %s, authors2 = %s, score = %d'\
            %(authors1, authors2, ratio_authors))
    LOGGER.debug('title1 = %s, title2 = %s, score = %d'\
            %(title1, title2, ratio_title))
    LOGGER.debug('jy1 = %s, jy2 = %s, score = %d'\
            %(jy1, jy2, ratio_other))
    '''

    return 0,jobid, ((id1,id2), round(score))


def dfsCC(edges):
    '''Get connected components in undirected graph using DFS

    Args:
        edges (list): list of vertices.

    Returns:
        ccs.values (list): list of connected components, in the format:
            [(v1, v2, ...), (v3, v4, ...) ...],
            each tuple is a connected component.
    '''

    def explore(v,cc):
        visited.append(v)
        if cc not in ccs:
            ccs[cc]=[v,]
        else:
            ccs[cc].append(v)

        for wii in adj_list[v]:
            if wii not in visited:
                explore(wii,cc)

    vertices=list(set(reduce(tuple.__add__,edges)))
    rev_edges=[(v2,v1) for v1,v2 in edges]

    # get adjacency list
    adj_list={}
    for vii in vertices:
        adj_list[vii]=[eii[1] for eii in edges+rev_edges if eii[0]==vii]

    visited=[]
    ccs={}
    cc=0

    for v in vertices:
        if v not in visited:
            explore(v,cc)
            cc+=1

    return list(ccs.values())


def createFolderTree(folder_dict,parent):
    """Create a folder tree using QTreeWidget

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        parent (QWidget): parent of QTreeWidget.

    Returns:
        folder_tree (QTreeWidget): QTreeWidget with the folder structure.
    """

    def addFolder(parent,folderid,folder_dict):

        foldername,parentid=folder_dict[folderid]
        fitem=QtWidgets.QTreeWidgetItem([foldername,str(folderid)])
        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        fitem.setIcon(0,diropen_icon)
        sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
        if parentid=='-1':
            fitem.setFlags(fitem.flags() | Qt.ItemIsTristate |\
                    Qt.ItemIsUserCheckable)
            fitem.setCheckState(0, Qt.Unchecked)
            #parent.addTopLevelItem(fitem)
            parent.addChild(fitem)
        else:
            fitem.setFlags(fitem.flags() | Qt.ItemIsUserCheckable)
            fitem.setCheckState(0, Qt.Unchecked)
            parent.addChild(fitem)
        if len(sub_ids)>0:
            for sii in sub_ids:
                addFolder(fitem,sii,folder_dict)

        return

    folder_tree=QtWidgets.QTreeWidget(parent)
    folder_tree.setColumnCount(2)
    folder_tree.setHeaderHidden(True)
    folder_tree.setColumnHidden(1,True)
    folder_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    folder_tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
    folder_tree.header().setStretchLastSection(False)
    folder_tree.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents)
    folder_tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

    #---------------------Add All---------------------
    allitem=QtWidgets.QTreeWidgetItem(['All', '-1'])
    style=QtWidgets.QApplication.style()
    diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
    allitem.setIcon(0,diropen_icon)
    allitem.setFlags(allitem.flags() | Qt.ItemIsTristate |\
            Qt.ItemIsUserCheckable)
    allitem.setCheckState(0, Qt.Unchecked)
    folder_tree.addTopLevelItem(allitem)

    #-------------Get all level 1 folders-------------
    folders1=[(vv[0],kk) for kk,vv in folder_dict.items() if\
            vv[1] in ['-1',]]
    folders1.sort()

    #------------Add folders to tree------------
    for fnameii,idii in folders1:
        addFolder(allitem,idii,folder_dict)

    allitem.setExpanded(True)

    return folder_tree


def iterTreeWidgetItems(treewidget, root=None):
    """Iterate through all items in a QTreeWidget

    Args:
        treewidget (QTreeWidget): QTreeWidget to Iterate.
        root (None or QTreeWidgetItem): start point.
    Returns:
        yield each item found.
    """

    if root is None:
        root=treewidget.invisibleRootItem()

    stack = [root]
    while stack:
        parent = stack.pop(0)
        for row in range(parent.childCount()):
            child = parent.child(row)
            yield child
            if child.childCount()>0:
                stack.append(child)


def autoRename(abpath):
    '''Auto rename a file to avoid overwriting an existing file

    Args:
        abpath (str): absolute path to a folder or a file to rename.

    Returns:
        newname (str): new file path.

    If no conflict found, return <abpath>;
    If conflict with existing file, return renamed file path,
    by appending "_(n)".
    E.g.
        n1='~/codes/tools/send2ever.py'
        n2='~/codes/tools/send2ever_(4).py'
    will be renamed to
        n1='~/codes/tools/send2ever_(1).py'
        n2='~/codes/tools/send2ever_(5).py'
    '''

    def rename_sub(match):
        base=match.group(1)
        delim=match.group(2)
        num=int(match.group(3))
        return '%s%s(%d)' %(base,delim,num+1)

    if not os.path.exists(abpath):
        return abpath

    folder,filename=os.path.split(abpath)
    basename,ext=os.path.splitext(filename)
    # match filename
    rename_re=re.compile('''
            ^(.+?)       # File name
            ([- _])      # delimiter between file name and number
            \\((\\d+)\\) # number in ()
            (.*)         # ext
            $''',\
            re.X)

    newname='%s_(1)%s' %(basename,ext)
    while True:
        newpath=os.path.join(folder,newname)

        if not os.path.exists(newpath):
            break
        else:
            if rename_re.match(newname):
                newname=rename_re.sub(rename_sub,newname)
                newname='%s%s' %(newname,ext)
            else:
                raise Exception("Exception")

    newname=os.path.join(folder,newname)
    return newname


def hasPdftotext():
    '''Check the existance of pdftotext'''

    proc=subprocess.Popen(['which','pdftotext'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    rec=proc.communicate()
    if len(rec[0])==0 and len(rec[1])>0:
        return False

    return True


def hasXapian():
    '''Check the existance of xapian core and xapian-python'''

    proc=subprocess.Popen(['which','xapian-delve'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    rec=proc.communicate()
    if len(rec[0])==0 and len(rec[1])>0:
        return False

    proc=subprocess.Popen(['which','omindex'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    rec=proc.communicate()
    if len(rec[0])==0 and len(rec[1])>0:
        return False

    try:
        import xapian
    except:
        return False

    return True


def isXapianReady():

    return hasPdftotext() and hasXapian()


class Cache(object):
    def __init__(self, func):
        self.func=func
        self.store_dict={}

    def get(self, key, args=(), update=False):
        '''
        if not update:
            return self.store_dict.setdefault(key, self.func(*args))
        else:
            self.store_dict[key]=self.func(*args)
            return self.store_dict[key]
        '''
        if not update and key in self.store_dict:
            print('# <get>: get existing for key=',key)
            return self.store_dict[key]

        print('# <get>: compute new for key=',key)
        value=self.func(*args)
        self.store_dict[key]=value

        return value


def getSqlitePath(connection):
    '''Get the database path from connection
    '''

    return connection.execute('PRAgMA database_list').fetchall()[0][2]


def createDelButton(font_height=12):
    '''Create a circular button with a symbol x

    Kwargs:
        font_height (int): font height. Determines button size.
    '''

    button=QtWidgets.QPushButton()
    button.setFixedWidth(int(font_height))
    button.setFixedHeight(int(font_height))
    button.setText('\u2715')
    button.setStyleSheet('''
    QPushButton {
        border: 1px solid rgb(190,190,190);
        background-color: rgb(190,190,190);
        border-radius: %dpx;
        font: bold %dpx;
        color: white;
        text-align: center;
        }

    QPushButton:pressed {
        border-style: inset;
        }
    ''' %(int(font_height/2), max(1,font_height-2))
    )

    return button
