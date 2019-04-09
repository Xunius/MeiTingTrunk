'''
Widgets for the folder tree: a QItemDelegate and a QTreeWidget


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import logging
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QRegExpValidator

LOGGER=logging.getLogger(__name__)



class TreeWidgetDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None):
        QtWidgets.QItemDelegate.__init__(self, parent=parent)

    def createEditor(self, parent, option, index):
        '''To disable typing in invalid chars in the folder name'''

        editor = QtWidgets.QLineEdit(parent)
        reg=QtCore.QRegExp('[A-z0-9\[\]_-\s]+')
        vd=QRegExpValidator(reg)
        editor.setValidator(vd)

        return editor

    '''
    def eventFilter(self, editor, event):
        # NOTE: possibly move the name conflict check inside
        print('# <eventFilter>: editor:', editor, 'event', event)


        if event.type()==QEvent.KeyPress:
            if event.key()==Qt.Key_Enter or event.key()==Qt.Key_Return:
                print('# <eventFilter>: Keypress', event.key())

                if editor.text()=='aaa':
                    return False
                self.commitData.emit(editor)
                self.closeEditor.emit(editor,0)
                return True
            else:
                return False
        else:
            return False
    '''


class MyTreeWidget(QtWidgets.QTreeWidget):

    folder_move_signal=pyqtSignal(str, str) # move_folder_id, new_parent_id
    folder_del_signal=pyqtSignal(QtWidgets.QTreeWidgetItem,  # move item
            QtWidgets.QTreeWidgetItem,  # newparent
            bool  # ask
            )
    add_doc_to_folder_signal=pyqtSignal(int, str)  # docid, folderid

    def __init__(self,parent=None):
        self.parent=parent
        super(MyTreeWidget,self).__init__(parent=parent)

        self.setDropIndicatorShown(True)
        self.setHeaderHidden(True)
        # column1: folder name, column2: folder id
        self.setColumnCount(2)
        self.hideColumn(1)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        # make horziontal scroll bar appear
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        delegate=TreeWidgetDelegate()
        self.setItemDelegate(delegate)


    def commitData(self,widget):
        '''Things to do after editing folder name

        itemChanged signal is connected to addNewFolderToDict to update the
        new folder name to storage. Then disconnect immediately.
        '''

        self.itemChanged.connect(self.parent.addNewFolderToDict, Qt.QueuedConnection)
        super(MyTreeWidget,self).commitData(widget)
        recs=self.receivers(self.itemChanged)

        LOGGER.debug('receivers of itemChanged signal = %s' %recs)
        if recs>0:
            self.itemChanged.disconnect()

        return


    def selectedIndexes(self):
        # to fix the issue of missing columns when setting DragDrop mode.
        return self.selectionModel().selectedIndexes()


    def startDrag(self,actions):

        move_item=self.selectedItems()[0]
        LOGGER.debug('move_item.data(0,0) = %s, move_item.data(1,0) = %s'\
                %(move_item.data(0,0), move_item.data(1,0)))

        self._move_item=move_item
        # abort if item is system folders
        if move_item.data(1,0) in ['-1','-2','-3']:
            return

        super(MyTreeWidget,self).startDrag(actions)


    def dragEnterEvent(self,event):

        #--------Deny dragging to all, needs review--------
        pos=event.pos()
        newparent=self.itemAt(pos)
        if newparent is not None and newparent.data(1,0) in ['-2','-1']:
            event.ignore()
            return

        mime_data=event.mimeData()
        LOGGER.debug('event.mimeData() = %s. mime_data.formats() = %s'\
                %(mime_data, mime_data.formats()))

        #----------------Dragging a doc row----------------
        if mime_data.hasFormat('doc_table_item'):
            trashed_folders=self.parent._trashed_folder_ids
            current_item=self.selectedItems()
            if current_item:
                current_item=current_item[0]

            #LOGGER.debug('folderid of current item = %s' %current_item.data(1,0))
            #LOGGER.debug('folderid of target item = %s' %newparent.data(1,0))

            if newparent is not None and current_item is not None and\
                    newparent.data(1,0) not in trashed_folders and\
                    current_item.data(1,0) in trashed_folders:
                event.setDropAction(Qt.MoveAction)

                #LOGGER.warning('Set drop action to Qt.MoveAction. Doesnt seem to work.')
            else:
                event.setDropAction(Qt.CopyAction)

            event.acceptProposedAction()

        #----------------Dragging a folder----------------
        elif mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):
            event.setDropAction(Qt.MoveAction)
            event.acceptProposedAction()
        else:
            event.ignore()

        return

    def dragMoveEvent(self,event):

        #--------Deny dragging to all, needs review--------
        pos=event.pos()
        newparent=self.itemAt(pos)
        if newparent is not None and newparent.data(1,0) in ['-2','-1']:
            event.ignore()
            return

        mime_data=event.mimeData()

        #----------------Dragging a doc----------------
        if mime_data.hasFormat('doc_table_item'):
            trashed_folders=self.parent._trashed_folder_ids
            current_item=self.selectedItems()
            if current_item:
                current_item=current_item[0]

            #LOGGER.debug('folderid of current item = %s' %current_item.data(1,0))
            #LOGGER.debug('folderid of target item = %s' %newparent.data(1,0))

            if newparent is not None and current_item is not None and\
                    newparent.data(1,0) not in trashed_folders and\
                    current_item.data(1,0) in trashed_folders:
                event.setDropAction(Qt.MoveAction)
                LOGGER.warning('Set drop action to Qt.MoveAction. Doesnt seem to work.')
            else:
                event.setDropAction(Qt.CopyAction)

            event.acceptProposedAction()

        #----------------Dragging a folder----------------
        elif mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):

            # deny droping to self
            pos=event.pos()
            newparent=self.itemAt(pos)
            if newparent==self._move_item:
                event.ignore()
                return

            event.setDropAction(Qt.MoveAction)
            event.acceptProposedAction()

            # need this to make dropIndicatorPosition work
            super(MyTreeWidget,self).dragMoveEvent(event)
        else:
            event.ignore()

        return


    def dropEvent(self,event):

        mime_data=event.mimeData()

        #------------------dropping a doc------------------
        if mime_data.hasFormat('doc_table_item'):
            # decode byte to str
            dropped_docids=mime_data.data('doc_table_item').data().decode('ascii')
            # if more than 1 doc dropping, is a string 'docid1, docid2, docid3...'
            dropped_docids=map(int, dropped_docids.split(','))
            pos=event.pos()
            newparent=self.itemAt(pos)

            if newparent is None:
                return

            parentidx=self.indexFromItem(newparent)

            LOGGER.debug('docid = %s. prarentid = %s.' %(dropped_docids,
                newparent.data(1,0)))

            if newparent.data(1,0) not in ['', '-2', '-1']:
                LOGGER.info('Doc drop valid. Emitting add_doc_to_folder_signal.')
                for docii in dropped_docids:
                    self.add_doc_to_folder_signal.emit(docii, newparent.data(1,0))

            return

        #----------------dropping a folder----------------
        elif mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):
            event.setDropAction(Qt.MoveAction)

            if self._move_item.data(1,0) in ['-1','-2','-3']:
                return

            pos=event.pos()
            newparent=self.itemAt(pos)

            if newparent is None:
                return

            parentidx=self.indexFromItem(newparent)
            indicatorpos=self.dropIndicatorPosition()

            LOGGER.debug('parentidx.row() = %s. newparent=data(0,0) = %s'\
                    %(parentidx.row(), newparent.data(0,0)))
            LOGGER.debug('dropIndicatorPosition = %s' %indicatorpos)

            #-----------------dropping on item-----------------
            if indicatorpos==0:

                if newparent.data(1,0) in ['-1', '-2']:
                    event.ignore()
                    return

                #----------------dropping to trash----------------
                elif newparent.data(1,0) in ['-3']+self.parent._trashed_folder_ids:

                    LOGGER.info('Dropping to trash a folder. Emitting folder_del_signal')
                    self.folder_del_signal.emit(self._move_item,newparent,True)

                    return

                # get children
                children=[newparent.child(ii) for ii in range(newparent.childCount())]
                children_names=[ii.data(0,0) for ii in children]
                LOGGER.debug('Got children names = %s' %children_names)

                # check name conflict
                if self._move_item.data(0,0) in children_names:

                    LOGGER.info('Found folder name conflict. Folder name = %s'\
                            %self._move_item.data(0,0))
                    event.ignore()
                    msg=QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setWindowTitle('Name conflict')
                    msg.setText('Move cancelled due to name conflict.')
                    msg.setInformativeText('Folder name\n\t%s\nconflicts with another folder in the target folder.\nPlease rename before moving.' %self._move_item.data(0,0))
                    msg.exec_()

                    return
                else:
                    # change folder parent
                    event.setDropAction(Qt.MoveAction)
                    LOGGER.info('Folder drop valid. Emit folder_move_signal')

                    self.folder_move_signal.emit(self._move_item.data(1,0),\
                            newparent.data(1,0))
                    super(MyTreeWidget,self).dropEvent(event)

                    return

            #--------------dropping above an item--------------
            elif indicatorpos==1:
                if parentidx.row()<=3:
                    event.ignore()
                    return
                else:
                    grandparent=newparent.parent()
                    if grandparent is None:
                        grandparentid='-1'
                    else:
                        grandparentid=grandparent.data(1,0)

                    event.setDropAction(Qt.MoveAction)
                    LOGGER.debug('grandparentid = %s' %grandparentid)
                    LOGGER.info('Folder drop valid. Emitting folder_move_signal.')

                    self.folder_move_signal.emit(self._move_item.data(1,0),\
                            grandparentid)
                    super(MyTreeWidget,self).dropEvent(event)

                    return

            #--------------dropping below an item--------------
            elif indicatorpos==2:
                if parentidx.row()<=2:
                    event.ignore()
                    return
                else:
                    grandparent=newparent.parent()
                    if grandparent is None:
                        grandparentid='-1'
                    else:
                        grandparentid=grandparent.data(1,0)

                    event.setDropAction(Qt.MoveAction)
                    LOGGER.debug('grandparentid = %s' %grandparentid)
                    LOGGER.info('Folder drop valid. Emitting folder_move_signal.')

                    self.folder_move_signal.emit(self._move_item.data(1,0),\
                            grandparentid)
                    super(MyTreeWidget,self).dropEvent(event)

                    return


