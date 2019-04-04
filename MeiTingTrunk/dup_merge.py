import sys
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QBrush, QTextCharFormat, QFont, QColor

import logging
LOGGER=logging.getLogger(__name__)


class DummyWidget(QtWidgets.QWidget):
    resize_sig=pyqtSignal(QSize)

    def __init__(self,parent=None):
        super(DummyWidget,self).__init__(parent)

    def resizeEvent(self,e):
        print('# <resizeEvent>: size hint=',self.sizeHint())
        super(DummyWidget,self).resizeEvent(e)
        self.resize_sig.emit(self.sizeHint())


class HighLighter(QSyntaxHighlighter):

    def __init__(self,match_words,parent=None):
        super(HighLighter,self).__init__(parent)

        brush=QBrush(Qt.yellow, Qt.SolidPattern)
        keyword=QTextCharFormat()
        keyword.setBackground(brush)
        keyword.setFontWeight(QFont.Bold)

        self.highlightingRules = [(QRegExp(key), keyword) for key in match_words]

    def highlightBlock(self, text):
        for pattern, tformat in self.highlightingRules:
            expression=QRegExp(pattern)
            index=expression.indexIn(text)

            while index >= 0:
              length = expression.matchedLength()
              self.setFormat(index, length, tformat)
              index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)




class AdjustableTextEdit(QtWidgets.QTextEdit):

    td_size_sig=pyqtSignal(QSize)
    def __init__(self,parent=None):
        super(AdjustableTextEdit,self).__init__(parent)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self.resizeTextEdit)
        self.document().documentLayout().documentSizeChanged.connect(
                self.resizeTextEdit)


    def setHighlightText(self, text):
        HighLighter([text,],self)
        return

    def resizeTextEdit(self):

        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)
        return

    def resizeEvent(self,e):
        super(AdjustableTextEdit,self).resizeEvent(e)
        self.td_size_sig.emit(QSize(self.sizeHint().width(),
            self.maximumHeight()))
        return


class AdjustableTextEditWithFold(AdjustableTextEdit):

    fold_change_signal=pyqtSignal(str,bool)
    fold_size_sig=pyqtSignal(QSize)
    def __init__(self,field,parent=None):
        super(AdjustableTextEditWithFold,self).__init__(parent)

        self.field=field
        self.is_fold=True
        self.fold_above_nl=2

        self.fold_button=QtWidgets.QToolButton()
        self.fold_button.setArrowType(Qt.DownArrow)
        font_height=self.fontMetrics().height()
        self.fold_button.setFixedWidth(int(font_height))
        self.fold_button.setFixedHeight(int(font_height))
        self.fold_button.clicked.connect(self.toggleFold)
        self.fold_button.setStyleSheet('''
        QToolButton {
            border: 1px solid rgb(190,190,190);
            background-color: rgb(190,190,190);
            border-radius: %dpx;
            color: white;
            }

        QToolButton:pressed {
            border-style: inset;
            }
        ''' %(int(font_height/2))
        )

        #self.foldText()
        #fontheight=self.fontMetrics().height()
        #margin=self.document().documentMargin()
        #self.setMinimumHeight(fontheight+2*margin)
        #self.setMaximumHeight(fontheight+2*margin)
        #self.is_fold=True
        #print('# <__init__>: fh=',fontheight,'margin',margin,self.maximumHeight())
        #self.fold_button.setText('+')

    def getNumberOfLines(self):
        fm=self.fontMetrics()
        doc=self.document()
        docheight=doc.size().height()
        margin=doc.documentMargin()
        nlines=(docheight-2*margin)/fm.height()

        return nlines

    def resizeTextEdit(self):
        print('# <resizeTextEdit>: nlines=',self.getNumberOfLines(),'isfold',self.is_fold)
        if self.getNumberOfLines()<self.fold_above_nl:
            self.fold_button.setVisible(False)
        else:
            self.fold_button.setVisible(True)
        if self.is_fold:
            self.foldText()
        else:
            self.unfoldText()

        return

    def toggleFold(self):
        self.unfoldText() if self.is_fold else self.foldText()
        #self.fold_change_signal.emit(self.field,self.is_fold)
        self.fold_size_sig.emit(QSize(self.sizeHint().width(),
            self.maximumHeight()))
        return

    def foldText(self):
        nlines=self.getNumberOfLines()
        print('# <foldText>: nline=',nlines)
        if nlines>=self.fold_above_nl:
            fontheight=self.fontMetrics().height()
            margin=self.document().documentMargin()
            self.setMinimumHeight(fontheight+2*margin)
            self.setMaximumHeight(fontheight+2*margin)
            self.is_fold=True
            self.fold_button.setArrowType(Qt.RightArrow)

        return

    def unfoldText(self):
        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)
        self.is_fold=False
        self.fold_button.setArrowType(Qt.DownArrow)
        return

class MainFrame(QtWidgets.QFrame):

    def __init__(self,parent=None):
        super(MainFrame,self).__init__(parent)

        '''
        ha=QtWidgets.QHBoxLayout(self)
        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(['aaa','bbb','ccc','ddd'])

        ha.addWidget(self.tree)

        self.text_edits=[]

        item1=QtWidgets.QTreeWidgetItem(['111','222','333','444'])
        self.tree.addTopLevelItem(item1)
        for ii in range(self.tree.columnCount()):
            item1.setBackground(ii, QColor(200,190,180))

        children1={'label1': 'very small text',
                'label2': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Maecenas et mauris in felis tempus molestie eu sit amet sapien. Proin dapibus pretium ipsum. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Pellentesque feugiat semper sem a accumsan. Nulla sollicitudin enim quis velit blandit posuere. Ut fringilla vulputate dolor, a accumsan lectus gravida a. Sed convallis facilisis mi et ullamcorper. Integer consectetur aliquet odio sit amet posuere.'
                }
        self.addChildrenRows(item1, children1)

        #item2=QtWidgets.QTreeWidgetItem(['111b','222b','333b','444b'])
        #self.tree.addTopLevelItem(item2)
        #self.addChildrenRows(item2, children1)
        self.show()

        #for tii in self.text_edits:
            #tii.foldText()
        '''

        #frame=QtWidgets.QWidget()
        #self.setWidgetResizable(True)
        #self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)

        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(7)
        self.tree.setColumnHidden(6,True)

        self.tree.setHeaderLabels(['Group', 'Authors', 'Title',
            'Publication', 'Year', 'Similarity','id'])
        self.tree.setColumnWidth(0, 55)
        self.tree.setColumnWidth(1, 250)
        self.tree.setColumnWidth(2, 300)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 50)
        self.tree.setColumnWidth(5, 20)
        self.tree.setColumnWidth(6, 0)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.tree.customContextMenuRequested.connect(self.docTreeMenu)

        self.noDupLabel=QtWidgets.QLabel('No duplicates found.')
        va.addWidget(self.noDupLabel)
        va.addWidget(self.tree)

        #frame.setLayout(va)

        meta1={'authors_l' : ['author1', 'author2', 'author3'],
                'title' : 'title 1',
                'publication' : 'nature',
                'year' : 1999
                }
        meta2={'authors_l' : ['author2', 'author3', 'author6'],
                'title' : 'title 2',
                'publication' : 'nature',
                'year' : 1999
                }
        meta3={'authors_l' : ['author3', 'author7', 'author1'],
                'title' : 'title 3',
                'publication' : '',
                'year' : 1999
                }
        meta4={'authors_l' : ['author1', 'author2', 'author3'],
                'title' : 'title 4',
                'publication' : 'science',
                'year' : 1999
                }


        docs=[
                (meta1, meta2, meta3, meta4),
                #(meta1, meta2, meta3, meta4),
                #(meta1, meta2, meta3, meta4)
                ]


        for ii, groupii in enumerate(docs):
            self.createGroup(groupii, ii+1)


        self.tree.expandAll()
        self.resize(1100,400)
        self.show()


    def createGroup(self,row_data,gid):

        fields=['authors_l', 'title', 'publication', 'year']

        def valueToStr(meta_dict,key):
            value=meta_dict[key]
            if key.endswith('_l'):
                value=', '.join(value)
            else:
                value=str(value)
            return value

        header=row_data[0]
        others=row_data[1:]
        header_data=[]
        #diff_fields=[]
        value_dict=OrderedDict()

        for kk in fields:
            headervv=valueToStr(header,kk)
            header_data.append(headervv)

            otherskk=[]
            for dii in others:
                vii=valueToStr(dii,kk)
                if vii != '':
                    otherskk.append(vii)

            value_set=list(set(otherskk+[headervv,]))
            if len(value_set)>1:
                #diff_fields.append(kk)
                value_dict[kk]=value_set

        print('header=',header_data)
        print('value_dict', value_dict)
        item=QtWidgets.QTreeWidgetItem([str(gid),]+header_data)
        self.tree.addTopLevelItem(item)

        self.addFieldRows(item, gid, value_dict)



        '''
        for ii in range(1,len(row_data)):
            rii=row_data[ii]
            rdataii=[rii[jj] if rii[jj]!=header[jj] else '' for jj in range(len(rii))]
            rdataii=list(map(str,rdataii))
            print('dataii=',rdataii)
            itemii=QtWidgets.QTreeWidgetItem([str(gid),]+rdataii)
            item.addChild(itemii)
        '''


    def addFieldRows(self, parent, gid, value_dict):
        '''Add detail rows to a matched doc

        Args:
            parent (QTreeWidgetItem): the header item showing a matched doc.
            fields (list): list of matched field names, including 'authors',
                           'title', 'keywords' etc..
            meta (DocMeta): meta data dict for the matched doc.
            search_text (str): searched text.

        A dummy container widget is created, inside which a grid layout is used
        to hold a number of rows, each being a matched field, e.g. 'authors',
        'title', etc.. Each row consists of a fold button to fold long texts,
        a label showing the field name, and a textedit showing the field value,
        with the <search_text> highlighted.

        The dummy container is then put in a QTreeWidgetItem by calling
        setItemWidget(). The item is added as a child of <parent>, which
        shows the matched doc in similar format as the doc table.
        '''

        #font=self.settings.value('display/fonts/doc_table',QFont)

        item=QtWidgets.QTreeWidgetItem()
        parent.addChild(item)
        item.setFirstColumnSpanned(True)

        frame=DummyWidget()
        grid=QtWidgets.QGridLayout(frame)
        crow=grid.rowCount()

        collect_dict={}
        button_le_dict={}


        fields=list(value_dict.keys())
        for ii, fii in enumerate(fields):

            valuesii=value_dict[fii]
            print('ii=',ii,'fii=',fii,'valuesii=',valuesii)
            #cdictii={}
            rgroup=QtWidgets.QButtonGroup(self) # NOTE: has to add self
            rgroup.setExclusive(True)
            collect_dict[fii]=rgroup

            for jj,vjj in enumerate(valuesii):

                radiojj=QtWidgets.QRadioButton()

                if jj==0:
                    labelii=QtWidgets.QLabel('%s: ' %fii)
                    grid.addWidget(labelii,crow,0)
                    radiojj.setChecked(True)

                #text_editjj=AdjustableTextEditWithFold()
                text_editjj=QtWidgets.QLineEdit()
                #text_editjj.setFont(font)
                text_editjj.setText(vjj)
                #text_editjj.setHighlightText(search_text)
                #grid.addWidget(text_editii.fold_button,crow,0)
                #grid.addWidget(labelii,crow,1)
                grid.addWidget(radiojj,crow,1)
                grid.addWidget(text_editjj,crow,2)
                rgroup.addButton(radiojj)
                #cdictii[radiojj]=text_editjj
                button_le_dict[radiojj]=text_editjj
                print('  jj=',jj,'vjj=',vjj,'crow=',crow)
                crow+=1

            '''
            radiojj=QtWidgets.QRadioButton()
            rgroup.addButton(radiojj)
            text_editjj=QtWidgets.QLineEdit()
            text_editjj.setReadOnly(True)
            text_editjj.setPlaceholderText('Clear Field')
            button_le_dict[radiojj]=text_editjj
            grid.addWidget(radiojj,crow,1)
            grid.addWidget(text_editjj,crow,2)

            radiojj=QtWidgets.QRadioButton()
            rgroup.addButton(radiojj)
            text_editjj=QtWidgets.QLineEdit()
            text_editjj.setPlaceholderText('Input new value here.')
            button_le_dict[radiojj]=text_editjj

            grid.addWidget(radiojj,crow,3)
            grid.addWidget(text_editjj,crow,4)

            crow+=1
            '''

            #print('fii=', fii, 'cdictii=', cdictii)

            if ii==len(fields)-1:
                confirm_button=QtWidgets.QToolButton(self)
                confirm_button.setText('Confirm')
                confirm_button.clicked.connect(lambda: self.confirmMerge(
                    gid, collect_dict, button_le_dict))

                grid.addWidget(confirm_button,crow-1,0)

            #text_editii.fold_size_sig.connect(lambda x: frame.resize(
                #frame.sizeHint()))

        self.tree.setItemWidget(item,0,frame)
        # add doc id to column 5
        #item.setText(5,str(meta['id']))
        frame.resize_sig.connect(lambda size: (item.setSizeHint(0,size),
            self.tree.model().layoutChanged.emit()))

        return

    @pyqtSlot(int, dict, dict)
    def confirmMerge(self, gid, collect_dict, button_le_dict):

        print('gid=',gid)
        for fii, rgroupii in collect_dict.items():
            print('fii=',fii, 'rgroupii=',rgroupii)

            checked=rgroupii.checkedButton()

            textii=button_le_dict[checked].text()
            print('checked=',checked, 'text=',textii)






    def addTextEditWidget(self,text,label,parent):

        #text_edit = AdjustableTextEdit()
        text_edit = AdjustableTextEditWithFold('a')
        #text_edit.setText(text)
        text_edit.setText('%s : %s' %(label,text))

        itemWidget = QtWidgets.QTreeWidgetItem()

        frame=DummyWidget()
        ha=QtWidgets.QHBoxLayout(frame)
        ha.addWidget(text_edit.fold_button)
        #qlabel=QtWidgets.QLabel(label)
        ha.addWidget(text_edit)
        #print('# <addTextEditWidget>: text=',text_edit.toPlainText())
        #itemWidget.setText(0, "")
        #itemWidget.setText(1, "")

        #self.tree.addTopLevelItem(itemWidget)
        parent.addChild(itemWidget)
        itemWidget.setFirstColumnSpanned(True)

        #self.tree.setItemWidget(itemWidget, 0, qlabel)
        #self.tree.setItemWidget(itemWidget, 0, text_edit.fold_button)
        self.tree.setItemWidget(itemWidget, 0, frame)
        #self.tree.setItemWidget(itemWidget, 0, frame)
        #text_edit.td_size_sig.connect(lambda size: itemWidget.setSizeHint(0,size))
        #text_edit.fold_size_sig.connect(lambda size: itemWidget.setSizeHint(0,size))
        frame.resize_sig.connect(lambda size: itemWidget.setSizeHint(0,size))

    def addChildrenRows(self, parent, fields):

        item=QtWidgets.QTreeWidgetItem()
        parent.addChild(item)
        item.setFirstColumnSpanned(True)

        frame=DummyWidget()
        grid=QtWidgets.QGridLayout(frame)

        crow=grid.rowCount()
        for kk, vv in fields.items():
            labelkk=QtWidgets.QLabel(kk)
            text_editkk=AdjustableTextEditWithFold(kk)
            text_editkk.setText(vv)
            text_editkk.setHighlightText('very')
            grid.addWidget(text_editkk.fold_button,crow,0)
            grid.addWidget(labelkk,crow,1)
            grid.addWidget(text_editkk,crow,2)

            text_editkk.fold_size_sig.connect(lambda x: frame.resize(
                frame.sizeHint()))

            self.text_edits.append(text_editkk)

            crow+=1

        self.tree.setItemWidget(item,0,frame)
        frame.resize_sig.connect(lambda size: (item.setSizeHint(0,size),
            self.tree.model().layoutChanged.emit()))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ui = MainFrame()
    sys.exit(app.exec_())
