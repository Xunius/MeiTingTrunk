import sys
import PyQt5
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from queue import Queue
import time

class Worker(QObject):
    sgnFinished = pyqtSignal()

    def __init__(self, parent, jobq, outq, func):
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
            #time.sleep(0.1)

            args=self.jobq.get()
            print('args=',args)
            rec=self.func(*args)
            self.jobq.task_done()
            self.outq.put(rec)
            time.sleep(0.1)
            print('doing work...')

        self.sgnFinished.emit()

def doJob(data_in):
    print('doJob: processing data',data_in)
    time.sleep(int(data_in))
    return data_in


def timeoutFunc(parent=None,func=None,jobq=None,outq=None,msec=4000):

    client = Client(None,func=func,jobq=jobq,outq=outq)

    timer=QTimer(parent)
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: client.toggle(False))
    client.toggle(True)
    timer.start(msec)

    print(client.results)


    return client



class Client(QObject):
    def __init__(self, parent, func, jobq, outq):
        QObject.__init__(self, parent)
        self._thread = None
        self._worker = None
        self.jobq=jobq
        self.outq=outq
        self.func=func

        self.results=[]

    def toggle(self, enable):
        if enable:
            if not self._thread:
                self._thread = QThread()

            self._worker = Worker(None,self.jobq,self.outq,self.func)
            self._worker.moveToThread(self._thread)
            self._worker.sgnFinished.connect(self.on_worker_done)

            self._thread.started.connect(self._worker.work)
            self._thread.start()
        else:
            print('stopping the worker object')
            self._worker.stop()

    @pyqtSlot()
    def on_worker_done(self):
        print('workers job was interrupted manually')
        self._thread.quit()
        self._thread.wait()
        #if raw_input('\nquit application [Yn]? ') != 'n':
        results=[]
        #while self.outq.qsize():
            #resii=self.outq.get()
            #results.append(resii)

        self.results=results
        qApp.quit()

if __name__ == '__main__':

    # prevent some harmless Qt warnings
    pyqtRemoveInputHook()

    app = QCoreApplication(sys.argv)

    '''
    client = Client(None)

    def start():
        timer=QTimer(app)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: client.toggle(False))
        client.toggle(True)
        timer.start(4000)
        #time.sleep(4)
        #QTimer.singleShot(4000,lambda:client.toggle(False))
        #raw_input('Press something\n')
        #client.toggle(False)
    '''

    jobq=Queue()
    outq=Queue()
    for ii in range(10):
        jobq.put((str(ii),))

    QTimer.singleShot(10, lambda:timeoutFunc(parent=app,jobq=jobq,
        outq=outq,func=doJob))
    #timeoutFunc()

    sys.exit(app.exec_())
