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

class Worder(QObject):



class WorkerThread(QThread):

    def __init__(self,func,jobqueue,outqueue,parent=None):
        QThread.__init__(self,parent)

        self.func=func
        self.jobqueue=jobqueue
        self.outqueue=outqueue
        #self.timer=QTimer()
        #self.timer.moveToThread(self)
        #self.timer.timeout.connect(self.stopthread)
        self._running=True

    def run(self):
        #self.timer.start(4000)
        #loop = QEventLoop()
        #loop.exec_()
        #self.exec_()
        while self._running:
            args=self.jobqueue.get()
            rec=self.func(*args)
            self.jobqueue.task_done()
            self.outqueue.put(rec)

    def stopthread(self):
        self._running=False
        print('stopthread called')
        self.outqueue.put(None)
        self.quit()


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

        for ii in range(20):
            self.jobq.put(str(ii))

        self.worker = WorkerThread(doJob,self.jobq,self.outq,self)
        self.worker.start()
        self.worker.wait(4000)

        results=[]
        while self.outq.qsize():
            resii=self.outq.get()
            results.append(resii)


def main():
     # a new app instance
     app = QApplication(sys.argv)
     form = MainWindow()
     form.show()
     sys.exit(app.exec_())

if __name__ == "__main__":
     main()
