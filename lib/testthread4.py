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

    #print(client.results)


    return client



class Client(QObject):
    clientDone = pyqtSignal()

    def __init__(self, parent, func, jobq, outq):
        QObject.__init__(self, parent)
        self._thread = None
        self._worker = None
        self.jobq=jobq
        self.outq=outq
        self.func=func

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
        self.clientDone.emit()
        #self._thread.wait()
        #if raw_input('\nquit application [Yn]? ') != 'n':
        #results=[]
        #while self.outq.qsize():
            #resii=self.outq.get()
            #results.append(resii)

        #self.results=results
        #qApp.quit()


class MainWindow(QMainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
        frame=QWidget()
        self.setCentralWidget(frame)
        hl=QVBoxLayout()
        frame.setLayout(hl)

        self.startBtn=QPushButton()
        self.startBtn.setText('Start')
        self.startBtn.clicked.connect(self.pressedStartBtn)

        hl.addWidget(self.startBtn)

        self.show()

    def pressedStartBtn(self):

        self.jobq=Queue()
        self.outq=Queue()
        for ii in range(10):
            self.jobq.put((str(ii),))

        #QTimer.singleShot(10, lambda:timeoutFunc(parent=self,jobq=self.jobq,
            #outq=self.outq,func=doJob))

        #self.worker = WorkerThread(doJob,self.jobq,self.outq,self)
        #self.worker.start()
        #self.worker.wait(4000)

        client = Client(self,func=doJob,jobq=self.jobq,outq=self.outq)
        client.clientDone.connect(self.getResults)

        timer=QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: client.toggle(False))
        client.toggle(True)
        timer.start(4000)

        #client._thread.wait()

        #self.jobq.join()
    def getResults(self):
        results=[]
        while self.outq.qsize():
            resii=self.outq.get()
            results.append(resii)

        print('results:', results)


def main():
     # a new app instance
     app = QApplication(sys.argv)
     form = MainWindow()
     form.show()
     sys.exit(app.exec_())

if __name__ == "__main__":
     main()
