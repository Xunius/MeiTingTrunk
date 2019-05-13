'''
Widgets for running tasks in separate threads, feedback display and task
controls.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from queue import Queue
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDialogButtonBox


LOGGER=logging.getLogger(__name__)


class SimpleWorker(QObject):

    def __init__(self, id, func):
        super().__init__()
        '''Worker used in separate thread.

        Args:
            id (int): id for the thread/worker.
            func (function): function object to call in the thread.
        '''

        self.id=id
        self.func=func

    @pyqtSlot()
    def processJob(self):
        self.func()

        return



class Worker(QObject):

    worker_jobdone_signal=pyqtSignal(int) # jobid

    def __init__(self, id, func, jobqueue, outqueue):
        super(Worker,self).__init__()
        '''Worker used in separate thread.

        Args:
            id (int): id for the thread/worker.
            func (function): function object to call in the thread.
            jobqueue (Queue): queue object containing input args.
            outqueue (Queue): queue object storing function returns.

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
                LOGGER.debug('Job %d done. Remaining queue size: %d.'\
                    %(jobid, self.jobqueue.qsize()))
            except:
                rec=(1,jobid,None)
                LOGGER.debug('Job %d failed. Remaining queue size: %d.'\
                    %(jobid, self.jobqueue.qsize()))
            self.jobqueue.task_done()
            self.outqueue.put(rec)
            self.worker_jobdone_signal.emit(jobid)

        return


class Master(QObject):

    all_done_signal=pyqtSignal()
    donejobs_count_signal=pyqtSignal(int) # NO. of finshed jobs

    def __init__(self, func, joblist, max_threads=4, progressbar=None,
            progressbar_style='classic',
            statusbar=None,
            show_message='',
            post_process_func=None,
            post_process_func_args=(),
            post_process_progress=1,
            close_on_finish=True,
            parent=None):
        '''A controller distributing tasks to workers, collecting results and
        sending feedbacks on task status

        Args:
            func (function): function object to call in the thread.
            joblist( list): list of job tasks, in the format:
                [(jobid1, jobargs), (jobid2, jobargs) ... ]

        Kwargs:
            max_threads (int): maximum number of threads to spawn.
            progressbar (QProgressBar or None): progressbar widget to send
                progress feedback. If None, ignore.
            progressbar_style (str): if 'classic', use percentage wise
                progressbar. if 'busy', use busy progressbar.
            statusbar (QStatusBar): status bar widget to show messages. If
                None, ignore.
            show_message (str): message to show in the status bar when running.
            post_process_func (callable): function object to call on each
                return value of <func>, as a post-process.
            post_process_func_args (tuple): additional arguments for the
                <post_process_func>.
            post_process_progress (int): when using 'classic' progressbar,
                how much percentage should the post-process count.
            close_on_finish (bool): If True, clear status bar message and
                hide progressbar after all jobs done.
            parent (QWidget): parent widget.

        '''
        super(self.__class__,self).__init__()

        self.func=func
        self.joblist=joblist
        self.max_threads=max_threads
        self.progressbar=progressbar
        self.progressbar_style=progressbar_style
        self.statusbar=statusbar
        self.show_message=show_message
        self.post_process_func=post_process_func
        self.post_process_func_args=post_process_func_args
        self.post_process_progress=post_process_progress
        self.close_on_finish=close_on_finish
        self.parent=parent

        self.all_done_signal.connect(self.onAllJobsDone)


    def run(self):

        if self.progressbar:
            if self.progressbar_style=='classic':
                if self.post_process_func is None:
                    self.progressbar.setMaximum(len(self.joblist))
                else:
                    self.progressbar.setMaximum(len(self.joblist)+\
                            self.post_process_progress)
                self.progressbar.setValue(0)
            elif self.progressbar_style=='busy':
                self.progressbar.setMaximum(0)
            else:
                raise Exception("Not defined")
            self.progressbar.setVisible(True)
        if self.statusbar and self.show_message:
            self.statusbar.showMessage(self.show_message)

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
            LOGGER.debug('Create thread %s' %ii)

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
        if self.progressbar and self.progressbar_style=='classic':
            self.progressbar.setValue(self.finished)

        LOGGER.debug('finished = %s. NO of results = %d' %(self.finished,
            len(self.results)))

        if self.finished==len(self.joblist):
            self.all_done_signal.emit()

        return


    @pyqtSlot()
    def onAllJobsDone(self):

        for tii,wii in self.threads:
            tii.quit()
            tii.wait()

        if self.post_process_func is not None:
            LOGGER.debug('Call post-process')

            self.results=self.post_process_func(self.results,
                    *self.post_process_func_args)
            if self.progressbar:
                self.progressbar.setValue(self.progressbar.maximum())

        if self.close_on_finish:
            if self.statusbar:
                self.statusbar.clearMessage()
            if self.progressbar:
                self.progressbar.setVisible(False)
        else:
            if self.statusbar:
                self.statusbar.showMessage('Finished.')
            if self.progressbar:
                self.progressbar.setVisible(False)

        return


    @pyqtSlot()
    def abortJobs(self):
        for tii,wii in self.threads:
            wii.abort=True
            tii.quit()
            tii.wait()
        if self.progressbar:
            self.progressbar.setVisible(False)
        if self.statusbar:
            self.statusbar.clearMessage()

        return


class ThreadRunDialog(QtWidgets.QDialog):

    abort_job_signal=pyqtSignal()

    def __init__(self,func, joblist, show_message='', max_threads=3,
            get_results=False, close_on_finish=True,
            progressbar_style='classic',
            post_process_func=None,
            post_process_func_args=(),
            post_process_progress=1,
            parent=None):
        '''A modal dialog shown when calling some long-lasting tasks, with
        message label, progressbar giving feedbacks.

        Args:
            func (callable): function object to call in the thread.
            joblist( list): list of job tasks, in the format:
                [(jobid1, jobargs), (jobid2, jobargs) ... ]

        Kwargs:
            max_threads (int): maximum number of threads to spawn.
            get_results (bool): if True, set the results to a results
                attribute of the dialog.
            close_on_finish (bool): If True, close dialog when all jobs done.
            progressbar_style (str): if 'classic', use percentage wise
                progressbar. if 'busy', use busy progressbar.
            post_process_func (callable): function object to call on each
                return value of <func>, as a post-process.
            post_process_func_args (tuple): additional arguments for the
                <post_process_func>.
            post_process_progress (int): when using 'classic' progressbar,
                how much percentage should the post-process count.
            parent (QWidget): parent widget.
        '''

        super(self.__class__,self).__init__(parent=parent)

        self.func=func
        self.joblist=joblist
        self.show_message=show_message
        self.max_threads=max_threads
        self.get_results=get_results
        self.close_on_finish=close_on_finish
        self.progressbar_style=progressbar_style
        self.post_process_func=post_process_func
        self.post_process_func_args=post_process_func_args
        self.post_process_progress=post_process_progress
        self.parent=parent

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle('Processing ...')
        self.resize(500,100)

        va=QtWidgets.QVBoxLayout(self)

        self.label=QtWidgets.QLabel(show_message)
        va.addWidget(self.label)

        self.progressbar=QtWidgets.QProgressBar(self)
        self.progressbar.setMaximum(len(joblist))
        self.progressbar.setValue(0)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)

        va.addWidget(self.progressbar)
        va.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.abortJobs)

        self.master=Master(func,joblist,self.max_threads,self.progressbar,
                self.progressbar_style, None, '',
                self.post_process_func,
                self.post_process_func_args,
                self.post_process_progress,
                self.close_on_finish,
                None)

        self.ok_button=self.buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        self.cancel_button=self.buttons.button(QDialogButtonBox.Cancel)
        self.master.all_done_signal.connect(self.allJobsDone)

    def exec_(self):

        # have to start master first
        self.master.run()
        super(ThreadRunDialog,self).exec_()

        return


    @pyqtSlot()
    def allJobsDone(self):

        self.cancel_button.setEnabled(False)
        self.ok_button.setEnabled(True)
        self.label.setText('Finished')
        if self.close_on_finish:
            self.accept()

        return


    @pyqtSlot()
    def abortJobs(self):
        self.master.abortJobs()
        if self.get_results:
            self.results=self.master.results
        self.abort_job_signal.emit()
        self.reject()

        return


    @pyqtSlot()
    def accept(self):

        LOGGER.debug('get_results = %s' %self.get_results)
        if self.get_results:
            self.results=self.master.results
        super(self.__class__,self).accept()

        return


