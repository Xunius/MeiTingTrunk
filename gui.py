import sys,os
import operator
import sqlite3
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QPixmap, QIcon, QFont, QBrush, QColor
import tempfile
import subprocess
import json

__version__='v0.1'

FILE_IN='new.sqlite'

def dirFind(string,obj,num=10,verbose=True):
    '''Fuzzy search dir(obj)

    <string>: string, keyword to search.
    <obj>: python obj other than None.
    <num>: int, number of best matches to display.

    Function takes the keyword and compares it with the strings in dir(obj).
    Comparison is done using Levenshtein distance algorithm implemented in
    the fuzzywuzzy module.

    Usage:

    To show all get functions of an instance:
        dirFind('get',inst)

    Update time: 2016-02-11 13:09:14.
    '''

    import numpy
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        from fuzzywuzzy import fuzz

    dirlist=numpy.array(dir(obj))
    scores=numpy.array([fuzz.partial_ratio(string,ii) for ii in dirlist])
    idx=numpy.argsort(scores)[::-1]
    dirlist=dirlist[idx]
    scores=numpy.sort(scores)[::-1]

    #----Make sure all highly matched are included----
    high=numpy.where(scores>=90)[0]

    num=max([num,len(high)])

    print '\n# <dirFind>: %-20.40s    %s' %('<obj> element:','Score:')
    print '-'*70
    for ii in range(num):
        print '# <dirFind>: %-20.40s    %d' %(dirlist[ii],scores[ii])

    return

def getMinSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum)
    return sizePolicy

def getXMinYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy

def getXExpandYExpandSizePolicy():
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
    return sizePolicy

def getHSpacer():
    h_spacer = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum)
    return h_spacer

def getVSpacer():
    v_spacer = QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
    return v_spacer

def getVLine(parent):
    v_line = QtWidgets.QFrame(parent)
    v_line.setFrameShape(QtWidgets.QFrame.VLine)
    v_line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return v_line

def getHLine(parent):
    h_line = QtWidgets.QFrame(parent)
    h_line.setFrameShape(QtWidgets.QFrame.HLine)
    h_line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return h_line


class TableModel(QAbstractTableModel):
    def __init__(self, parent, datain, headerdata):
        QAbstractTableModel.__init__(self, parent)

        self.ncol=len(headerdata)
        if datain is None:
            self.arraydata=[None]*self.ncol
        else:
            self.arraydata=datain
        self.headerdata=headerdata

        self.icon_section={
                'favourite': QPixmap('./bf.jpg'),
                'read': QPixmap('./read.jpg')
                }
        self.icon_sec_indices=[self.headerdata.index(kk) for kk
                in self.icon_section.keys()]

    def rowCount(self,p):
        return len(self.arraydata)

    def columnCount(self,p):
        #if len(self.arraydata)>0:
            #return len(self.arraydata[0])
        #return 0
        return self.ncol

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        if role == Qt.BackgroundRole:
            if index.row()%2==0:
                return QBrush(QColor(230,230,240))
        if role==Qt.DisplayRole:
            return QVariant(self.arraydata[index.row()][index.column()])
        if role==Qt.EditRole:
            return QVariant(self.arraydata[index.row()][index.column()])

        if index.column() in self.icon_sec_indices and role==Qt.CheckStateRole:
            if self.arraydata[index.row()][index.column()].isChecked():
                return Qt.Checked
            else:
                return Qt.Unchecked

        if role != Qt.DisplayRole:
            return QVariant()

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if index.column() in self.icon_sec_indices and role==Qt.CheckStateRole:
            if value == Qt.Checked:
                self.arraydata[index.row()][index.column()].setChecked(True)
            else:
                self.arraydata[index.row()][index.column()].setChecked(False)

        self.dataChanged.emit(index,index)
        return True

    def flags(self, index):
        if not index.isValid():
            return None
        if index.column() in self.icon_sec_indices:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable\
                    | QtCore.Qt.ItemIsUserCheckable
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


    def headerData(self, col, orientation, role):

        if col in self.icon_sec_indices:
            label=self.headerdata[col]
            if orientation==Qt.Horizontal and role==Qt.DecorationRole:
                return self.icon_section[label]
        else:
            if orientation==Qt.Horizontal and role==Qt.DisplayRole:
                return self.headerdata[col]
        return None

    def sort(self,col,order):
        self.layoutAboutToBeChanged.emit()
        self.arraydata=sorted(self.arraydata,key=operator.itemgetter(col))
        if order==Qt.DescendingOrder:
            self.arraydata.reverse()
        self.layoutChanged.emit()



class MyHeaderView(QtWidgets.QHeaderView):
    def __init__(self,parent):
        super(MyHeaderView,self).__init__(Qt.Horizontal,parent)

        self.colSizes={'favourite': 20, 'read': 20, 'author': 200, 'title': 500,
                'journal':100,'year':50}


    def initresizeSections(self):
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



    def myresize(self, *args):

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
                if lii in ['favourite','read']:
                    continue
                if ii==args[0]:
                    continue
                if ii==self.count()-1:
                    self.setSectionResizeMode(ii,QtWidgets.QHeaderView.Stretch)
                else:
                    pass


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
            if lii in ['favourite','read']:
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
        headers=self.model().headerdata
        if label in headers:
            return headers.index(label)
        return -1





class MainFrame(QtWidgets.QWidget):

    def __init__(self,db):
        super(MainFrame,self).__init__()

        self.db=db

        #self.thumbnail_meta_list=thumbnail_meta_list
        #self.thumbnail_btn_dict={}    # buttons for preset icons

        #-----Try load previous session and favorites-----
        #self.loadHistory()

        #-------------------Button holders-------------------
        #self.history_btn_dict={}
        #self.history_btn_list=[]
        #self.favorite_btn_dict={}
        #self.favorite_btn_list=[]
        #self.tab_btn_dict={}

        self.initUI()


    def initUI(self):

        self.setWindowTitle('reference manager')

        v_layout0=QtWidgets.QVBoxLayout(self)

        #-------------------Tool bar row-------------------
        h_layout0=QtWidgets.QHBoxLayout()
        v_layout0.addLayout(h_layout0)

        # Add button
        self.add_button=QtWidgets.QToolButton(self)
        self.add_button.setText('Add')
        #self.add_button.setIcon(QIcon.fromTheme('list-add'))
        self.add_button.setIcon(QIcon.fromTheme('edit-undo'))
        self.add_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.add_button.clicked.connect(self.add_button_clicked)
        h_layout0.addWidget(self.add_button)

        h_layout0.addStretch()

        # seach bar
        self.search_bar=QtWidgets.QLineEdit(self)
        self.search_bar.setText('Type to search')

        self.search_bar.setFixedWidth(280)
        self.search_bar.setSizePolicy(getMinSizePolicy())
        self.search_bar.returnPressed.connect(self.search_bar_pressed)

        h_layout0.addWidget(self.search_bar)

        #-------------Add hline below tool bar-------------
        v_layout0.addWidget(getHLine(self))

        #-------------------Add lib tree-------------------
        self.libtree=self.addLibTree()
        h_split=QtWidgets.QSplitter(Qt.Horizontal)
        h_split.setSizePolicy(getXExpandYExpandSizePolicy())
        v_split=QtWidgets.QSplitter(Qt.Vertical)
        v_split.addWidget(self.libtree)
        v_layout0.addWidget(h_split)

        #----------------Add filter window----------------
        self.filter_list=QtWidgets.QTextEdit(self)
        v_split.addWidget(self.filter_list)
        h_split.addWidget(v_split)


        v_split.setSizes([2,1])
        

        #------------------Add doc table------------------
        self.doc_table=self.createTable()
        h_split.addWidget(self.doc_table)


        #---------------------Add tabs---------------------
        self.tabs=self.createTabs()

        h_split.addWidget(self.tabs)

        #------------------Add status bar------------------
        self.status_bar=QtWidgets.QStatusBar()
        v_layout0.addWidget(self.status_bar)
        self.status_bar.showMessage('etest')

        #------------------Load doc table------------------
        self.loadDocTable()
        


        h_split.setHandleWidth(10)
        w=h_split.size().width()
        h_split.setSizes([w*0.2,w*0.6,w*0.2])

        self.show()

    def createTable(self):

        tv=QtWidgets.QTableView(self)

        hh=MyHeaderView(self)
        hh.setSectionsClickable(True)
        hh.setHighlightSections(True)
        hh.sectionResized.connect(hh.myresize)
        #hh.sectionResized.connect(hh.resizeSections)
        hh.setStretchLastSection(False)
        #hh.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        #hh.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        #tv.setSizeAdjustPolicy(getXExpandYExpandSizePolicy())

        tv.setHorizontalHeader(hh)
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        tv.setSortingEnabled(True)
        hh.setSectionsMovable(True)
        hh.tv=tv




        return tv

    def addLibTree(self):

        libtree=QtWidgets.QTreeWidget()
        libtree.setHeaderHidden(True)

        folder_dict=getFolders(self.db)

        #-------------Get all level 1 folders-------------
        query='''SELECT DISTINCT id
        FROM Folders
        WHERE Folders.parentId=-1'''
        
        ret=self.db.execute(query).fetchall()
        folders1=[(folder_dict[fii[0]][0],fii[0]) for fii in ret]
        folders1.sort()

        #---------------Add level 1 folders---------------
        for fnameii,idii in folders1:
            fii=self.addTreeItem(libtree.invisibleRootItem(), fnameii)
            sub_ids=getSubFolders(folder_dict,idii)
            #-----------------Get sub folders-----------------
            for subii in sub_ids:
                subfii=folder_dict[subii][0]
                sii=self.addTreeItem(fii, subfii)
        
        libtree.itemChanged.connect(self.libtreeChange)

        return libtree

    def addTreeItem(self,parent,foldername):
        column=0
        folder=self.addParent(parent, column, foldername)
        #self.addChild(parent, column, foldername)
        return folder

    def addParent(self, parent, column, title):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        #item.setData(column, QtCore.Qt.UserRole, '')
        item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(True)
        return item

    def addChild(self, parent, column, title):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        #item.setData(column, QtCore.Qt.UserRole, data)
        item.setCheckState (column, QtCore.Qt.Unchecked)
        return item

    def libtreeChange(self, item, column):
        pass
        #if item.checkState(column) == QtCore.Qt.Checked:
        #print "checked", item, item.text(column)
        #if item.checkState(column) == QtCore.Qt.Unchecked:
        #print "unchecked", item, item.text(column)


    def createTabs(self):
        def _createPage():
            scroll=QtWidgets.QScrollArea(self)
            frame=QtWidgets.QWidget()
            v_layout=QtWidgets.QVBoxLayout()
            frame.setLayout(v_layout)
            scroll.setWidget(frame)
            return scroll

        tabs=QtWidgets.QTabWidget()
        t_meta=_createPage()
        t_notes=_createPage()
        t_topics=_createPage()

        tabs.addTab(t_meta,'Meta data')
        tabs.addTab(t_notes,'Notes')
        tabs.addTab(t_topics,'Topics')

        return tabs

    def loadDocTable(self):

        header=['favourite','read','author', 'title','journal','year']
        tablemodel=TableModel(self,[],header)
        self.doc_table.setModel(tablemodel)
        hh=self.doc_table.horizontalHeader()
        hh.setModel(tablemodel)

        n=10
        data=[]

        for ii in range(n):
            ii+=1
            entryii=getMetaData(self.db,ii)

            first=entryii['firstNames']
            last=entryii['lastName']
            if first is None or last is None:
                authors=''
            if type(first) is not list and type(last) is not list:
                authors='%s, %s' %(last, first)
            else:
                authors=['%s, %s' %(ii[0],ii[1]) for ii in zip(last,first)]
                authors=' and '.join(authors)

            aii=[QtWidgets.QCheckBox(entryii['favourite']),
                    QtWidgets.QCheckBox(entryii['read']),
                    authors,
                    entryii['title'],
                    entryii['publication'],
                    entryii['year']]
            data.append(aii)

        if len(data)==0:
            return

        self.tabledata=data
        tablemodel.arraydata=self.tabledata
        tablemodel.sort(0,Qt.DescendingOrder)
        hh.initresizeSections()



    def add_button_clicked(self):
        print 'add'

    def search_bar_pressed(self):
        print 'search term:', self.search_bar.text()

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self,db):
        super(MainWindow,self).__init__()

        self.db=db
        self.main_frame=MainFrame(db)
        self.setCentralWidget(self.main_frame)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Reference manager %s' %__version__)
        self.setGeometry(100,100,1200,900)    #(x_left,y_top,w,h)
        #self.setWindowIcon(QIcon('img.png'))
        self.menu_bar=self.menuBar()
        self.file_manu=self.menu_bar.addMenu('File')
        self.edit_manu=self.menu_bar.addMenu('Edit')
        self.view_manu=self.menu_bar.addMenu('View')
        self.tool_manu=self.menu_bar.addMenu('Tool')
        self.help_manu=self.menu_bar.addMenu('Help')

        self.show()

    def closeEvent(self,event):
        pass

def getMetaData(db, docid):
    '''Get meta-data of a doc by docid.
    '''

    # fetch column from Document table
    query_base=\
    '''SELECT Documents.%s
       FROM Documents
       WHERE (Documents.id=%s)
    '''

    query_tags=\
    '''
    SELECT DocumentTags.tag
    FROM DocumentTags
    WHERE (DocumentTags.docid=%s)
    ''' %docid

    query_firstnames=\
    '''
    SELECT DocumentContributors.firstNames
    FROM DocumentContributors
    WHERE (DocumentContributors.docid=%s)
    ''' %docid

    query_lastnames=\
    '''
    SELECT DocumentContributors.lastName
    FROM DocumentContributors
    WHERE (DocumentContributors.docid=%s)
    ''' %docid

    query_keywords=\
    '''
    SELECT DocumentKeywords.text
    FROM DocumentKeywords
    WHERE (DocumentKeywords.docid=%s)
    ''' %docid

    query_folder=\
    '''
    SELECT Folders.name
    FROM Folders
    LEFT JOIN DocumentFolders ON DocumentFolders.folderid=Folders.id
    WHERE (DocumentFolders.docid=%s)
    ''' %docid


    def fetchField(db,query):
        aa=db.execute(query).fetchall()
        bb=[ii[0] for ii in aa]
        if len(bb)==1:
            return bb[0]
        elif len(bb)==0:
            return None
        else:
            return bb

    #------------------Get file meta data------------------
    fields=['id','citationkey','title','issue','pages',\
            'publication','volume','year','doi','abstract',\
            'arxivId','chapter','city','country','edition','institution',\
            'isbn','issn','month','day','publisher','series','type',\
            'read','favourite']


    result={}

    # query single-worded fields, e.g. year, city
    for kii in fields:
        vii=fetchField(db,query_base %(kii,docid))
        result[kii]=vii

    result['tags']=fetchField(db,query_tags)
    result['firstNames']=fetchField(db,query_firstnames)
    result['lastName']=fetchField(db,query_lastnames)
    result['keywords']=fetchField(db,query_keywords)
    result['folder']=fetchField(db,query_folder)

    #-----------------Append user name-----------------
    #result['user_name']=getUserName(db)

    #------------------Add local url------------------
    #result['path']=getFilePath(db,docid)  # None or list

    #-----Add folder to tags, if not there already-----
    folder=result['folder']
    result['folder']=folder or 'Canonical' # if no folder name, a canonical doc
    tags=result['tags']
    tags=tags or []

    if not isinstance(tags,list):
        tags=[tags,]
    tags.sort()

    result['tags']=tags

    return result


def getFolders(db):

    #-----------------Get all folders-----------------
    query='''SELECT id, name, parentId
    FROM Folders
    '''
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    df=dict([(ii[0],ii[1:]) for ii in data])

    return df






#--------------Get folder id and name list in database----------------
def getFolderList(db,folder,verbose=True):
    '''Get folder id and name list in database

    <folder>: select folder from database.
              If None, select all folders/subfolders.
              If str, select folder <folder>, and all subfolders. If folder
              name conflicts, select the one with higher level.
              If a tuple of (id, folder), select folder with name <folder>
              and folder id <id>, to avoid name conflicts.

    Return: <folders>: list, with elements of (id, folder_tree).
            where <folder_tree> is a str of folder name with tree structure, e.g.
            test/testsub/testsub2.

    Update time: 2016-06-16 19:38:15.
    '''

    # get all folders with id, name, parentid
    query=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
    '''
    # get folder by name
    query1=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
       WHERE (Folders.name="%s")
    '''%folder

    #-----------------Get all folders-----------------
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    df=dict([(ii[0],ii[1:]) for ii in data])

    allfolderids=[ii[0] for ii in data]

    #---------------Select target folder---------------
    if folder is None:
        folderids=allfolderids
    if type(folder) is str:
        folderids=db.execute(query1).fetchall()
        folderids=[ii[0] for ii in folderids]
    elif isinstance(folder, (tuple,list)):
        # get folder from gui
        #seldf=df[(df.folderid==folder[0]) & (df.folder==folder[1])]
        #folderids=fetchField(seldf,'folderid')
        folderids=[folder[0]]

    #----------------Get all subfolders----------------
    if folder is not None:
        folderids2=[]
        for ff in folderids:
            folderids2.append(ff)
            subfs=getSubFolders(df,ff)
            folderids2.extend(subfs)
    else:
        folderids2=folderids

    #---------------Remove empty folders---------------
    folderids2=[ff for ff in folderids2 if not isFolderEmpty(db,ff)]

    #---Get names and tree structure of all non-empty folders---
    folders=[]
    for ff in folderids2:
        folders.append(getFolderTree(df,ff))

    #----------------------Return----------------------
    if folder is None:
        return folders
    else:
        if len(folders)==0:
            print("Given folder name not found in database or folder is empty.")
            return []
        else:
            return folders


#--------------------Check a folder is empty or not--------------------
def isFolderEmpty(db,folderid,verbose=True):
    '''Check a folder is empty or not
    '''

    query=\
    '''SELECT Documents.title,
              DocumentFolders.folderid,
              Folders.name
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       LEFT JOIN Folders
           ON Folders.id=DocumentFolders.folderid
    '''

    fstr='(Folders.id="%s")' %folderid
    fstr='WHERE '+fstr
    query=query+' '+fstr

    ret=db.execute(query)
    data=ret.fetchall()
    if len(data)==0:
        return True
    else:
        return False


#-------------------Get subfolders of a given folder-------------------
def getSubFolders(df,folderid,verbose=True):
    '''Get subfolders of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getParentId=lambda df,id: df[id][1]
    results=[]

    for idii in df:
        fii,pii=df[idii]
        cid=idii
        while True:
            pid=getParentId(df,cid)
            if pid==-1 or pid==0:
                break
            if pid==folderid:
                results.append(idii)
                break
            else:
                cid=pid

    results.sort()
    return results

#-------------Get folder tree structure of a given folder-------------
def getFolderTree(df,folderid,verbose=True):
    '''Get folder tree structure of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getFolderName=lambda df,id: df[id][0]
    getParentId=lambda df,id: df[id][1]

    folder=getFolderName(df,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=getParentId(df,cid)
        if pid==-1 or pid==0:
            break
        else:
            pfolder=getFolderName(df,pid)
            folder=u'%s/%s' %(pfolder,folder)
        cid=pid

    return folderid,folder


#----------Get a list of docids from a folder--------------
def getFolderDocList(db,folderid,verbose=True):
    '''Get a list of docids from a folder

    Update time: 2018-07-28 20:11:09.
    '''

    query=\
    '''SELECT Documents.id
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       WHERE (DocumentFolders.folderid=%s)
    ''' %folderid

    ret=db.execute(query)
    data=ret.fetchall()
    docids=[ii[0] for ii in data]
    docids.sort()
    return docids





if __name__=='__main__':

    abpath_in=os.path.abspath(FILE_IN)
    try:
        dbin = sqlite3.connect(abpath_in)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    app=QtWidgets.QApplication(sys.argv)
    mainwindow=MainWindow(dbin)
    sys.exit(app.exec_())
