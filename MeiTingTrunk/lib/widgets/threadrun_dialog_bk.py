from queue import Queue
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDialogButtonBox


LOGGER=logging.getLogger('default_logger')



class Worker(QObject):

    worker_jobdone_signal=pyqtSignal(int) # jobid

    def __init__(self, id, func, jobqueue, outqueue):
        super(Worker,self).__init__()
        '''Worker used for separate thread.

        NOTE: args for func is assumed to have the format (jobid,jobargs)
        return of func is assumed to have the format (return_code, jobid,\
                other_results)
        '''

        self.id=id
        self.func=func
        self.jobqueue=jobqueue
        self.outqueue=outqueue
        self.abort=False

    @pyqtSlot()
    def processJob(self):
        while self.jobqueue.qsize():
            QtWidgets.QApplication.processEvents()
            if self.abort:
                return

            args=self.jobqueue.get()
            jobid=args[0]
            try:
                rec=self.func(*args)
                print('# <Worker>: Job %d done. Remaining queue size: %d.'\
                    %(jobid, self.jobqueue.qsize()))
            except:
                rec=(1,jobid,None)
                print('# <Worker>: Job %d failed. Remaining queue size: %d.'\
                    %(jobid, self.jobqueue.qsize()))
            self.jobqueue.task_done()
            self.outqueue.put(rec)
            self.worker_jobdone_signal.emit(jobid)

        return



class Master(QObject):

    all_done_signal=pyqtSignal()
    donejobs_count_signal=pyqtSignal(int) # NO. of finshed jobs

    def __init__(self, func, joblist, max_threads=4):
        super(Master,self).__init__()

        self.func=func
        self.joblist=joblist
        self.max_threads=max_threads
        self.all_done_signal.connect(self.onAllJobsDone)

    def run(self):

        self.threads=[]
        self.results=[]
        n_threads=min(self.max_threads,len(self.joblist))
        self.finished=0
        self.finished_jobs=[]

        self.jobqueue=Queue()
        self.outqueue=Queue()
        # populate job queue
        for ii,jobii in enumerate(self.joblist):
            self.jobqueue.put(jobii)

        # start worker threads
        for ii in range(n_threads):
            print('# <run>: create thread',ii)
            tii=QThread()
            wii=Worker(ii,self.func,self.jobqueue,self.outqueue)
            self.threads.append((tii,wii)) # need to keep record of both!

            wii.moveToThread(tii)
            wii.worker_jobdone_signal.connect(self.countJobDone)
            tii.started.connect(wii.processJob)
            tii.start()

        return


    @pyqtSlot(int)
    def countJobDone(self,jobid):
        self.finished+=1
        self.finished_jobs.append(jobid)
        self.donejobs_count_signal.emit(self.finished)
        while self.outqueue.qsize():
            resii=self.outqueue.get()
            self.results.append(resii)

        print('# <countJobDone>: Finished job id=%d. Finished jobs=%d'\
                %(jobid, self.finished))

        if self.finished==len(self.joblist):
            self.all_done_signal.emit()

        return


    @pyqtSlot()
    def onAllJobsDone(self):
        while self.outqueue.qsize():
            resii=self.outqueue.get()
            self.results.append(resii)

        for tii,wii in self.threads:
            tii.quit()
            tii.wait()
        return

    @pyqtSlot()
    def abortJobs(self):
        for tii,wii in self.threads:
            wii.abort=True
            tii.quit()
            tii.wait()



class ThreadRunDialog(QtWidgets.QDialog):

    def __init__(self,func,joblist,show_message='',max_threads=3,
            get_results=False,close_on_finish=True,parent=None):
        super(ThreadRunDialog,self).__init__(parent=parent)

        self.func=func
        self.joblist=joblist
        self.show_message=show_message
        self.max_threads=max_threads
        self.get_results=get_results
        self.close_on_finish=close_on_finish
        self.parent=parent

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle('Processing ...')
        self.resize(500,100)

        va=QtWidgets.QVBoxLayout(self)

        va.addWidget(QtWidgets.QLabel(show_message))

        self.progressbar=QtWidgets.QProgressBar(self)
        self.progressbar.setMaximum(len(joblist))
        self.progressbar.setValue(0)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)

        va.addWidget(self.progressbar)
        va.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.abortJobs)

        self.master=Master(func,joblist,self.max_threads)
        self.master.donejobs_count_signal.connect(self.updatePB)
        self.ok_button=self.buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        self.cancel_button=self.buttons.button(QDialogButtonBox.Cancel)
        self.master.all_done_signal.connect(self.allJobsDone)

        self.master.run()
        self.exec_()


    @pyqtSlot()
    def allJobsDone(self):
        self.cancel_button.setEnabled(False)
        self.ok_button.setEnabled(True)
        if self.close_on_finish:
            self.accept()
        return

    @pyqtSlot(int)
    def updatePB(self,value):
        self.progressbar.setValue(value)
        return

    @pyqtSlot()
    def abortJobs(self):
        self.master.abortJobs()
        if self.get_results:
            self.results=self.master.results
        self.reject()
        return

    @pyqtSlot()
    def accept(self):
        print('# <accept>: get result?',self.get_results)
        if self.get_results:
            self.results=self.master.results
            print('# <accept>: self.results',self.results)
        super(ThreadRunDialog,self).accept()
        return


