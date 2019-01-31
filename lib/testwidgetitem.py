import sys
from PyQt5.QtWidgets import QItemDelegate, QTreeWidget, QVBoxLayout, QLineEdit,\
        QMainWindow, QWidget, QTreeWidgetItem, QApplication
from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator, QValidator

class MyValidator(QValidator):
        def __init__(self, siblings, parent):
            super(MyValidator,self).__init__(parent)

            self.siblings = siblings

        def validate(self, s, pos):

            # look for invalid chars
            reg=QRegExp('[A-z0-9\[\]_-]+')
            regvd=QRegExpValidator(reg)

            regvd_rec=regvd.validate(s,pos)[0]
            print('regexp validate result:',regvd_rec)

            # check name conflicts
            '''
            if s in self.siblings:
                siblingvd_rec=0
            else:
                current_len=len(s)
                sub_strings=[sii[:current_len] for sii in self.siblings]
                if s in sub_strings:
                    siblingvd_rec=1
                else:
                    siblingvd_rec=2
            '''

            siblingvd_rec=2

            print('siblings validate result:',siblingvd_rec)

            if regvd_rec*siblingvd_rec==0:
                print('Invalid')
                return (QValidator.Invalid, s, pos)
            elif regvd_rec+siblingvd_rec==4:
                print('Acceptable')
                return (QValidator.Acceptable, s, pos)
            else:
                print('Intermediate')
                return (QValidator.Intermediate, s, pos)


        def fixup(self, s):
            pass



class TreeWidgetDelegate(QItemDelegate):
    def __init__(self, siblings, parent=None):
        QItemDelegate.__init__(self, parent=parent)
        self.siblings=siblings
        self.parent=parent

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        vd=MyValidator(self.siblings,self.parent)
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
        hl.addWidget(self.tree)

        # add treewidgetitems
        for ii in range(5):
            item=QTreeWidgetItem([str(ii)*3,])
            self.tree.addTopLevelItem(item)

        self.tree.itemDoubleClicked.connect(self.rename)
        self.tree.itemChanged.connect(self.checkName, Qt.QueuedConnection)

        self.show()

    def getSiblings(self,item):
        siblings=[self.tree.topLevelItem(ii).data(0,0) for ii in \
                range(self.tree.topLevelItemCount())]
        item_text=item.data(0,0)
        if item_text in siblings:
            siblings.remove(item_text)
        return siblings

    def rename(self):
        item=self.tree.selectedItems()
        if item:
            item=item[0]
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.tree.scrollToItem(item)

            dele=TreeWidgetDelegate(self.getSiblings(item),self)
            self.tree.setItemDelegate(dele)

            self.tree.editItem(item)

    def checkName(self,item,column):

        text=item.data(0,0)
        siblings=self.getSiblings(item)
        print('checkName: slibings:', siblings)

        if text in siblings:
            print('checkName: ivalid')
            item.setData(0,0,'New_name_needed')
            self.tree.editItem(item)



if __name__ == "__main__":
     app = QApplication(sys.argv)
     form = MainWindow()
     form.show()
     sys.exit(app.exec_())
