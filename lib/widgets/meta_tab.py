import os
import re
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QFontMetrics
from PyQt5.QtWidgets import QDialogButtonBox
import resources
from .. import sqlitedb
from ..tools import getHLine, getXExpandYMinSizePolicy, parseAuthors,\
        getXExpandYExpandSizePolicy
from .. import _crossref

LOGGER=logging.getLogger(__name__)



class AdjustableTextEdit(QtWidgets.QTextEdit):

    edited_signal=pyqtSignal(str)
    def __init__(self,field,parent=None):
        super(AdjustableTextEdit,self).__init__(parent)

        self.field=field # field name, e.g. title, year, tags_l ...
        self.fm=QFontMetrics(self.font())
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
        self.setTabChangesFocus(True)


    def focusInEvent(self,event):
        #self.setToolTip('tooltip')
        #print('focusInEvent: QCursor.pos()', QCursor.pos())
        #QtWidgets.QToolTip.showText(QCursor.pos(), 'tooltip')
        if self.label_enabled and self.tooltip_text:
            self.tooltip_label.move(self.mapToGlobal(
                QPoint(0, self.height()-120)))
            self.tooltip_label.setText(self.tooltip_text)
            self.tooltip_label.show()

        super(AdjustableTextEdit,self).focusInEvent(event)


    def focusOutEvent(self,event):

        if self.document().isModified():
            self.edited_signal.emit(self.field)
        if self.label_enabled:
            self.tooltip_label.close()
        super(AdjustableTextEdit,self).focusOutEvent(event)


    def setText(self,text):

        super(AdjustableTextEdit,self).setText(text)
        self.document().setModified(False)


    def resizeTextEdit(self):

        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)

        return



class AdjustableTextEditWithFold(AdjustableTextEdit):

    fold_change_signal=pyqtSignal(str,bool)
    def __init__(self,field,parent=None):
        super(AdjustableTextEditWithFold,self).__init__(parent)

        self.field=field
        self.is_fold=False
        self.fold_above_nl=3

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
            font: bold %dpx;
            color: white;
            }

        QToolButton:pressed {
            border-style: inset;
            }
        ''' %(int(font_height/2), max(1,font_height-2))
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
            #self.unfoldText()
        else:
            self.fold_button.setVisible(True)
        if self.is_fold:
            self.foldText()
        else:
            self.unfoldText()

        return


    def toggleFold(self):

        self.unfoldText() if self.is_fold else self.foldText()
        self.fold_change_signal.emit(self.field,self.is_fold)

        return

    def foldText(self):

        nlines=self.getNumberOfLines()
        if nlines>=self.fold_above_nl:
            fontheight=self.fontMetrics().height()
            margin=self.document().documentMargin()
            self.setMinimumHeight(fontheight+2*margin)
            self.setMaximumHeight(fontheight+2*margin)
            self.is_fold=True
            self.fold_button.setArrowType(Qt.LeftArrow)

        return


    def unfoldText(self):

        docheight=self.document().size().height()
        margin=self.document().documentMargin()
        self.setMinimumHeight(docheight+2*margin)
        self.setMaximumHeight(docheight+2*margin)
        self.is_fold=False
        self.fold_button.setArrowType(Qt.DownArrow)

        return



class FileLineEdit(QtWidgets.QLineEdit):
    def __init__(self,parent=None):
        super(FileLineEdit,self).__init__(parent)

        self.fm=QFontMetrics(self.font())

    def setText(self,text,elide=True):
        self.full_text=text
        self.short_text=os.path.split(self.full_text)[1]
        #self.short_text=text

        '''
        if elide:
            super(FileLineEdit,self).setText(
                self.fm.elidedText(self.short_text,Qt.ElideRight,self.width()))
        else:
            super(FileLineEdit,self).setText(self.short_text)
        '''
        #super(FileLineEdit,self).setText(text)
        # It seems that it requires a 20 pixel space
        super(FileLineEdit,self).setText(
             self.fm.elidedText(self.short_text,Qt.ElideRight,self.width()-20))

        return


    def text(self):
        #return self.full_text
        return self.fm.elidedText(self.short_text,Qt.ElideRight,self.width()-20)


    def resizeEvent(self,event):

        super(QtWidgets.QLineEdit, self).resizeEvent(event)
        if hasattr(self,'full_text'):
            self.setText(self.full_text,elide=True)



class MetaTabScroll(QtWidgets.QScrollArea):

    meta_edited=pyqtSignal(list) # send field names
    update_by_doi_signal=pyqtSignal(sqlitedb.DocMeta)
    def __init__(self,settings,parent=None):
        super(MetaTabScroll,self).__init__(parent)

        self.settings=settings
        self.parent=parent

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.label_font=QFont('Serif',12,QFont.Bold)

        frame=QtWidgets.QWidget()
        frame.setStyleSheet('background-color:white')
        self.setWidgetResizable(True)
        self.setWidget(frame)
        self.fields_dict={}  # key: field name, value: textedit or lineedit
        self.fold_dict={} # key: field name, value: is textedit folded

        #-------------------Add widgets-------------------
        self.v_layout=QtWidgets.QVBoxLayout()

        #--------------------Add title--------------------
        title_te=AdjustableTextEdit('title')
        title_te.setFrameStyle(QtWidgets.QFrame.NoFrame)
        title_te.setFont(self.settings.value('display/fonts/meta_title', QFont))
        self.fields_dict['title']=title_te
        self.v_layout.addWidget(title_te)

        self.v_layout.addWidget(getHLine(self))

        #-------------------Add authors-------------------
        self.createMultiLineField('Authors','authors_l','meta_authors')

        #-----Add journal, year, volume, issue, pages-----
        grid_layout=QtWidgets.QGridLayout()

        for fii in ['publication','year','volume','issue','pages',
                'citationkey']:
            self.createOneLineField(fii,fii,'meta_keywords',grid_layout)

        self.v_layout.addLayout(grid_layout)

        #---------------------Add tags---------------------
        self.createMultiLineField('Tags','tags_l','meta_keywords')

        #-------------------Add abstract-------------------
        self.createMultiLineField('Abstract','abstract','meta_keywords')

        #-------------------Add keywords-------------------
        self.createMultiLineField('Keywords','keywords_l',
                'meta_keywords')

        #-----------------Add catalog ids-----------------
        self.v_layout.addWidget(self.createLabel('Catalog IDs'))

        grid_layout=QtWidgets.QGridLayout()

        for fii in ['arxivId','doi','issn','pmid']:
            self.createOneLineField(fii,fii,'meta_keywords',grid_layout)

        #--------------Add doi search button--------------
        self.doi_search_button=QtWidgets.QPushButton()
        self.doi_search_button.setFixedSize(30,30)
        self.doi_search_button.setIcon(QIcon.fromTheme('edit-find'))
        self.doi_search_button.setStyleSheet('''
        QPushButton {
            border: 1px solid rgb(190,190,190);
            border-radius: 15px;
            color: white;
            }
        QPushButton:pressed {
            border-style: inset;
            }
        ''')
        self.doi_search_button.clicked.connect(self.doiSearchButtonClicked)

        grid_layout.addWidget(self.doi_search_button,2,2)

        self.v_layout.addLayout(grid_layout)

        #--------------------Add files--------------------
        self.fields_dict['files_l']=[]
        self.v_layout.addWidget(self.createLabel('Files'))
        self.file_insert_idx=self.v_layout.count()

        LOGGER.debug('NO of widgets in v_layout=%d' %self.v_layout.count())

        #---------------Add add file button---------------
        add_file_button=QtWidgets.QPushButton()
        add_file_button.setText('Add File...')
        add_file_button.setSizePolicy(getXExpandYMinSizePolicy())
        add_file_button.setStyleSheet('''
        QPushButton {
            background-color: rgb(220,220,220);
            border-radius: 2px;
            }

        QPushButton:pressed {
            border-style: inset;
            }
        ''')
        add_file_button.clicked.connect(self.addFileButtonClicked)
        self.v_layout.addWidget(add_file_button)

        self.v_layout.addStretch()
        frame.setLayout(self.v_layout)

        #-------------Connect focus out events-------------
        for kk,vv in self.fields_dict.items():
            if isinstance(vv,(list,tuple)):
                for vii in vv:
                    vii.edited_signal.connect(self.fieldEdited)
            else:
                vv.edited_signal.connect(self.fieldEdited)

        #------------------Set tab orders------------------
        field_keys=['title', 'authors_l', 'publication', 'year', 'volume',
                'issue', 'pages', 'citationkey', 'tags_l', 'abstract',
                'keywords_l', 'arxivId', 'doi', 'issn', 'pmid']
        for ii,kk in enumerate(field_keys[:-1]):
            w1=self.fields_dict[kk]
            w2=self.fields_dict[field_keys[ii+1]]
            self.setTabOrder(w1,w2)


    @pyqtSlot(str)
    def fieldEdited(self,field):

        LOGGER.debug('Changed field = %s' %field)
        LOGGER.debug('meta_dict = %s' %self._meta_dict)

        self.meta_edited.emit([field,])

        return


    def createLabel(self,label):

        qlabel=QtWidgets.QLabel(label)
        qlabel.setStyleSheet(self.label_color)
        qlabel.setFont(self.label_font)

        return qlabel


    def createOneLineField(self,label,key,font_name,grid_layout):

        te=AdjustableTextEdit(key)
        qlabel=QtWidgets.QLabel(label)
        qlabel.setStyleSheet(self.label_color)

        #if font_name in self.font_dict:
        te.setFont(self.settings.value('display/fonts/%s' %font_name, QFont))

        rnow=grid_layout.rowCount()
        grid_layout.addWidget(qlabel,rnow,0,1,1)
        if key=='doi':
            # leave room for button
            grid_layout.addWidget(te,rnow,1,1,1)
        else:
            grid_layout.addWidget(te,rnow,1,1,2)
        self.fields_dict[key]=te

        return


    def createMultiLineField(self,label,key,font_name):

        te=AdjustableTextEditWithFold(key)
        te.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.fold_dict[key]=te.is_fold
        te.fold_change_signal.connect(self.foldChanged)

        #if font_name in self.font_dict:
        te.setFont(self.settings.value('display/fonts/%s' %font_name, QFont))

        if key=='authors_l':
            te.label_enabled=True
            te.tooltip_text='lastname, firstname\nlastname, firstname\n...'
        elif key=='tags_l':
            te.label_enabled=True
            te.tooltip_text='tag1; tag2; tag3 ...'
        elif key=='keywords_l':
            te.label_enabled=True
            te.tooltip_text='keyword1; keyword2; keyword3 ...'
        self.fields_dict[key]=te

        h_layout=QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.createLabel(label))
        h_layout.addWidget(te.fold_button)

        self.v_layout.addLayout(h_layout)
        self.v_layout.addWidget(te)

        return te


    def createFileField(self,text=None,font_name='meta_keywords'):

        h_layout=QtWidgets.QHBoxLayout()

        le=FileLineEdit()
        le.setReadOnly(True)

        le.setFont(self.settings.value('display/fonts/%s' %font_name, QFont))

        if text is not None:
            print('# <createFileField>: file text=',text)
            le.setText(text)

        if le not in self.fields_dict['files_l']:
            LOGGER.debug('before add file le to fields_dict. %s'\
                    %self.fields_dict['files_l'])
            self.fields_dict['files_l'].append(le)
            LOGGER.debug('after add file le to fields_dict. %s'\
                    %self.fields_dict['files_l'])

        # create a del file button
        button=QtWidgets.QPushButton()
        font_height=le.fm.height()
        button.setFixedWidth(int(font_height))
        button.setFixedHeight(int(font_height))
        button.setText('\u2715')
        button.setStyleSheet('''
        QPushButton {
            border: 1px solid rgb(190,190,190);
            background-color: rgb(190,190,190);
            border-radius: %dpx;
            font: bold %dpx;
            color: white;
            text-align: center;
            padding-bottom: 2px;
            }

        QPushButton:pressed {
            border-style: inset;
            }
        ''' %(int(font_height/2), max(1,font_height-2))
        )
        button.clicked.connect(lambda: self.delFileButtonClicked(
            self.fields_dict['files_l'].index(le)))

        le.del_button=button
        h_layout.addWidget(le)
        h_layout.addWidget(button)

        LOGGER.debug('Insert file %s entry at %s' %(text,self.file_insert_idx))

        self.v_layout.insertLayout(self.file_insert_idx,h_layout)
        self.file_insert_idx+=1

        return


    def delFileButtonClicked(self, idx=None):

        self.delFileField(idx)
        self.fieldEdited('files_l')

        return


    def delFileField(self,idx=None):

        def delFile(le):
            self.v_layout.removeWidget(le.del_button)
            self.v_layout.removeWidget(le)
            le.deleteLater()
            le.del_button.deleteLater()
            # NOTE: you can't del a element in list if it is iterating
            #self.fields_dict['files_l'].remove(le)
            self.file_insert_idx-=1

        if idx is None:
            for leii in self.fields_dict['files_l']:
                delFile(leii)
            self.fields_dict['files_l']=[]

        else:
            if idx in range(len(self.fields_dict['files_l'])):
                leii=self.fields_dict['files_l'][idx]
                delFile(leii)
                self.fields_dict['files_l'].remove(leii)

        return


    def addFileButtonClicked(self):

        if hasattr(self.parent, '_current_doc') and self.parent._current_doc is None:
            return

        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose a PDF file',
         '',"PDF files (*.pdf);; All files (*)")[0]

        if fname:

            LOGGER.info('Add new file = %s' %fname)

            self.createFileField(fname)
            self.fieldEdited('files_l')

        return


    def foldChanged(self,field,isfold):

        self.fold_dict[field]=isfold

        LOGGER.debug('Field = %s. isfold = %s' %(field, isfold))

        return


    def doiSearchButtonClicked(self):

        doi_pattern=re.compile(r'(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)',
                re.DOTALL|re.UNICODE)

        doi=self.fields_dict['doi'].toPlainText()
        LOGGER.info('doi = %s' %doi)

        if len(doi)>0:
            match=doi_pattern.match(doi)
            LOGGER.debug('match = %s' %match)

            if match:
                rec,doi_dict=_crossref.fetchMetaByDOI(doi)
                if rec==1:
                    LOGGER.warning('Failed to fetch from doi.')

                    msg=QtWidgets.QMessageBox()
                    msg.resize(500,500)
                    msg.setIcon(QtWidgets.QMessageBox.Information)
                    msg.setWindowTitle('Error')
                    msg.setText('Oopsie.')
                    msg.setInformativeText('Failed to retrieve metadata from doi')
                    msg.exec_()

                    return

                meta_dict=_crossref.crossRefToMetaDict(doi_dict)

                LOGGER.debug('Got meta_dict from doi:' %meta_dict)
                LOGGER.debug('citationkey = %s' %meta_dict['citationkey'])

                #self.update_by_doi_signal.emit(meta_dict)
                self.exchangeMetaDict(meta_dict)

        return


    def exchangeMetaDict(self,new_dict):

        docid=self.parent._current_doc
        if docid is None:
            return

        old_dict=self.parent.meta_dict[docid]
        fields=[]

        for kk,vv in old_dict.items():
            if kk in ['id', 'read', 'favourite', 'added', 'files_l',
                    'folders_l', 'tags_l', 'deletionPending', 'notes',
                    'abstract' ]:
                new_dict[kk]=vv
            else:
                if vv!=new_dict[kk]:
                    fields.append(kk)

        if 'firstNames_l' in fields or 'lastName_l' in fields:
            fields.append('authors_l') # updateTabelData monitors this

        LOGGER.debug('Changed fields = %' %fields)

        if len(fields)==0:
            return

        self.update_by_doi_signal.emit(new_dict)

        return


    @property
    def _meta_dict(self):

        def parseToList(text):
            result=[]
            textlist=text.replace('\n',';').strip(';').split(';')
            for tii in textlist:
                tii=tii.strip()
                if len(tii)>0:
                    result.append(tii)
            return result

        #result_dict={}
        result_dict=sqlitedb.DocMeta()
        for kk,vv in self.fields_dict.items():
            # field should be a list
            if kk.endswith('_l'):
                if isinstance(vv,(tuple,list)):
                    values=[]
                    for vii in vv:
                        if isinstance(vii,QtWidgets.QLineEdit):
                            if kk=='files_l':
                                textii=vii.full_text
                            else:
                                textii=vii.text().strip()
                        elif isinstance(vii,QtWidgets.QTextEdit):
                            textii=vii.toPlaintext().strip()
                        if textii:
                            values.append(textii)
                    result_dict[kk]=values
                elif isinstance(vv,QtWidgets.QTextEdit):
                    if kk=='authors_l':
                        names=parseToList(vv.toPlainText())
                        firsts,lasts,authors=parseAuthors(names)
                        result_dict['firstNames_l']=firsts
                        result_dict['lastName_l']=lasts
                        #result_dict['authors_l']=authors
                    else:
                        result_dict[kk]=parseToList(vv.toPlainText())
                elif isinstance(vv,QtWidgets.QLineEdit):
                    result_dict[kk]=parseToList(vv.toText())
            # field should be a str
            else:
                if isinstance(vv,QtWidgets.QLineEdit):
                    values=vv.toText().strip()
                    result_dict[kk]=values or None
                elif isinstance(vv,QtWidgets.QTextEdit):
                    values=vv.toPlainText().strip()
                    result_dict[kk]=values or None

        return result_dict



class MetaDataEntryDialog(QtWidgets.QDialog):

    def __init__(self,settings,parent=None):
        super(MetaDataEntryDialog,self).__init__(parent)

        self.resize(500,700)
        self.setWindowTitle('Add New Entry')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()

        self.scroll=MetaTabScroll(settings,self)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.scroll.meta_edited.connect(self.checkOkButton)

        v_layout.addWidget(self.scroll)
        v_layout.addWidget(self.buttons)

        self.setLayout(v_layout)

        self.initialized=False
        self.empty_dict=sqlitedb.DocMeta()
        self.empty_dict.pop('added')
        self.empty_dict.pop('files_l')

    def checkOkButton(self):
        def checkDictChanged(d1,d2):
            for kk in d1.keys():
                if d1[kk]!=d2[kk]:
                    return True
            return False

        if checkDictChanged(self.empty_dict,self.scroll._meta_dict):
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def showEvent(self,e):
        if not self.initialized:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            self.initialized=True

        self.scroll.fields_dict['title'].setFocus()
        super(MetaDataEntryDialog,self).showEvent(e)
        return

    def exec_(self):
        ret=super(MetaDataEntryDialog,self).exec_()
        return ret, self.scroll._meta_dict


class NoteTextEdit(QtWidgets.QTextEdit):

    note_edited_signal=pyqtSignal()
    def __init__(self,settings,parent=None):

        self.settings=settings

        super(NoteTextEdit,self).__init__(parent=parent)

        self.setFont(self.settings.value('display/fonts/notes',QFont))
        self.setSizePolicy(getXExpandYExpandSizePolicy())


    def focusOutEvent(self,event):
        if self.document().isModified():
            self.note_edited_signal.emit()
        super(NoteTextEdit,self).focusOutEvent(event)

