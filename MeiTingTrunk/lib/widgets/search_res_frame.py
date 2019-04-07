'''
Widgets for search computation and result display.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from collections import OrderedDict
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QRegExp, QRect,\
        QPoint
from PyQt5.QtGui import QBrush, QColor, QFont, QSyntaxHighlighter,\
        QTextCharFormat
#from PyQt5.QtWidgets import QDialogButtonBox
from .. import sqlitefts
from ..tools import iterTreeWidgetItems


LOGGER=logging.getLogger(__name__)



class DummyWidget(QtWidgets.QWidget):
    '''A dummy widget to hold the fold button, text label and textedit for a
    search result detail row
    '''

    resize_sig=pyqtSignal(QSize)

    def __init__(self,parent=None):
        super(DummyWidget,self).__init__(parent)

    def resizeEvent(self,e):
        super(DummyWidget,self).resizeEvent(e)
        self.resize_sig.emit(self.sizeHint())



class HighLighter(QSyntaxHighlighter):
    '''Highlight the search term in textedit'''

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
    '''This modified QTextEdit doesn't show scroll bar, but adjusts height
    acorrding to contents and width.
    '''

    td_size_sig=pyqtSignal(QSize)
    def __init__(self,parent=None):

        super(AdjustableTextEdit,self).__init__(parent)

        # pop up tooltip
        self.tooltip_label=QtWidgets.QLabel()
        self.tooltip_label.setWindowFlags(Qt.SplashScreen)
        self.tooltip_label.setMargin(3)
        self.tooltip_label.setStyleSheet('''
                background-color: rgb(235,225,120)
                ''')
        self.tooltip_text=''
        self.label_enabled=False

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self.resizeTextEdit)
        self.document().documentLayout().documentSizeChanged.connect(
                self.resizeTextEdit)


    def focusInEvent(self,event):

        #-----------------Pop up tool tip-----------------
        if self.label_enabled and self.tooltip_text:
            self.tooltip_label.move(self.mapToGlobal(
                QPoint(0, self.height()-70)))
            self.tooltip_label.setText(self.tooltip_text)
            self.tooltip_label.show()

        super(AdjustableTextEdit,self).focusInEvent(event)


    def focusOutEvent(self,event):

        #------------------Close tool tip------------------
        if self.label_enabled:
            self.tooltip_label.close()
        super(AdjustableTextEdit,self).focusOutEvent(event)


    def resizeTextEdit(self):
        '''Set textedit height according to contents'''

        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)

        return


    def resizeEvent(self,e):
        '''Send the current size via signal'''

        super(AdjustableTextEdit,self).resizeEvent(e)
        self.td_size_sig.emit(QSize(self.sizeHint().width(),
            self.maximumHeight()))

        return


    def setHighlightText(self, text_list):
        '''Highlight the search term'''

        if not isinstance(text_list, (tuple, list)):
            text_list=[text_list,]
        HighLighter(text_list, self)

        return


class AdjustableTextEditWithFold(AdjustableTextEdit):
    '''Adjustable textedit with a fold button to fold/expand long texts'''

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
        nlines=(docheight-2*margin)//fm.height()

        return nlines


    def resizeTextEdit(self):
        '''Show/hide fold button according to number of lines in text'''

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
        else:
            # dont understand, but this works
            fontheight=self.fontMetrics().height()
            margin=self.document().documentMargin()
            self.setMinimumHeight(fontheight+2*margin)
            self.setMaximumHeight(fontheight+2*margin)

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
    '''To show borders in treewidget item.
    NOT IN USE
    '''

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
    create_folder_sig=pyqtSignal(str,list)  # search_text, docids
    MyBorderRole = Qt.UserRole + 1  # not in use

    def __init__(self,settings,parent=None):
        '''Handles text searching and result display

        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''
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
        # put doc id in column 5. This is later used to identify selected docs.
        self.tree.setColumnHidden(5,True)

        # column widths
        headers=OrderedDict([
            ('Fold all', 70),
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
        self.tree.header().setSectionsClickable(True)
        self.tree.header().sectionClicked.connect(self.headerSectionClicked)
        self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        #self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.itemSelectionChanged.connect(self.changeBGColor)

        self.is_all_fold=False

        self.noMatchLabel=QtWidgets.QLabel('No match found.')
        self.noMatchLabel.setVisible(False)
        va.addWidget(self.noMatchLabel)
        va.addWidget(self.tree)

        frame.setLayout(va)


    def createClearSearchFrame(self):
        '''Create a header frame showing search term, results count and control
        buttons'''

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
                LOGGER.warning('Wrong field given %s' %fii)
                raise Exception("Exception")

            labelii=QtWidgets.QLabel('%s: ' %fii)
            text_editii=AdjustableTextEditWithFold()
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
        # add doc id to column 5
        item.setText(5,str(meta['id']))
        frame.resize_sig.connect(lambda size: (item.setSizeHint(0,size),
            self.tree.model().layoutChanged.emit()))

        return


    def changeBGColor(self):
        '''Change background color of QTreeWidgetItem

        This makes the header row of a doc, and all detail rows (child items
        of the header row) appeared to be selected together, by giving them
        a highlight color. Selecting either the header row or any child row
        makes them all highlighted.
        '''

        sel_rows=self.tree.selectedItems()
        hlcolor=self.tree.palette().highlight().color().name()

        docids=[itemii.data(5,0) for itemii in sel_rows]
        root=self.tree.invisibleRootItem()

        # set all widgetitems with selected docids selected.
        for item in iterTreeWidgetItems(self.tree, root):
            idii=item.data(5,0)
            if idii in docids:
                # I thought this would results in endless loop, but it doesn't!
                item.setSelected(True)

            # child detail rows has item widget
            wii=self.tree.itemWidget(item,0)
            if wii:
                if idii in docids:
                    wii.setStyleSheet('background-color: %s;' %hlcolor)
                else:
                    wii.setStyleSheet('')

        return


    def search(self, db, text, field_list, folderid, meta_dict, desend):
        """Start search

        Args:
            db (sqlite connection): sqlite connection.
            text (str): searched term.
            field_list (list): list of field names to search. Including
                'Authors', 'Title', etc.. The complete list see _MainFrame.py.
            folderid (str): id the folder. Search is done within docs in this
                 folder, also controled by <desend>.
            meta_dict (dict): dict of all meta data in the library.
            desend (bool): whether to walk down the folder tree and include
                 subfolders of folder <folderid>.

        """

        self.tree.clear()
        self.setVisible(True)
        self.meta_dict=meta_dict
        self.search_text=text
        self.desend=desend
        LOGGER.info('search text = %s. is desend = %s' %(text, desend))

        search_res=sqlitefts.searchMultipleLike2(db, text, field_list,
                folderid, desend)
        self.label.setText('%d searches results related to "%s"'\
                %(len(search_res),text))
        self.addResultToTree(text, search_res)

        return


    def addResultToTree(self, search_text, search_res):
        '''Add search results to a QTreeWidget for display

        Args:
            search_text (str): searched term.
            search_res (list): list of doc ids matching search, together with
                the field names where the match is found. E.g.
                        [(1, 'authors,title'),
                         (10, 'title,keywords'),
                         (214, 'abstract,tag'),
                         ...
                        ]
        '''

        def createEntry(docid, gid):
            '''Create an entry for a matched doc

            Args:
                docid (int): id of matched doc.
                gid (int): counter of the current doc.
            '''

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

        #-------------------If no match-------------------
        if len(search_res)==0:
            self.noMatchLabel.setVisible(True)
            LOGGER.info('Not result found.')
            return

        self.noMatchLabel.setVisible(False)

        #-------------Create entries for docs-------------
        for ii,recii in enumerate(search_res):
            docii, fieldii=recii
            fieldii=list(set(fieldii.split(','))) # str to list
            itemii=createEntry(docii, str(ii+1))
            self.tree.addTopLevelItem(itemii)

            # add group members
            self.addFieldRows(itemii, fieldii, self.meta_dict[docii],
                    search_text)

        self.tree.expandAll()

        # highlight header rows
        hi_color=self.settings.value('display/folder/highlight_color_br',
                QBrush).color().name()

        self.tree.setStyleSheet('''
        QTreeWidget::item:has-children:!selected {
        border-left: 1px solid black;
        border-bottom: 1px solid black;
        background-color: %s;
        }
        ''' %hi_color)

        self.search_done_sig.emit() # trigger main_frame.status_bar.clearMessage()

        return


    @pyqtSlot()
    def createFolder(self):
        '''Send signal to create a folder for selected search results'''

        sel_rows=self.tree.selectedItems()
        if len(sel_rows)>0:
            docids=[]
            for ii in sel_rows:
                docids.append(int(ii.data(5,0)))
            docids=list(set(docids))
            LOGGER.info('Selected docids=%s.' %docids)
            self.create_folder_sig.emit(self.search_text, docids)

        return


    @pyqtSlot(int)
    def headerSectionClicked(self,idx):
        '''Expand/fold all docs on clicking header 0'''

        if idx==0:
            if self.is_all_fold:
                LOGGER.debug('fold all')

                for ii in range(self.tree.topLevelItemCount()):
                    itemii=self.tree.topLevelItem(ii)
                    self.tree.expandItem(itemii)
                self.is_all_fold=False
                self.tree.setHeaderLabels(['Fold all', 'Authors', 'Title',
                    'Publication', 'Year', 'id'])
            else:
                LOGGER.debug('expand all')

                for ii in range(self.tree.topLevelItemCount()):
                    itemii=self.tree.topLevelItem(ii)
                    self.tree.collapseItem(itemii)
                self.is_all_fold=True
                self.tree.setHeaderLabels(['Unfold all', 'Authors', 'Title',
                    'Publication', 'Year', 'id'])

