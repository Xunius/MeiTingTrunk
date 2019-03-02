import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QBrush, QColor, QIcon, QCursor
from PyQt5.QtWidgets import QDialogButtonBox
import resources
from ..tools import fuzzyMatch, dfsCC


LOGGER=logging.getLogger('default_logger')




class CheckDuplicateDialog(QtWidgets.QDialog):

    def __init__(self,settings,meta_dict,docids1,docid2=None,parent=None):
        super(CheckDuplicateDialog,self).__init__(parent=parent)

        self.settings=settings
        self.docids1=docids1
        self.docids1.sort()
        self.docid2=docid2
        self.meta_dict=meta_dict

        self.min_score=self.settings.value('duplicate_min_score',type=int)

        self.resize(900,600)
        self.setWindowTitle('Duplicate Check')
        self.setWindowModality(Qt.ApplicationModal)

        va=QtWidgets.QVBoxLayout(self)

        self.tree=QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(6)

        self.tree.setHeaderLabels(['Group', 'Authors', 'Title', 'Publication',
            'Year', 'Similarity'])
        self.tree.setColumnWidth(0, 55)
        self.tree.setColumnWidth(1, 250)
        self.tree.setColumnWidth(2, 300)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 50)
        self.tree.setColumnWidth(5, 20)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(
                QtWidgets.QHeaderView.Interactive)
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

        self.buttons=QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.noDupLabel=QtWidgets.QLabel('No duplicates found.')

        va.addWidget(self.noDupLabel)
        va.addWidget(self.tree)
        va.addWidget(self.buttons)

        self.scores_dict=self.checkDuplicates()

        self.addResultToTree()
        self.exec_()

    def checkDuplicates(self):

        n=len(self.docids1)

        scores=[]
        scores_dict={}
        if self.docid2 is None:
            #----------------Check among docds----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoresii=[]
                for jj in range(n):
                    if ii>=jj:
                        scoreij=0
                    else:
                        docjj=self.docids1[jj]
                        scoreij=fuzzyMatch(self.meta_dict[docii], self.meta_dict[docjj])
                        scores_dict[(docii,docjj)]=scoreij
                    scoresii.append(scoreij)
                scores.append(scoresii)

            print('# <checkDuplicates>: scores=')
            for ii in range(n):
                print(scores[ii])

        else:
            #-----------------1 to all compare-----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoreii=fuzzyMatch(self.meta_dict[docii],
                        self.meta_dict[self.docid2])
                scores_dict[docii]=scoreii
                scores.append(scoreii)

            print('# <checkDuplicates>: scores=', scores)

        return scores_dict

    def addResultToTree(self):

        if self.docid2 is None:
            #-------------------Build graph-------------------
            import networkx as nx

            g=nx.Graph()
            edges=[kk for kk,vv in self.scores_dict.items() if vv>=self.min_score]

            if len(edges)==0:
                self.resize(400,200)
                self.tree.setVisible(False)
                self.noDupLabel.setVisible(True)
                return

            self.resize(900,600)
            self.tree.setVisible(True)
            self.noDupLabel.setVisible(False)
            g.add_edges_from(edges)
            print('# <addResultToTree>: edges',edges,'g.edges',list(g.edges))

            #comps=list(nx.connected_components(g))
            comps=[list(cii) for cii in sorted(nx.connected_components(g), key=len,\
                    reverse=True)]
            print('# <addResultToTree>: comps=',comps)

            #--------------------Add items--------------------
            for ii,cii in enumerate(comps):
                cii.sort()
                #itemii=QtWidgets.QTreeWidgetItem([str(ii+1),])
                docjj=cii[0]
                metajj=self.meta_dict[docjj]
                itemii=QtWidgets.QTreeWidgetItem([str(ii+1),
                    ', '.join(metajj['authors_l']),
                    metajj['title'],
                    metajj['publication'],
                    str(metajj['year']),
                    ''])
                self.tree.addTopLevelItem(itemii)

                # sort by scores
                docs=cii[1:]
                scores=[self.scores_dict[(cii[0],dii)] for dii in docs]
                docs=[x for _,x in sorted(zip(scores,docs), reverse=True)]

                for docjj in docs:
                    metajj=self.meta_dict[docjj]
                    itemjj=QtWidgets.QTreeWidgetItem(['',
                        ', '.join(metajj['authors_l']),
                        metajj['title'],
                        metajj['publication'],
                        str(metajj['year']),
                        str(self.scores_dict[(cii[0],docjj)])
                        ])
                    itemii.addChild(itemjj)

            self.tree.expandAll()
        else:
            pass

        return 


class CheckDuplicateFrame(QtWidgets.QScrollArea):

    del_doc_from_folder_signal=pyqtSignal(list, str, str, bool)
    del_doc_from_lib_signal=pyqtSignal(list, bool)
    def __init__(self,settings,parent=None):
        super(CheckDuplicateFrame,self).__init__(parent=parent)

        self.settings=settings
        self.min_score=self.settings.value('duplicate_min_score',type=int)

        frame=QtWidgets.QWidget()
        self.setWidgetResizable(True)
        self.setWidget(frame)
        va=QtWidgets.QVBoxLayout(self)

        #----------------Create clear frame----------------
        va.addWidget(self.createClearDuplicateFrame())

        #----------------Create treewidget----------------
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
        self.tree.customContextMenuRequested.connect(self.docTreeMenu)

        self.noDupLabel=QtWidgets.QLabel('No duplicates found.')
        va.addWidget(self.noDupLabel)
        va.addWidget(self.tree)

        frame.setLayout(va)

    def createClearDuplicateFrame(self):

        frame=QtWidgets.QFrame()
        frame.setStyleSheet('background: rgb(235,225,190)')
        ha=QtWidgets.QHBoxLayout()

        # del button
        self.del_duplicate_button=QtWidgets.QToolButton(self)
        self.del_duplicate_button.setText('Delete Selected')
        self.del_duplicate_button.clicked.connect(self.delDocs)

        # clear button
        self.clear_duplicate_button=QtWidgets.QToolButton(self)
        self.clear_duplicate_button.setText('Exit')

        self.clear_duplicate_label=QtWidgets.QLabel('Clear current filtering')
        ha.addWidget(self.clear_duplicate_label)
        tip_label=QtWidgets.QLabel()
        tip_icon=QIcon.fromTheme('help-about').pixmap(QSize(16,16))
        tip_label.setPixmap(tip_icon)
        tip_label.setToolTip('''Change "Mininimum Similary Score" in "Preferences" to change the filtering of matching results.''')
        ha.addWidget(tip_label)
        ha.addWidget(self.del_duplicate_button)
        ha.addWidget(self.clear_duplicate_button)

        frame.setLayout(ha)

        return frame



    def checkDuplicates(self,meta_dict,current_folder,docids1,docid2=None):

        self.tree.clear()

        self.meta_dict=meta_dict
        self.current_folder=current_folder # (name, id)
        self.docids1=docids1
        self.docids1.sort()
        self.docid2=docid2

        n=len(self.docids1)

        scores=[]
        self.scores_dict={}
        if self.docid2 is None:
            #----------------Check among docds----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoresii=[]
                for jj in range(n):
                    if ii>=jj:
                        scoreij=0
                    else:
                        docjj=self.docids1[jj]
                        scoreij=fuzzyMatch(self.meta_dict[docii], self.meta_dict[docjj])
                        self.scores_dict[(docii,docjj)]=scoreij
                    scoresii.append(scoreij)
                scores.append(scoresii)

            print('# <checkDuplicates>: scores=')
            for ii in range(n):
                print(scores[ii])

        else:
            #-----------------1 to all compare-----------------
            for ii in range(n):
                docii=self.docids1[ii]
                scoreii=fuzzyMatch(self.meta_dict[docii],
                        self.meta_dict[self.docid2])
                self.scores_dict[docii]=scoreii
                scores.append(scoreii)

            print('# <checkDuplicates>: scores=', scores)

        return

    def addResultToTree(self):

        #hi_color=self.settings.value('display/folder/highlight_color_br',
                #QBrush)

        if self.docid2 is None:
            #-------------------Build graph-------------------

            #g=nx.Graph()
            edges=[kk for kk,vv in self.scores_dict.items() if vv>=self.min_score]

            if len(edges)==0:
                self.noDupLabel.setVisible(True)
                return

            self.noDupLabel.setVisible(False)
            #g.add_edges_from(edges)
            #print('# <addResultToTree>: edges',edges,'g.edges',list(g.edges))

            #comps=[list(cii) for cii in sorted(nx.connected_components(g), key=len,\
                    #reverse=True)]
            comps=dfsCC(edges)
            print('# <addResultToTree>: comps=',comps)

            #--------------------Add items--------------------
            for ii,cii in enumerate(comps):
                cii.sort()
                docjj=cii[0]
                metajj=self.meta_dict[docjj]
                itemii=QtWidgets.QTreeWidgetItem([
                    str(ii+1),
                    ', '.join(metajj['authors_l']),
                    metajj['title'],
                    metajj['publication'],
                    str(metajj['year']),
                    '',
                    str(docjj)
                    ])

                for jj in range(self.tree.columnCount()):
                    itemii.setBackground(jj, QBrush(QColor(230,230,249)))

                self.tree.addTopLevelItem(itemii)

                # sort by scores
                docs=cii[1:]
                scores=[self.scores_dict[(cii[0],dii)] for dii in docs]
                docs=[x for _,x in sorted(zip(scores,docs), reverse=True)]

                for docjj in docs:
                    metajj=self.meta_dict[docjj]
                    itemjj=QtWidgets.QTreeWidgetItem([
                        '',
                        ', '.join(metajj['authors_l']),
                        metajj['title'],
                        metajj['publication'],
                        str(metajj['year']),
                        str(self.scores_dict[(cii[0],docjj)]),
                        str(docjj)
                        ])
                    itemii.addChild(itemjj)

            self.tree.expandAll()
        else:
            pass

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
    def delDocs(self):

        print('# <docTreeMenu>: current_folder=',self.current_folder)
        foldername,folderid=self.current_folder
        sel_rows=self.tree.selectedItems()
        if len(sel_rows)>0:

            docids=[int(ii.data(6,0)) for ii in sel_rows]

            print('# <docTreeMenu>: Selected docids=%s.' %docids)
            LOGGER.info('Selected docids=%s.' %docids)

            if folderid=='-1':
                self.del_doc_from_lib_signal.emit(docids,False)
            else:
                self.del_doc_from_folder_signal.emit(docids, foldername,
                        folderid, False)

            for itemii in sel_rows:
                self.tree.invisibleRootItem().removeChild(itemii)

        return
