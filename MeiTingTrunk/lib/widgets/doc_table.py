'''
Widget for the doc table: a table model and a headerview.

MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

from datetime import datetime
import operator
import logging
from queue import Queue
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant, pyqtSignal,\
        pyqtSlot, QMimeData, QByteArray, QThread, QTimer
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon, QFont
from ..._MainFrameOtherSlots import SettingsThread


LOGGER=logging.getLogger(__name__)



class TableModel(QAbstractTableModel):

    sort_change_sig=pyqtSignal(int, int)  # column idx, sort order

    def __init__(self, parent, datain, headerdata, settings):
        '''
        Args:
            parent (QWidget): parent widget.
            datain (list): data for the table, a list of lists, each
                           element list for a row. Created by
                           _MainFrameLoadData.prepareDocs().
            headerdata (list): table column names.
            settings (QSettings): application settings. See _MainWindow.py
        '''

        QAbstractTableModel.__init__(self, parent)

        self.ncol=len(headerdata)
        if datain is None:
            self.arraydata=[None]*self.ncol
        else:
            self.arraydata=datain
        self.headerdata=headerdata
        self.settings=settings

        self.icon_section={
                'has_file': QIcon(':/file_icon.png')
                }
        self.check_section={
                'favourite': QPixmap(':/bf.png'),
                'read': QPixmap(':/clap.png')
                }
        self.icon_sec_indices=[self.headerdata.index(kk) for kk
                in self.icon_section.keys()]
        self.check_sec_indices=[self.headerdata.index(kk) for kk
                in self.check_section.keys()]

        self.sort_change_sig.connect(self.saveSort, Qt.QueuedConnection)


    def rowCount(self,p):
        return len(self.arraydata)


    def columnCount(self,p):
        return self.ncol


    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        #if role == Qt.BackgroundRole:
            #if index.row()%2==0:
                #return QBrush(QColor(230,230,249))
                #pass

        if role == Qt.FontRole:
            font=self.settings.value('display/fonts/doc_table',QFont)
            if self.arraydata[index.row()][9] in [None, 'false']:
                font.setBold(True)
            else:
                font.setBold(False)
            return font

        if role==Qt.DisplayRole:
            if index.column() in self.icon_sec_indices:
                return
            elif index.column()==self.headerdata.index('added'):
                added=self.arraydata[index.row()][index.column()]
                if added:
                    # convert time to str
                    added=int(added[:10])
                    added=datetime.fromtimestamp(added)
                    if added.year==datetime.today().year:
                        added=added.strftime('%b-%d')
                    else:
                        added=added.strftime('%b-%d-%y')
                    return QVariant(added)
                else:
                    return
            else:
                return QVariant(self.arraydata[index.row()][index.column()])

        if role==Qt.EditRole:
            return QVariant(self.arraydata[index.row()][index.column()])

        #if role==Qt.TextAlignmentRole:
            #return Qt.AlignCenter
        if index.column() in self.check_sec_indices and role==Qt.CheckStateRole:
            if self.arraydata[index.row()][index.column()].isChecked():
                return Qt.Checked
            else:
                return Qt.Unchecked
        if index.column() in self.icon_sec_indices and role==Qt.DecorationRole:
            if self.arraydata[index.row()][index.column()]:
                return self.icon_section['has_file']
            else:
                return None

        if role != Qt.DisplayRole:
            return QVariant()


    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if index.column() in self.check_sec_indices and role==Qt.CheckStateRole:
            if value == Qt.Checked:
                self.arraydata[index.row()][index.column()].setChecked(True)
            else:
                self.arraydata[index.row()][index.column()].setChecked(False)
        self.dataChanged.emit(index,index)

        return True


    def flags(self, index):
        if index.column() in self.check_sec_indices:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable\
                    | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |\
                    QtCore.Qt.ItemIsDragEnabled


    def headerData(self, col, orientation, role):

        if col in self.icon_sec_indices:
            label=self.headerdata[col]
            if orientation==Qt.Horizontal and role==Qt.DecorationRole:
                return self.icon_section[label]
        elif col in self.check_sec_indices:
            label=self.headerdata[col]
            if orientation==Qt.Horizontal and role==Qt.DecorationRole:
                return self.check_section[label]
        else:
            if orientation==Qt.Horizontal and role==Qt.DisplayRole:
                return self.headerdata[col]

        return None


    def sort(self,col,order):
        self.layoutAboutToBeChanged.emit()

        #NOTE that python3 doesn't support mixed type sorting (e.g. 1<None,
        # 'a' > 2. So convert everything to str.
        self.arraydata=sorted(self.arraydata,key=lambda x: \
                str(operator.itemgetter(col)(x)) or '')
        if order==Qt.DescendingOrder:
            self.arraydata.reverse()

        # for some reason there is always a lag if I do anything with settings
        # here. Therefore this short delay
        QTimer.singleShot(10, lambda: self.sort_change_sig.emit(col, order))
        self.layoutChanged.emit()

        return


    @pyqtSlot(int, int)
    def saveSort(self, col, order):
        '''Save sorting column and order to settings

        Args:
            col (int): column index to sort.
            order (int): sort order, 1=Qt.DescendingOrder, 0=Qt.AscendingOrder.
        '''

        self.setting_thread=SettingsThread(self.settings,
                'view/sortidx', col)
        self.setting_thread.start()
        self.setting_thread=SettingsThread(self.settings,
                'view/sortorder', order)
        self.setting_thread.start()
        LOGGER.debug('Saved sortidx = %s. sortorder = %s' %(col, order))

        return


    def mimeTypes(self):
        '''For drag/drop docs into folders'''

        return ['doc_table_item',]


    def mimeData(self,indices):
        '''For drag/drop docs into folders'''

        LOGGER.debug('header data = %s' %self.headerdata)
        LOGGER.debug('indices = %s' %indices)

        for idii in indices:
            LOGGER.debug('idii.row() = %s, idii.column() = %s, idii.data() = %s'\
                    %(idii.row(), idii.column(), idii.data()))

        ids=[ii for ii in indices if ii.isValid()]
        LOGGER.debug('ids = %s' %ids)

        rowids=[ii.row() for ii in ids]
        rowids=list(set(rowids))
        LOGGER.debug('rowids = %s' %rowids)

        encode_data=[str(self.arraydata[ii][0]) for ii in rowids]
        encode_data=', '.join(encode_data)
        LOGGER.debug('encode_data = %s, type() = %s' %(encode_data,
            type(encode_data)))

        encode_data_array=QByteArray()
        encode_data_array.append(encode_data)

        mimedata=QMimeData()
        mimedata.setData('doc_table_item',encode_data_array)

        return mimedata


class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)

        self.colSizes={'docid':0, 'favourite': 20, 'read': 20, 'has_file': 20,
            'author': 200, 'title': 500, 'journal':100,'year':50,'added':50,
            'confirmed':0}

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.sectionResized.connect(self.myresize)
        self.setStretchLastSection(False)
        self.setSectionsMovable(True)

    def initresizeSections(self):
        '''Initial resize columns

        The entire resizing logic is very confusing, I can't quite recall
        myself.

        The problem was: by default Qt doesn't let you resize each column's
        width, if you want the table widget to expand with its container.
        This is because there are only 4 resize modes for the headerview:
            * QHeaderView.Interactive
            * QHeaderView.Fixed
            * QHeaderView.Stretch
            * QHeaderView.ResizeToContents
        and they are mutually exclusive, i.e. you can't combine them like

            QHeaderView.Interactive | QHeaderView.Stretch

        Very annoying.
        The current solution is still not ideal.
        '''

        model=self.model()
        if model is None:
            return

        self.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        headers=model.headerdata

        for ii in range(self.count()):
            lii=headers[ii]
            sii=self.colSizes[lii]
            if lii in self.colSizes:
                self.setSectionResizeMode(ii, QtWidgets.QHeaderView.Fixed)
                self.resizeSection(ii,sii)
            else:
                self.setSectionResizeMode(ii, QtWidgets.QHeaderView.Stretch)
                wnow=self.sectionSize(ii)
                self.resizeSection(ii,wnow)
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Interactive)

        return


    def myresize(self, *args):
        '''Resize columns
        '''

        model=self.model()
        if model is None:
            return
        ws=[]
        for c in range(self.count()):
            wii=self.sectionSize(c)
            ws.append(wii)

        if args[0]>0 or args[0]<self.count():
            for ii in range(args[0],self.count()):
                lii=model.headerdata[ii]
                if lii in ['favourite','read','has_file']:
                    continue
                if ii==args[0]:
                    continue
                if ii==self.count()-1:
                    self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Stretch)
                else:
                    pass

        return


    def resizeEvent(self, event):

        super(QtWidgets.QHeaderView, self).resizeEvent(event)

        model=self.model()
        if model is None:
            return

        ws=[]
        perc=[]
        total_w=self.length() # width of the table
        total_w2=self.size().width()   # new available space after resizing
        for c in range(self.count()):
            wii=self.sectionSize(c)
            ws.append(wii)
            perc.append(float(wii)/total_w)

        headers=model.headerdata

        for ii in range(self.count()):
            lii=headers[ii]
            if lii in ['favourite','read','has_file']:
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Fixed)
                continue
            elif lii=='year':
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Stretch)
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Interactive)
            else:
                wnow=int(perc[ii]*total_w2)
                self.resizeSection(ii,wnow)
                self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Interactive)

        return


    def columnFromLabel(self, label):
        '''NOT IN USE'''
        headers=self.model().headerdata
        if label in headers:
            return headers.index(label)

        return -1

