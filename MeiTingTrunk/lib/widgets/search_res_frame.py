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

import os
import platform
from collections import OrderedDict
import logging
import subprocess
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QRegExp, QRect,\
        QPoint
from PyQt5.QtGui import QBrush, QColor, QFont, QSyntaxHighlighter,\
        QTextCharFormat, QFontMetrics
from PyQt5.QtWidgets import QDialogButtonBox
from .threadrun_dialog import Master
from .. import sqlitefts
from ..tools import iterTreeWidgetItems, isXapianReady, getSqlitePath
if isXapianReady():
    from .. import xapiandb


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

        self.highlightingRules = [(QRegExp(key, Qt.CaseInsensitive), keyword)\
                for key in match_words]

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
            self.setMinimumHeight(fontheight*(self.fold_above_nl-1)+2*margin)
            self.setMaximumHeight(fontheight*(self.fold_above_nl-1)+2*margin)
            self.is_fold=True
            self.fold_button.setArrowType(Qt.RightArrow)
        else:
            # dont understand, but this works
            fontheight=self.fontMetrics().height()
            margin=self.document().documentMargin()
            self.setMinimumHeight(fontheight*(self.fold_above_nl-1)+2*margin)
            self.setMaximumHeight(fontheight*(self.fold_above_nl-1)+2*margin)

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


    def addFieldRows(self, parent, fields, meta, pdf_match_dict, search_text):
        '''Add detail rows to a matched doc

        Args:
            parent (QTreeWidgetItem): the header item showing a matched doc.
            fields (list): list of matched field names, including 'authors',
                           'title', 'keywords' etc..
            meta (DocMeta): meta data dict for the matched doc.
            pdf_match_dict (dict or None): dict containing results in
                full text search, in the format of {rel_path1: snippet1,
                                                    rel_path2: snippet2,
                                                    ...
                                                    }.
                if None, skip.
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

        def openSnippetsDialog(snip_list, relpath):
            diag=SnippetsDialog(relpath, self.settings, self)
            diag.addSnippets(meta['title'], search_text, snip_list)
            diag.exec_()

            return

        def addField(label, text, crow, relpath=None):
            '''Add a field to grid layout

            Args:
                label (str): field name.
                text (str): search result text.
                crow (int): current row number of grid layout.
                relpath (str or None): relpath of PDF file. If not None, will
                                       create a button instead of a QLabel.
            '''

            if relpath is not None:
                labelii=QtWidgets.QPushButton('%s: ' %label)
                labelii.clicked.connect(lambda: self.openPDF(relpath))
                # if text is list, a list of snippets
                if isinstance(text, list):
                    snip_button=QtWidgets.QPushButton('Snippets')
                    snip_button.clicked.connect(lambda: openSnippetsDialog(
                        text, relpath))
            else:
                labelii=QtWidgets.QLabel('%s: ' %label)

            text_editii=AdjustableTextEditWithFold()
            text_editii.setReadOnly(True)
            text_editii.setFont(font)
            text_editii.setHighlightText(search_text)
            grid.addWidget(text_editii.fold_button,crow,1)

            if relpath is not None:
                if isinstance(text, list):
                    text_editii.fold_above_nl=3
                    text_editii.setText(text[0])
                    va=QtWidgets.QVBoxLayout()
                    va.addWidget(labelii)
                    va.addWidget(snip_button)
                    grid.addLayout(va,crow,0)
                else:
                    grid.addWidget(labelii,crow,0)
                    text_editii.setText(text)
            else:
                text_editii.setText(text)
                grid.addWidget(labelii,crow,0)

            grid.addWidget(text_editii,crow,2)

            text_editii.fold_size_sig.connect(lambda x: frame.resize(
                frame.sizeHint()))

            return


        for fii in fields:
            if fii=='authors':
                textii='; '.join(meta['authors_l'])
            elif fii=='title':
                textii=meta['title']
            elif fii=='publication':
                textii=meta['publication']
            elif fii=='keywords':
                textii='; '.join(meta['keywords_l'])
            elif fii=='tag':
                textii='; '.join(meta['tags_l'])
            elif fii=='abstract':
                textii=meta['abstract']
            elif fii=='note':
                textii=meta['notes']
            elif fii=='pdf':
                # add later
                continue
            else:
                LOGGER.warning('Wrong field given %s' %fii)
                raise Exception("Exception")

            addField(fii, textii, crow, None)
            crow+=1

        # add each matched pdf
        if 'pdf' in fields and pdf_match_dict is not None:
            for jj,(kk,vv) in enumerate(pdf_match_dict.items()):
                addField('File-%d' %(jj+1), vv, crow, kk)
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


    def search(self, db, text, field_list, folderid, meta_dict, folder_data,
            desend):
        """Start search

        Args:
            db (sqlite connection): sqlite connection.
            text (str): searched term.
            field_list (list): list of field names to search. Including
                'Authors', 'Title', etc.. The complete list see _MainFrame.py.
            folderid (str): id the folder. Search is done within docs in this
                 folder, also controled by <desend>.
            meta_dict (dict): dict of all meta data in the library.
            folder_data (dict): documents in each folder. keys: folder id in str,
                values: list of doc ids.
            desend (bool): whether to walk down the folder tree and include
                 subfolders of folder <folderid>.

        """

        self.tree.clear()
        self.setVisible(True)
        self.meta_dict=meta_dict
        self.folder_data=folder_data
        self.search_text=text
        self.desend=desend
        LOGGER.info('search text = %s. is desend = %s' %(text, desend))

        # Didn't put it to separate thread as access to sqlite db is restricted
        # to single thread.
        search_res, search_folderids=sqlitefts.searchMultipleLike2(db, text, field_list,
                folderid, desend)

        #def searchXapian(jobid, dbpath, querystring, fields, docids):
        sqlitepath=getSqlitePath(db)

        def searchXapian(jobid, dbpath, querystring, docids, sqlitepath ):
            try:
                #result=xapiandb.search(dbpath, querystring, fields,
                        #docids=docids)
                result=xapiandb.search2(dbpath, sqlitepath, querystring, docids)
                return 0, jobid, result
            except Exception:
                LOGGER.exception('Failed to call searchXapian.')
                return 1, jobid, None

        #---------------Do full text search---------------
        if 'PDF' in field_list:
            xapian_db=os.path.join(self.settings.value(
                'saving/current_lib_folder', type=str), '_xapian_db')

            # filter by docids
            if folderid=='-1':
                docids=None
            elif folderid=='-2':
                docids=self.folder_data['-2']
            else:
                docids=[]
                for fii in search_folderids:
                    docids.extend(self.folder_data[str(fii)])

            #self.master1=Master(searchXapian, [(0, xapian_db, text, ['pdf',],
            self.master1=Master(searchXapian, [(0, xapian_db, text,
                docids, sqlitepath)],
                    1, self.parent.progressbar,
                    'busy', self.parent.status_bar, 'Search PDFs...')
            self.master1.all_done_signal.connect(lambda: \
                    self.combineXapianResults(text, search_res))
            self.master1.run()
        #--------------Do only sqlite search--------------
        else:
            self.addResultToTree(text, search_res)

        return


    @pyqtSlot(str, list)
    def combineXapianResults(self, search_text, sqlite_results):
        '''Combine results from sqlite search with xapian search

        Args:
            search_text (str): searched term.
            sqlite_res (list): list of doc ids matching search from the sqlite
                search, together with the field names where the match is found.
                        E.g.
                        [(1, 'authors,title'),
                         (10, 'title,keywords'),
                         (214, 'abstract,tag'),
                         ...
                        ]
        '''

        rec, _, xapian_results=self.master1.results[0]
        # xapian_results: dict, key = docid_in_str, value: dict:
        #                       {relpath1: snippet1,
        #                        relpath2: snippet2,
        #                         ... }
        if rec==1:
            LOGGER.error('Failed to retrieve xapian search results.')
        else:
            sqlite_docs=[ii[0] for ii in sqlite_results]

            for idii in xapian_results.keys():
                idii=int(idii)
                if idii in sqlite_docs:
                    # if doc appear in sqlite search, add 'pdf' to its group
                    idx=sqlite_docs.index(idii)
                    sqlite_fields=sqlite_results[idx][1]
                    sqlite_results[idx]=(idii, '%s,pdf' %sqlite_fields)
                else:
                    # add new doc
                    sqlite_results.append((idii, 'pdf'))

            LOGGER.debug('Combined docs from sqlite and xapian search: %s'\
                    %sqlite_results)

        self.addResultToTree(search_text, sqlite_results, xapian_results)

        return


    def addResultToTree(self, search_text, sqlite_res, xapian_res=None):
        '''Add search results to a QTreeWidget for display

        Args:
            search_text (str): searched term.
            sqlite_res (list): list of doc ids matching search, together with
                the field names where the match is found. E.g.
                        [(1, 'authors,title'),
                         (10, 'title,keywords'),
                         (214, 'abstract,tag'),
                         ...
                        ]
        Kwargs:
            xapian_res (dict or None): full text search resutls from xapian.
                key = docid_in_str, value: dict:
                                  {relpath1: snippet1,
                                    relpath2: snippet2,
                                     ... }
                If None, xapian search was not performed.
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
        if len(sqlite_res)==0:
            self.noMatchLabel.setVisible(True)
            self.label.setText('No match found.')
            LOGGER.info('Not result found.')
            return

        self.noMatchLabel.setVisible(False)
        self.label.setText('%d searches results related to "%s"'\
                %(len(sqlite_res),search_text))

        #-------------Create entries for docs-------------
        for ii,recii in enumerate(sqlite_res):
            docii, fieldii=recii
            fieldii=list(set(fieldii.split(','))) # str to list
            itemii=createEntry(docii, str(ii+1))
            self.tree.addTopLevelItem(itemii)

            # get xapian search results for doc if exists
            if xapian_res is not None and docii in xapian_res:
                pdf_match_dict=xapian_res[docii]['pdf']
            else:
                pdf_match_dict=None

            # add group members
            self.addFieldRows(itemii, fieldii, self.meta_dict[docii],
                    pdf_match_dict, search_text)

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


    @pyqtSlot()
    def openPDF(self, relpath):
        '''Open pdf externally

        Args:
            relpath (str): relative path of PDF file.
        '''

        lib_folder=self.settings.value('saving/current_lib_folder', type=str)
        filepath=os.path.join(lib_folder, relpath)
        LOGGER.debug('Open file at path %s' %filepath)

        if not os.path.exists(filepath):
            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText("Can't find file.")
            msg.setInformativeText("No such file: %s. Please re-attach the document file." %filepath)
            msg.exec_()
            return

        current_os=platform.system()
        if current_os=='Linux':
            open_command='xdg-open'
        elif current_os=='Darwin':
            open_command='open'
        elif current_os=='Windows':
            raise Exception("Currently only support Linux and Mac.")
        else:
            raise Exception("Currently only support Linux and Mac.")

        LOGGER.info('OS = %s, open command = %s' %(current_os, open_command))

        try:
            subprocess.call((open_command, filepath))
        except Exception:
            LOGGER.exception('Failed to open file %s' %filepath)

            msg=QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText("Failed to open file")
            msg.setInformativeText("Failed to open file s" %filepath)
            msg.exec_()
            return

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




class SnippetsDialog(QtWidgets.QDialog):
    def __init__(self,relpath, settings,parent):
        '''
        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''

        super(SnippetsDialog,self).__init__(parent=parent)

        self.relpath=relpath
        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(700,800)
        self.setWindowTitle('Snippets')
        self.setWindowModality(Qt.ApplicationModal)

        # title label
        self.title_label=QtWidgets.QLabel('')
        self.title_label.setStyleSheet(self.label_color)
        self.title_label.setFont(self.title_label_font)
        self.title_label.setWordWrap(True)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(self.title_label)
        #ha.addStretch()
        #ha.addWidget(self.open_file_button, 0, Qt.AlignRight)

        # snip frame
        self.snip_frame=self.createSnipFrame()

        # dialog buttons
        self.buttons=QDialogButtonBox(Qt.Horizontal, self)
        self.cancel_button=self.buttons.addButton('Cancel',
                QDialogButtonBox.RejectRole)
        self.cancel_button.setAutoDefault(True)
        self.cancel_button.setDefault(True)
        self.cancel_button.setFocus()

        # open file button
        self.open_file_button=self.buttons.addButton('Open File',
                QDialogButtonBox.ApplyRole)
        self.open_file_button.setAutoDefault(False)
        self.open_file_button.setDefault(False)
        self.open_file_button.clicked.connect(lambda: self.parent.openPDF(
            self.relpath))

        self.buttons.rejected.connect(self.reject)

        self.v_layout=QtWidgets.QVBoxLayout(self)
        self.v_layout.addLayout(ha)
        self.v_layout.addWidget(self.snip_frame)
        self.v_layout.addWidget(self.buttons, 0, Qt.AlignRight)


    def createSnipFrame(self):

        frame=QtWidgets.QWidget(self)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        self.grid=QtWidgets.QGridLayout()
        self.grid.setContentsMargins(20,5,20,20)
        frame.setLayout(self.grid)
        #va.setSpacing(int(va.spacing()*2))

        return scroll


    def addSnippets(self, title, search_text, snip_list):

        font=self.settings.value('display/fonts/doc_table',QFont)
        self.title_label.setText('%s' %title)

        crow=0
        for ii, sii in enumerate(snip_list):
            labelii=QtWidgets.QLabel(str(ii+1))
            text_editii=AdjustableTextEdit()

            text_editii.setReadOnly(True)
            text_editii.setFont(font)
            text_editii.setText(sii)
            text_editii.setHighlightText(search_text)

            self.grid.addWidget(labelii,crow,0)
            self.grid.addWidget(text_editii,crow,1)

            crow+=1

        return



