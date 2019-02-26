'''General purpose functions.

Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
Update time: 2018-09-29 21:20:32.
'''

import os
import re
import time
import platform
from fuzzywuzzy import fuzz
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, QObject, QMutex, pyqtSignal, pyqtSlot
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


def fuzzyMatch(dict1,dict2):

    authors1=dict1.get('authors_l','')
    authors2=dict2.get('authors_l','')
    authors1=', '.join(authors1)
    authors2=', '.join(authors2)

    title1=dict1.get('title','')
    title2=dict2.get('title','')

    journal1=dict1.get('journal','')
    journal2=dict2.get('journal','')
    year1=dict1.get('year','')
    year2=dict2.get('year','')

    jy1='%s %s' %(journal1, year1)
    jy2='%s %s' %(journal2, year2)

    print('# <fuzzyMatch>: authors1=',authors1,'authors2=',authors2,
            'title1=',title1,'title2=',title2,'jy1=',jy1,'jy2=',jy2)

    ratio_authors=fuzz.token_sort_ratio(authors1, authors2)
    ratio_title=fuzz.partial_ratio(title1, title2)
    ratio_other=fuzz.token_set_ratio(jy1, jy2)

    len_authors=0.5*(len(authors1)+len(authors2))
    len_title=0.5*(len(title1)+len(title2))
    len_other=0.5*(len(jy1)+len(jy2))

    score=(len_authors*ratio_authors + len_title*ratio_title + len_other*ratio_other)/\
            (len_authors+len_title+len_other)

    return score



