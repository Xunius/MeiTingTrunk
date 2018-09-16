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
        print('sort')
        self.layoutAboutToBeChanged.emit()
        self.arraydata=sorted(self.arraydata,key=operator.itemgetter(col))
        if order==Qt.DescendingOrder:
            self.arraydata.reverse()
        self.layoutChanged.emit()

class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)

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
        tv.setModel(tablemodel)

        # Optional 1: use custom headerview, sorting not working
        hh=MyHeaderView(tv)
        #hh.setModel(tablemodel)
        tv.setHorizontalHeader(hh)
        hh.setSectionsClickable(True)
        hh.setHighlightSections(True)
        # Optional 2: get tableview's header, sorting works
        #hh=tv.horizontalHeader()

        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        hh.setSectionsMovable(True)
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch)
        #hh.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        tv.setSortingEnabled(True)
        #tv.setSizePolicy(getXExpandYExpandSizePolicy())
        #hh.setSizePolicy(getXExpandYExpandSizePolicy())

        return tv

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
