import sys
import PyQt5
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from queue import Queue
import time

def doJob(data_in):
    print('doJob: processing data',data_in)
    time.sleep(int(data_in))
    return data_in


class Worker(QObject):
    sgnFinished = pyqtSignal()

    def __init__(self, parent, func, jobq, outq):
        QObject.__init__(self, parent)
        self._mutex = QMutex()
        self._running = True

        self.func=func
        self.jobq=jobq
        self.outq=outq

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
            print('args=',args)
            rec=self.func(*args)
            self.jobq.task_done()
            self.outq.put(rec)
            time.sleep(0.1)
            print('doing work...')
        self.sgnFinished.emit()

class Client(QObject):
    def __init__(self, parent, func, jobq, outq):
        QObject.__init__(self, parent)
        self._thread = None
        self._worker = None

        self.func=func
        self.jobq=jobq
        self.outq=outq
        #self.timer=QTimer(None)
        #self.timer.setSingleShot(True)

    def toggle(self, enable):
        if enable:
            if not self._thread:
                self._thread = QThread()

            self._worker = Worker(None, self.func,self.jobq,self.outq)
            self._worker.moveToThread(self._thread)
            self._worker.sgnFinished.connect(self.on_worker_done)
            #self.timer.moveToThread(self._thread)
            #self.timer.timeout.connect(self._worker.stop)

            self._thread.started.connect(self._worker.work)
            #self.timer.start(4000)
            QTimer.singleShot(4000,self._worker.stop)
            self._thread.start()
            #print('timer.isActive',self.timer.isActive())
        else:
            print('stopping the worker object')
            self._worker.stop()

    def stopworker(self):
        print('stopping the worker object')
        self._worker.stop()

    @pyqtSlot()
    def on_worker_done(self):
        print('workers job was interrupted manually')
        self._thread.quit()
        self._thread.wait()
        #if raw_input('\nquit application [Yn]? ') != 'n':
        qApp.quit()

if __name__ == '__main__':

    # prevent some harmless Qt warnings
    #pyqtRemoveInputHook()

    app = QCoreApplication(sys.argv)
    jobq=Queue()
    outq=Queue()

    for ii in range(10):
        jobq.put((str(ii),))

    client = Client(app, doJob, jobq, outq)

    def start():
        #timer=QTimer()
        #timer.setSingleShot(True)
        #timer.timeout.connect(lambda:client.toggle(False))
        #timer.timeout.connect(client.stopworker)
        #timer.start(4000)

        client.toggle(True)
        #print('timer.isActive',timer.isActive())
        #time.sleep(2)
        #raw_input('Press something\n')
        #client.toggle(False)

    QTimer.singleShot(10, start)

    sys.exit(app.exec_())
