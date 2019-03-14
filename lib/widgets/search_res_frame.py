from collections import OrderedDict
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QRegExp, QRect
from PyQt5.QtGui import QBrush, QColor, QIcon, QCursor, QFont, \
        QSyntaxHighlighter, QTextCharFormat, QPen
from PyQt5.QtWidgets import QDialogButtonBox
import resources
from .. import sqlitefts


LOGGER=logging.getLogger('default_logger')



class DummyWidget(QtWidgets.QWidget):
    resize_sig=pyqtSignal(QSize)

    def __init__(self,parent=None):
        super(DummyWidget,self).__init__(parent)

    def resizeEvent(self,e):
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

    def setHighlightText(self, text_list):
        if not isinstance(text_list, (tuple, list)):
            text_list=[text_list,]
        HighLighter(text_list, self)
        return

class AdjustableTextEditWithFold(AdjustableTextEdit):

    fold_size_sig=pyqtSignal(QSize)
    def __init__(self,parent=None):
        super(AdjustableTextEditWithFold,self).__init__(parent)

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

    def getNumberOfLines(self):
        fm=self.fontMetrics()
        doc=self.document()
        docheight=doc.size().height()
        margin=doc.documentMargin()
        nlines=(docheight-2*margin)/fm.height()

        return nlines

    def resizeTextEdit(self):
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
        self.fold_size_sig.emit(QSize(self.sizeHint().width(),
            self.maximumHeight()))
        return

    def foldText(self):
        nlines=self.getNumberOfLines()
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



class BorderItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent, borderRole):
        super(BorderItemDelegate, self).__init__(parent)
        self.borderRole = borderRole

    def sizeHint(self, option, index):
        size = super(BorderItemDelegate, self).sizeHint(option, index)
        pen = index.data(self.borderRole)
        if pen is not None:
            # Make some room for the border
            # When width is 0, it is a cosmetic pen which
            # will be 1 pixel anyways, so set it to 1
            width = max(pen.width(), 1)
            size = size + QSize(2 * width, 2 * width)
        return size

    def paint(self, painter, option, index):
        pen = index.data(self.borderRole)
        # copy the rect for later...
        rect = QRect(option.rect)
        if pen is not None:
            width = max(pen.width(), 1)
            # ...and remove the extra room we added in sizeHint...
            option.rect.adjust(width, width, -width, -width)

        # ...before painting with the base class method...
        super(BorderItemDelegate, self).paint(painter, option, index)

        # ...then paint the borders
        if pen is not None:
            painter.save()
            # The pen is drawn centered on the rectangle lines
            # with pen.width()/2 width on each side of these lines.
            # So, rather than shifting the drawing of pen.width()/2
            # we double the pen width and clip the part that would
            # go outside the rect.
            painter.setClipRect(rect, Qt.ReplaceClip);
            pen.setWidth(2 * width)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.restore()




class SearchResFrame(QtWidgets.QScrollArea):

    search_done_sig=pyqtSignal()
    #hide_doc_sig=pyqtSignal()
    create_folder_sig=pyqtSignal(str,list)
    MyBorderRole = Qt.UserRole + 1

    def __init__(self,settings,parent=None):
        super(SearchResFrame,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        frame=QtWidgets.QWidget()
        self.setWidgetResizable(True)
        self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)

        #----------------Create clear frame----------------
        va.addWidget(self.createClearSearchFrame())

        #----------------Create treewidget----------------
        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(6)
        self.tree.setColumnHidden(5,True)

        headers=OrderedDict([
            (' ', 50),
            ('Authors', 150),
            ('Title', 300),
            ('Publication', 100),
            ('Year', 50),
            ('id', 0)
            ])

        self.tree.setHeaderLabels(headers.keys())
        for ii,kk in enumerate(headers.keys()):
            self.tree.setColumnWidth(ii, headers[kk])

        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(True)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        #self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.tree.customContextMenuRequested.connect(self.docTreeMenu)

        self.noMatchLabel=QtWidgets.QLabel('No match found.')
        va.addWidget(self.noMatchLabel)
        va.addWidget(self.tree)

        frame.setLayout(va)

    def createClearSearchFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        ha=QtWidgets.QHBoxLayout()

        # create folder button
        self.create_folder_button=QtWidgets.QToolButton(self)
        self.create_folder_button.setText('Create Folder From Selection')
        self.create_folder_button.clicked.connect(self.createFolder)

        # hide doc table button
        #self.hide_doc_table_button=QtWidgets.QToolButton(self)
        #self.hide_doc_table_button.setText('Hide Document Table')
        #self.hide_doc_table_button.clicked.connect(lambda: self.hide_doc_sig.emit())

        # clear button
        self.clear_searchres_button=QtWidgets.QToolButton(self)
        self.clear_searchres_button.setText('Close')

        self.label=QtWidgets.QLabel('Search results')
        ha.addWidget(self.label)
        ha.addWidget(self.create_folder_button)
        #ha.addWidget(self.hide_doc_table_button)
        ha.addWidget(self.clear_searchres_button)

        frame.setLayout(ha)

        return frame


    def addFieldRows(self, parent, fields, meta, search_text):

        font=self.settings.value('display/fonts/doc_table',QFont)

        item=QtWidgets.QTreeWidgetItem()
        parent.addChild(item)
        item.setFirstColumnSpanned(True)

        frame=DummyWidget()
        grid=QtWidgets.QGridLayout(frame)
        crow=grid.rowCount()

        for fii in fields:

            if fii=='authors':
                textii=', '.join(meta['authors_l'])
            elif fii=='title':
                textii=meta['title']
            elif fii=='publication':
                textii=meta['publication']
            elif fii=='keywords':
                textii=', '.join(meta['keywords_l'])
            elif fii=='tag':
                textii=', '.join(meta['tags_l'])
            elif fii=='abstract':
                textii=meta['abstract']
            elif fii=='note':
                textii=meta['notes']
            else:
                print('# <createEntry>: fii',fii)
                raise Exception("Exception")

            labelii=QtWidgets.QLabel('%s: ' %fii)
            text_editii=AdjustableTextEditWithFold(fii)
            text_editii.setFont(font)
            text_editii.setText(textii)
            text_editii.setHighlightText(search_text)
            grid.addWidget(text_editii.fold_button,crow,0)
            grid.addWidget(labelii,crow,1)
            grid.addWidget(text_editii,crow,2)

            text_editii.fold_size_sig.connect(lambda x: frame.resize(
                frame.sizeHint()))
            crow+=1

        self.tree.setItemWidget(item,0,frame)
        frame.resize_sig.connect(lambda size: (item.setSizeHint(0,size),
            self.tree.model().layoutChanged.emit()))

        return


    def search(self,db,text,field_list,folderid,meta_dict):

        self.tree.clear()
        self.setVisible(True)
        self.meta_dict=meta_dict
        self.search_text=text

        search_res=sqlitefts.searchMultipleLike(db, text, field_list, folderid)
        self.label.setText('%d searches results related to "%s"'\
                %(len(search_res),text))
        self.addResultToTree(text, search_res)

        return


    def addResultToTree(self, search_text, search_res):

        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush)

        def createEntry(docid, gid):

            meta=self.meta_dict[docid]
            item=QtWidgets.QTreeWidgetItem([
                gid,
                ', '.join(meta['authors_l']),
                meta['title'],
                meta['publication'],
                str(meta['year']),
                str(docid)
                ])
            return item

        if len(search_res)==0:
            self.noMatchLabel.setVisible(True)
            return

        self.noMatchLabel.setVisible(False)

        #--------------------Get groups--------------------
        for ii,recii in enumerate(search_res):
            docii, fieldii=recii
            fieldii=list(set(fieldii.split(',')))

            itemii=createEntry(docii, str(ii+1))
            # highlight group header
            #pen = QPen(QColor(120, 120, 120))
            #pen.setWidth(1)
            # Store the border pen in the item as the role we defined
            for jj in range(self.tree.columnCount()):
                #itemii.setBackground(jj, hi_color)
                #itemii.setBackground(jj, QColor(200,190,180))
                #itemii.setData(jj, self.MyBorderRole, pen)
                pass

            self.tree.addTopLevelItem(itemii)

            # add group members
            self.addFieldRows(itemii, fieldii, self.meta_dict[docii], search_text)

        self.tree.expandAll()

        color=hi_color.color().getRgb()
        color_str='rgb(%s)' %','.join(map(str,color))

        self.tree.setStyleSheet('''
        QTreeWidget::item:has-children { border-left: 1px solid black;
        background-color: %s;}
        ''' %color_str)

        # Pass the role where we stored the border pen to the delegate constructor
        #delegate = BorderItemDelegate(self.tree, self.MyBorderRole)
        #self.tree.setItemDelegate(delegate)

        self.search_done_sig.emit()

        return


    def docTreeMenu(self,pos):

        menu=QtWidgets.QMenu()

        print('# <docTreeMenu>: current_folder=',self.current_folder)
        foldername,folderid=self.current_folder
        if folderid=='-1':
            menu.addAction('Delete From Library')
        else:
            menu.addAction('Delete From Current Folder')

        action=menu.exec_(QCursor.pos())

        if action:
            self.delDocs()

        return


    @pyqtSlot()
    def createFolder(self):
        sel_rows=self.tree.selectedItems()
        if len(sel_rows)>0:

            docids=[]
            for ii in sel_rows:
                idii=ii.data(5,0)
                if idii:
                    docids.append(int(idii))

            print('# <createFolder>: Selected docids=%s.' %docids)
            LOGGER.info('Selected docids=%s.' %docids)

        self.create_folder_sig.emit(self.search_text, docids)

        return
