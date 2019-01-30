import sys
from PyQt5.QtWidgets import QItemDelegate, QTreeWidget, QVBoxLayout, QLineEdit,\
        QMainWindow, QWidget, QTreeWidgetItem, QApplication
from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator


class TreeWidgetDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent=parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        reg=QRegExp('[A-z0-9\[\]_-]+')
        vd=QRegExpValidator(reg)

        editor.setValidator(vd)
        return editor


class MainWindow(QMainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
        frame=QWidget()
        self.setCentralWidget(frame)
        hl=QVBoxLayout()
        frame.setLayout(hl)

        self.tree=QTreeWidget(self)
        mydele=TreeWidgetDelegate()
        self.tree.setItemDelegate(mydele)
        hl.addWidget(self.tree)

        # add treewidgetitems
        for ii in range(5):
            item=QTreeWidgetItem([str(ii),])
            self.tree.addTopLevelItem(item)

        self.tree.itemDoubleClicked.connect(self.rename)
        self.tree.itemChanged.connect(self.checkString)

        dele=self.tree.itemDelegate()
        print('dele',dele)

        self.show()

    def rename(self):
        item=self.tree.selectedItems()
        if item:
            item=item[0]
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.tree.scrollToItem(item)
            self.tree.editItem(item)

    def checkString(self,item,column):
        text=item.data(0,column)
        print('text',text)

        invalid=['.', ':', '!']
        accepted=True
        for ii in invalid:
            if ii in text:
                accepted=False
                break

        if not accepted:
            print('invalid name')
            self.tree.editItem(item)


if __name__ == "__main__":
     app = QApplication(sys.argv)
     form = MainWindow()
     form.show()
     sys.exit(app.exec_())
