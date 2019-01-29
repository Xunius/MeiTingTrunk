import sys
import PyQt5
from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
from queue import Queue
import time
from PyQt5.QtCore import QThread, QObject, QMutex, pyqtSignal, pyqtSlot, QTimer

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
            time.sleep(0.1)
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

        client = Client(self,func=doJob,jobq=self.jobq,outq=self.outq,
                callback=self.getResults)

        client.start()
        QTimer.singleShot(4000,client.stop)

    def getResults(self):
        results=[]
        while self.outq.qsize():
            resii=self.outq.get()
            results.append(resii)

        print('results:', results)
        return results



if __name__ == "__main__":
     app = QApplication(sys.argv)
     form = MainWindow()
     form.show()
     sys.exit(app.exec_())
