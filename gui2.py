import sys
from PyQt5 import QtWidgets
from PyQt5.QtGui import QCursor, QHelpEvent
from PyQt5.QtCore import QPoint,QEvent,QRect,Qt,QTimer


class MyTextEdit(QtWidgets.QTextEdit):

    def __init__(self,parent=None):
        super(MyTextEdit,self).__init__(parent)

        self.label=QtWidgets.QLabel()
        self.label.setWindowFlags(Qt.SplashScreen)

        self.timer=QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.label.close)


    def focusInEvent(self,event):
        #he=QHelpEvent(QEvent.ToolTip,
                #QPoint(self.pos().x(),self.pos().y()),
                #QPoint(QCursor.pos()))
        #QtWidgets.QApplication.postEvent(self,he)

        #QtWidgets.QToolTip.hideText()
        #self.setToolTip('tooltip')
        #self.setToolTipDuration(5000)
        #QtWidgets.QToolTip.showText(QCursor.pos(), 'tooltip',self)
        #self.label.move(QCursor.pos()+QPoint(10,10))
        self.label.move(self.mapToGlobal(QPoint(self.width()//2, self.height()//2)))
        self.label.setText('test text')
        self.label.show()
        #self.timer.start()
        super(MyTextEdit,self).focusInEvent(event)


    def focusOutEvent(self,event):
        #self.timer.stop()
        self.label.close()
        super(MyTextEdit,self).focusOutEvent(event)

class MainFrame(QtWidgets.QWidget):

    def __init__(self):
        super(MainFrame,self).__init__()
        self.initUI()

    def initUI(self):


        self.te=MyTextEdit()
        self.te2=MyTextEdit()
        b=QtWidgets.QPushButton()
        b.clicked.connect(self.bclick)
        hlayout=QtWidgets.QHBoxLayout()
        hlayout.addWidget(self.te)
        hlayout.addWidget(self.te2)
        hlayout.addWidget(b)
        hlayout.addStretch()
        self.setLayout(hlayout)
        self.show()

    def bclick(self):
        #QtWidgets.QToolTip.showText(QCursor.pos(), 'tooltip',self,
                #QRect(10,10,10,10),5000)
        QtWidgets.QToolTip.showText(QCursor.pos(), 'tooltip',self,
                QRect(),5000)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow,self).__init__()

        self.main_frame=MainFrame()
        self.setCentralWidget(self.main_frame)
        self.setGeometry(100,100,800,600)
        self.show()


if __name__=='__main__':

    app=QtWidgets.QApplication(sys.argv)
    mainwindow=MainWindow()
    sys.exit(app.exec_())
