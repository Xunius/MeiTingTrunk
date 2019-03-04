'''General purpose functions.

Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
Update time: 2018-09-29 21:20:32.
'''

import os
import re
import time
import platform
from functools import reduce
from fuzzywuzzy import fuzz
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, QObject, QMutex, pyqtSignal, pyqtSlot, Qt
try:
    from . import sqlitedb
except:
    import sqlitedb

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


def parseAuthors(textlist):
    firstnames=[]
    lastnames=[]
    for nii in textlist:
        nii=nii.split(',',1)
        lastnames.append(nii[0] if len(nii)>1 else nii[0])
        firstnames.append(nii[1] if len(nii)>1 else '')
    authors=sqlitedb.zipAuthors(firstnames,lastnames)

    return firstnames,lastnames,authors

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


def fuzzyMatch(jobid,id1,id2,dict1,dict2):

    authors1=dict1['authors_l'] or ''
    authors2=dict2['authors_l'] or ''
    authors1=', '.join(authors1)
    authors2=', '.join(authors2)

    title1=dict1['title'] or ''
    title2=dict2['title'] or ''

    journal1=dict1['publication'] or ''
    journal2=dict2['publication'] or ''
    print('# <fuzzyMatch>: year1=',dict1['year'])
    print('# <fuzzyMatch>: year2=',dict2['year'])
    year1=dict1['year'] or ''
    year2=dict2['year'] or ''

    jy1='%s %s' %(journal1, year1)
    jy2='%s %s' %(journal2, year2)


    ratio_authors=fuzz.token_sort_ratio(authors1, authors2)
    ratio_title=fuzz.ratio(title1, title2)
    #ratio_other=fuzz.token_set_ratio(jy1, jy2)
    ratio_other=fuzz.ratio(jy1, jy2)

    len_authors=0.5*(len(authors1)+len(authors2))
    len_title=0.5*(len(title1)+len(title2))
    len_other=0.5*(len(jy1)+len(jy2))

    score=(len_authors*ratio_authors + len_title*ratio_title + len_other*ratio_other)/\
            (len_authors+len_title+len_other)

    print('\n# <fuzzyMatch>: authors1=',authors1,'\nauthors2=',authors2,'\nscore=',
            ratio_authors)
    print('\n# <fuzzyMatch>: title1=',title1,'\ntitle2=',title2,'\nscore=',
            ratio_title)
    print('\n# <fuzzyMatch>: jy1=',jy1,'\njy2=',jy2,'\nscore=',
            ratio_other)

    #return round(score)
    return 0,jobid, ((id1,id2), round(score))


def dfsCC(edges):
    '''Get connected components in undirected graph
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
            parent.addTopLevelItem(fitem)
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

    #-------------Get all level 1 folders-------------
    folders1=[(vv[0],kk) for kk,vv in folder_dict.items() if\
            vv[1] in ['-1',]]
    folders1.sort()

    #------------Add folders to tree------------
    for fnameii,idii in folders1:
        addFolder(folder_tree,idii,folder_dict)

    return folder_tree


def iterTreeWidgetItems(treewidget, root=None):
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

    <abpath>: str, absolute path to a folder or a file to rename.
    
    Return <newname>: str, new file path.
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

