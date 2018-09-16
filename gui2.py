import sys
import operator
from PyQt5 import QtWidgets
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant

def getXExpandYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy


class TableModel(QAbstractTableModel):
    def __init__(self, parent, datain, headerdata):
        super(TableModel,self).__init__(parent)

        self.arraydata=datain
        self.headerdata=headerdata

    def rowCount(self,p):
        return len(self.arraydata)

    def columnCount(self,p):
        if len(self.arraydata)>0:
            return len(self.arraydata[0])
        return 0

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(self.arraydata[index.row()][index.column()])

    def headerData(self, col, orientation, role):
        if orientation==Qt.Horizontal and role==Qt.DisplayRole:
            return self.headerdata[col]
        return None

    def sort(self,col,order):
        self.layoutAboutToBeChanged.emit()
        self.arraydata=sorted(self.arraydata,key=operator.itemgetter(col))
        if order==Qt.DescendingOrder:
            self.arraydata.reverse()
        self.layoutChanged.emit()

class MyTableView(QtWidgets.QTableView):

    def __init__(self,parent):
        #QtWidgets.QTableView.__init__(self, parent)
        super(MyTableView,self).__init__(parent)


    def resizeEvent(self, event):
        """ Resize all sections to content and user interactive """

        super(QtWidgets.QTableView, self).resizeEvent(event)
        header = self.horizontalHeader()
        #header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for column in range(header.count()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
            width = header.sectionSize(column)
            print 'column',column,'width',width
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
            header.resizeSection(column, width)

            width = header.sectionSize(column)
            print 'column',column,'width2',width

        #header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent,model):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)
        self.setModel(model)

    def myresize(self, *args):

        # keep a copy of column widths
        ws=[]
        for c in range(self.count()):
            wii=self.sectionSize(c)
            ws.append(wii)

        if args[0]>0 or args[0]<self.count():
            for ii in range(args[0],self.count()):
                if ii==args[0]:
                    # resize present column
                    self.resizeSection(ii,args[2])
                elif ii==args[0]+1:
                    # if present column expands, shrink the one to the right
                    self.resizeSection(ii,ws[ii]-(args[2]-args[1]))
                else:
                    # keep all others as they were
                    self.resizeSection(ii,ws[ii])

    def resizeEvent(self, event):

        super(QtWidgets.QHeaderView, self).resizeEvent(event)
        #self.setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch)
        for column in range(self.count()):
            self.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch)
            width = self.sectionSize(column)
            self.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
            self.resizeSection(column, width)

        #self.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        #self.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        return

class MainFrame(QtWidgets.QWidget):

    def __init__(self):
        super(MainFrame,self).__init__()
        self.initUI()

    def initUI(self):

        self.doc_table=self.createTable()
        dummy_box=QtWidgets.QLineEdit()

        hlayout=QtWidgets.QHBoxLayout()
        h_split=QtWidgets.QSplitter(Qt.Horizontal)
        h_split.addWidget(self.doc_table)
        h_split.addWidget(dummy_box)
        hlayout.addWidget(h_split)
        self.setLayout(hlayout)
        self.show()

    def createTable(self):
        # create some dummy data
        self.tabledata=[['aaa' ,' title1', True, 1999],
                    ['bbb' ,' title2', True, 2000],
                    ['ccc' ,' title3', False, 2001]
                    ]
        header=['author', 'title', 'read', 'year']

        tablemodel=TableModel(self,self.tabledata,header)
        tv=QtWidgets.QTableView(self)
        #tv=MyTableView(self)
        tv.setModel(tablemodel)
        #tv.sig.sig.connect(tv.resizeEvent)
        hh=MyHeaderView(tv,tablemodel)
        tv.setHorizontalHeader(hh)
        print 'clikc', hh.sectionsClickable()
        hh.setSectionsClickable(True)
        hh.setHighlightSections(True)
        print 'clikc2', hh.sectionsClickable()
        #hh=tv.horizontalHeader()
        #hh.setModel(tablemodel)
        hh.sectionResized.connect(hh.myresize)
        #hh.sectionResized.connect(lambda: myresize(hh))
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)

        hh.setSectionsMovable(True)
        hh.setStretchLastSection(False)
        # this may be optional:
        hh.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tv.setSortingEnabled(True)

        #tv.sig.sig.emit(None)

        return tv

    def myresize(self,*args):
        '''Resize while keep total width constant'''

        # keep a copy of column widths
        #sender=args[0]
        sender=self.sender()
        print sender
        print args
        ws=[]
        for c in range(sender.count()):
            wii=sender.sectionSize(c)
            ws.append(wii)

        if args[0]>0 or args[0]<sender.count():
            for ii in range(args[0],sender.count()):
                if ii==args[0]:
                    # resize present column
                    sender.resizeSection(ii,args[2])
                elif ii==args[0]+1:
                    # if present column expands, shrink the one to the right
                    sender.resizeSection(ii,ws[ii]-(args[2]-args[1]))
                else:
                    # keep all others as they were
                    sender.resizeSection(ii,ws[ii])


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
