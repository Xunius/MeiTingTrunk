from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from datetime import datetime
from lib.widgets import TableModel, MyHeaderView
from lib import sqlitedb
from lib import export2bib




def addFolder(parent,folderid,folder_dict):

    foldername,parentid=folder_dict[folderid]
    fitem=QtWidgets.QTreeWidgetItem([foldername,str(folderid)])
    style=QtWidgets.QApplication.style()
    diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
    fitem.setIcon(0,diropen_icon)
    sub_ids=sqlitedb.getChildFolders(folder_dict,folderid)
    if parentid=='0' or parentid=='-1':
        parent.addTopLevelItem(fitem)
    else:
        parent.addChild(fitem)
    if len(sub_ids)>0:
        for sii in sub_ids:
            addFolder(fitem,sii,folder_dict)

    return

def prepareDocs(meta_dict,docids):

    data=[]
    for ii in docids:
        entryii=meta_dict[ii]
        # convert timestamp to str
        added=entryii['added']
        if added:
            added=int(entryii['added'][:10])
            added=datetime.fromtimestamp(added)
            if added.year==datetime.today().year:
                added=added.strftime('%b-%d')
            else:
                added=added.strftime('%b-%d-%y')

        aii=[ii,
            QtWidgets.QCheckBox(entryii['favourite']),
            QtWidgets.QCheckBox(entryii['read']),
            entryii['has_file'],
            ' and '.join(entryii['authors']),
            entryii['title'],
            entryii['publication'],
            entryii['year'],
            added
            ]

        data.append(aii)

    return data



class MainFrameLoadData:

    def createDocTable(self):

        tv=QtWidgets.QTableView(self)

        hh=MyHeaderView(self)
        hh.setSectionsClickable(True)
        hh.setHighlightSections(True)
        hh.sectionResized.connect(hh.myresize)
        hh.setStretchLastSection(False)

        tv.setHorizontalHeader(hh)
        tv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tv.setShowGrid(True)
        tv.setSortingEnabled(True)
        hh.setSectionsMovable(True)

        header=['docid','favourite','read','has_file','author','title',
                'journal','year','added']
        tablemodel=TableModel(self,[],header)
        tv.setModel(tablemodel)
        hh.setModel(tablemodel)
        hh.initresizeSections()
        tv.setColumnHidden(0,True)

        tv.selectionModel().currentChanged.connect(self.selDoc)

        return tv


    def loadLibTree(self):

        style=QtWidgets.QApplication.style()
        diropen_icon=style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)

        #-------------Get all level 1 folders-------------
        folders1=[(vv[0],kk) for kk,vv in self.folder_dict.items() if\
                vv[1]=='0' or vv[1]=='-1']
        folders1.sort()

        allitem=QtWidgets.QTreeWidgetItem(['All','0'])
        allitem.setIcon(0,diropen_icon)
        self.libtree.addTopLevelItem(allitem)

        for fnameii,idii in folders1:
            addFolder(self.libtree,idii,self.folder_dict)

        self.libtree.setCurrentItem(allitem)

        return



    def loadDocTable(self,folder=None,docids=None):
        '''Load doc table given folder'''

        tablemodel=self.doc_table.model()
        #hh=self.doc_table.horizontalHeader()
        print('load tabel', folder)

        if docids is None:
            if folder is None:
                docids=self.meta_dict.keys()
                #data=prepareDocs(self.meta_dict,docids)
            else:
                folderid=folder[1]
                #if folderid in self.folder_data:
                docids=self.folder_data[folderid]
                #else:
                    #data=[]
            data=prepareDocs(self.meta_dict,docids)
        else:
            data=prepareDocs(self.meta_dict,docids)


        print('num in folder',len(docids))
        tablemodel.arraydata=data
        tablemodel.sort(4,Qt.AscendingOrder)
        self.tabledata=tablemodel.arraydata

        #------------Load meta data on 1st row------------
        if len(data)>0:
            self.doc_table.selectRow(0)
            current_row=self.doc_table.currentIndex().row()
            docid=self.tabledata[current_row][0]
            print('current_row',current_row, docid)
            print(self.tabledata[current_row])
            self.loadMetaTab(docid)
            self.enableMetaTab()
        else:
            # clear meta tab
            self.clearMetaTab()



    def loadMetaTab(self,docid=None):
        print('loadMetaTab',docid)
        if docid is None:
            return

        fields=self.t_meta.fields_dict.keys()
        metaii=self.meta_dict[docid]
        def deu(text):
            if isinstance(text,(str)):
                return text
            else:
                return str(text)

        for fii in fields:
            tii=metaii[fii]
            if tii is None:
                self.t_meta.fields_dict[fii].clear()
                continue
            if isinstance(tii,(list,tuple)):
                tii=u'; '.join(tii)
            self.t_meta.fields_dict[fii].setText(deu(tii))

        return 




    def loadBibTab(self,docid=None):
        print('loadBibTab',docid)
        if docid is None:
            return

        metaii=self.meta_dict[docid]
        #import bibtexparser
        #bb=bibtexparser.bibdatabase.BibDatabase()

        text=export2bib.parseMeta(metaii,'',metaii['folder'],True,False,
                True)

        self.bib_textedit.setText(text)

        return 


