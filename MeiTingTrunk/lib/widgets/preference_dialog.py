'''
Preference dialog.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import logging
from collections import OrderedDict
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, pyqtSlot, QRect
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtWidgets import QStyle, QStyleOptionSlider, QDialogButtonBox
from ..tools import getHLine, getXMinYExpandSizePolicy

LOGGER=logging.getLogger(__name__)



class PreferenceDialog(QtWidgets.QDialog):

    def __init__(self,settings,parent=None):
        '''
        Args:
            parent (QWidget): parent widget.
            settings (QSettings): application settings. See _MainWindow.py
        '''

        super(PreferenceDialog,self).__init__(parent=parent)

        self.settings=settings
        self.parent=parent

        self.font_dict=OrderedDict([
            ('Meta Tab -> Title'      , 'display/fonts/meta_title')    ,
            ('Meta Tab -> Authors'    , 'display/fonts/meta_authors')  ,
            ('Meta Tab -> Keywords'   , 'display/fonts/meta_keywords') ,
            ('Document Table Entries' , 'display/fonts/doc_table')     ,
            ('Bibtex Tab'             , 'display/fonts/bibtex')        ,
            ('Notes Tab'              , 'display/fonts/notes')         ,
            ('Scratch Pad Tab'        , 'display/fonts/scratch_pad')
            ])

        self.new_values={} # store changes before applying

        self.label_color='color: rgb(0,0,140); background-color: rgb(235,235,240)'
        self.title_label_font=QFont('Serif',12,QFont.Bold)
        self.sub_title_label_font=QFont('Serif',10,QFont.Bold)

        self.resize(800,600)
        self.setWindowTitle('Preferences')
        self.setWindowModality(Qt.ApplicationModal)

        v_layout=QtWidgets.QVBoxLayout()
        h_layout=QtWidgets.QHBoxLayout()
        #h_layout.setContentsMargins(10,40,10,20)
        self.setLayout(v_layout)

        title_label=QtWidgets.QLabel('    Change Preference Settings')
        title_label.setFont(QFont('Serif',12,QFont.Bold))
        v_layout.addWidget(title_label)

        v_layout.addLayout(h_layout)

        self.cate_list=QtWidgets.QListWidget(self)
        #self.list.setSizePolicy(getXMinYExpandSizePolicy())
        self.cate_list.setMaximumWidth(150)
        h_layout.addWidget(self.cate_list)

        #self.cate_list.setStyleSheet('''
            #QListWidget::item { border: 0px solid rgb(235,235,240);
            #font: 14px;
            #background-color: rgb(205,205,245);
            #color: rgb(100,10,13) };
            #background-color: rgb(230,234,235);
            #''')

        self.cate_list.addItems(['Citation Style', 'Display', 'Bibtex Export',
            'RIS Export', 'Savings', 'Miscellaneous'])

        self.content_vlayout=QtWidgets.QVBoxLayout()
        h_layout.addLayout(self.content_vlayout)

        self.buttons=QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply |\
                    QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.buttons.accepted.connect(lambda: (self.applyChanges(), self.accept()))
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Apply).clicked.connect(
                self.applyChanges)

        self.content_vlayout.addWidget(self.buttons)

        self.cate_list.currentItemChanged.connect(self.cateSelected)
        self.cate_list.setCurrentRow(0)


    @pyqtSlot()
    def applyChanges(self):
        '''Write changes to settings'''

        LOGGER.info('Changes: %s' %self.new_values)

        for kk,vv in self.new_values.items():

            self.settings.setValue(kk,vv)

        #------------------Set new timer------------------
        if 'saving/auto_save_min' in self.new_values:
            interval=self.settings.value('saving/auto_save_min',1,int)
            self.parent.main_frame.auto_save_timer.setInterval(interval*60*1000)
            LOGGER.info('Set auto save timer to %s' %interval)

        self.new_values={}

        #---------------Create output folder---------------
        storage_folder=self.settings.value('saving/storage_folder')
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)

            LOGGER.info('Create new storage folder %s' %storage_folder)


        # TODO: apply change to database and meta_dict
        # need to call saveFoldersToDatabase() with new folder, and
        # metaDictToDatabase() for all docids. Then move database file over.
        # may need to require a reboot if so.

        #sqlitedb.saveFoldersToDatabase(self.db,self.folder_dict,
                #self.settings.value('saving/storage_folder'))
        # UPDATE: after changing the file paths relative, seems no need to
        # do the above things.

        return


    @pyqtSlot(QtWidgets.QListWidgetItem)
    def cateSelected(self,item):
        '''Load widgets for a selected category

        Args:
            item (QListWidgetItem): selected category item.
        '''

        item_text=item.text()
        LOGGER.info('item.text() = %s' %item.text())

        if self.content_vlayout.count()>1:
            self.content_vlayout.removeWidget(self.content_frame)

        if item_text=='Display':
            self.content_frame=self.loadDisplayOptions()
        elif item_text=='Bibtex Export':
            self.content_frame=self.loadBibExportOptions()
        elif item_text=='RIS Export':
            self.content_frame=self.loadRISExportOptions()
        elif item_text=='Citation Style':
            self.content_frame=self.loadCitationStyleOptions()
        elif item_text=='Savings':
            self.content_frame=self.loadSavingsOptions()
        elif item_text=='Miscellaneous':
            self.content_frame=self.loadMiscellaneousOptions()

        self.content_vlayout.insertWidget(0,self.content_frame)


    def createFrame(self,title):
        '''Create a template frame for a category page

        Args:
            title (str): title of the category

        Returns:
            scroll (QScrollArea): a scroll area.
            va (QVBoxLayout): the vertical box layout used in scroll.
        '''

        frame=QtWidgets.QWidget(self)
        scroll=QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        va=QtWidgets.QVBoxLayout()
        frame.setLayout(va)
        va.setSpacing(int(va.spacing()*2))

        label=QtWidgets.QLabel(title)
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)
        va.addWidget(label)
        #va.addWidget(getHLine(self))

        return scroll, va


    def createOmitKeyGroup(self):
        '''Create checkbox group
        '''

        grid=QtWidgets.QGridLayout()

        self.groupbox=QtWidgets.QGroupBox('Omit these fields in the exported bib entry.')
        self.groupbox.setCheckable(True)

        omittable_keys=[
            'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
            'lastName_l', 'deletionPending', 'folders_l', 'type', 'id',
            'abstract', 'advisor', 'month', 'language', 'confirmed',
            'deletionPending', 'note', 'publicLawNumber', 'sections',
            'reviewedArticle', 'userType', 'shortTitle', 'sourceType',
            'code', 'codeNumber', 'codeSection', 'codeVolume', 'citationKey',
            'day', 'dateAccessed', 'internationalAuthor', 'internationalUserType',
            'internationalTitle', 'internationalNumber', 'genre', 'lastUpdate',
            'legalStatus', 'length', 'medium'
            ]
        omittable_keys.sort()

        omit_keys=self.settings.value('export/bib/omit_fields', [], str)
        # likely something wrong with qt. When list is set empty by
        # settings.setValue('key',[]), on the NEXT load of the program,
        # settings.value('export/bib/omit_fields', [], str) gives ''
        if isinstance(omit_keys,str) and omit_keys=='':
            omit_keys=[]

        for ii,keyii in enumerate(omittable_keys):
            checkboxii=QtWidgets.QCheckBox(keyii,self.groupbox)
            if keyii in omit_keys:
                checkboxii.setChecked(True)
            checkboxii.stateChanged.connect(self.omitKeyChanged)
            grid.addWidget(checkboxii,int(ii/3),ii%3)

        self.groupbox.toggled.connect(lambda on: self.omitKeysGroupChanged(on,
            self.groupbox))

        self.groupbox.setLayout(grid)

        return self.groupbox


    def loadDisplayOptions(self):
        '''Load widgets for the Display category'''

        scroll,va=self.createFrame('Select Fonts')

        ha=QtWidgets.QHBoxLayout()
        #ha.addStretch()
        label=QtWidgets.QLabel('NOTE some changes requires re-booting.')
        ha.addWidget(label,0,Qt.AlignTop)

        text_list=QtWidgets.QListWidget()
        text_list.setSizePolicy(getXMinYExpandSizePolicy())
        text_list.addItems(self.font_dict.keys())

        ha.addWidget(text_list)

        text_list.itemDoubleClicked.connect(self.chooseFont)
        va.addLayout(ha)

        return scroll


    @pyqtSlot(QtWidgets.QListWidgetItem)
    def chooseFont(self,item):
        '''Choose a font

        Args:
            item (QListWidgetItem): item for field font change is applying to
        '''

        item_text=item.text()
        LOGGER.info('item.text() = %s' %item.text())

        font_setting_name=self.font_dict[item_text]
        default=self.settings.value(font_setting_name, QFont)
        new_font,isok=QtWidgets.QFontDialog.getFont(default,
                caption='Choose Font for %s' %item_text)

        if isok:
            self.new_values[font_setting_name]=new_font
            LOGGER.info('Font after change = %s' %new_font)

        return


    def loadSavingsOptions(self):
        '''Load widgets for the Savings category'''

        scroll, va=self.createFrame('Default saving folder')

        #-------------Choose storage folder section-------------
        label2=QtWidgets.QLabel('''
        Select default folder to save libraries
        ''')
        label2.setTextFormat(Qt.RichText)
        va.addWidget(label2)

        ha=QtWidgets.QHBoxLayout()
        ha.addStretch()

        storage_folder=self.settings.value('saving/storage_folder')
        le=QtWidgets.QLineEdit()
        le.setText(storage_folder)

        va.addWidget(le)
        va.addLayout(ha)
        button=QtWidgets.QPushButton(self)
        button.setText('Choose')

        button.clicked.connect(lambda x,le=le:self.chooseSaveFolder(le))
        ha.addWidget(button)
        va.addWidget(getHLine())

        #---------------Link or copy section---------------
        label1=QtWidgets.QLabel('Choose saving manner')
        label1.setStyleSheet(self.label_color)
        label1.setFont(self.title_label_font)
        self.saving_manner_radiogroup=self.createSavingMannerGroup()
        label4=QtWidgets.QLabel('NOTE that changes would only affect files added in the future')
        label4.setWordWrap(True)

        va.addWidget(label1)
        va.addWidget(self.saving_manner_radiogroup)
        va.addWidget(label4)
        va.addWidget(getHLine())

        #---------------Rename file section---------------
        label3=QtWidgets.QLabel('Rename Files')
        label3.setStyleSheet(self.label_color)
        label3.setFont(self.title_label_font)
        checkbox=QtWidgets.QCheckBox('Rename Files')
        checked=self.settings.value('saving/rename_files',type=int)
        LOGGER.debug('Is rename files = %s' %checked)

        checkbox.setChecked(checked)

        le=QtWidgets.QLineEdit(self)
        le.setReadOnly(True)
        le.setDisabled(1-checked)
        checkbox.stateChanged.connect(lambda on: self.changeRenameFiles(on))
        checkbox.stateChanged.connect(lambda on: le.setEnabled(on))

        le.setText('Renaming Format: Author_Year_Title.pdf')

        current_lib=self.settings.value('saving/current_lib_folder', type=str)
        label2=QtWidgets.QLabel('''
        Documents (e.g. PDFs) will be copied/linked to the
        <span style="font:bold;">
        "%s/_collections" </span>
        folder, and renamed by the following format.
        ''' %('library-name' if current_lib=='' else current_lib)
        )
        label2.setTextFormat(Qt.RichText)
        label2.setWordWrap(True)

        va.addWidget(checkbox)
        va.addWidget(label2)
        va.addWidget(le)

        #----------------Auto save section----------------
        va.addWidget(getHLine(self))
        label3=QtWidgets.QLabel('Auto save interval (min)')
        label3.setStyleSheet(self.label_color)
        label3.setFont(self.title_label_font)
        va.addWidget(label3)
        va.addWidget(getHLine(self))

        slider=LabeledSlider(1,10,1,parent=self)
        slider.sl.setValue(self.settings.value('saving/auto_save_min',2,int))
        slider.sl.valueChanged.connect(self.changeSavingInterval)
        slider.setMaximumWidth(400)

        va.addWidget(slider)

        va.addStretch()


        return scroll


    @pyqtSlot(QtWidgets.QLineEdit)
    def chooseSaveFolder(self, le=None):
        '''Prompt for dir choose and store new value'''

        fname=QtWidgets.QFileDialog.getExistingDirectory(self,
            'Choose a folder to save documents and database')

        if fname:
            if le is not None:
                le.setText(fname)
            LOGGER.info('Folder after change = %s' %fname)
            self.new_values['saving/storage_folder']=fname

        return


    def createSavingMannerGroup(self):
        '''Create radiobutton group for file copy or link manner selection'''

        groupbox=QtWidgets.QGroupBox('Copy or link file when adding into library.')
        ha=QtWidgets.QHBoxLayout()
        manner=self.settings.value('saving/file_move_manner', type=str)

        for ii in ['Copy File', 'Create Symbolic Link']:
            buttonii=QtWidgets.QRadioButton(ii)
            if manner in ii.lower():
                buttonii.setChecked(True)
            buttonii.toggled.connect(lambda on: self.savingMannerChange(on))
            ha.addWidget(buttonii)

        groupbox.setLayout(ha)

        return groupbox


    @pyqtSlot(bool)
    def savingMannerChange(self, on):
        '''Collect check states in the saving manner radiobutton group'''

        for rii in self.saving_manner_radiogroup.findChildren(QtWidgets.QRadioButton):
            if rii.isChecked():
                if 'link' in rii.text().lower():
                    new_value='link'
                elif 'copy' in rii.text().lower():
                    new_value='copy'
                self.new_values['saving/file_move_manner']=new_value
                break

        return


    def changeRenameFiles(self,on):
        '''Store the check state of rename file checkbox'''

        on=1 if on>0 else 0 # for some reason <on> keeps giving me 2
        self.new_values['saving/rename_files']=on
        LOGGER.info('Change rename files to %s' %on)

        return


    def changeSavingInterval(self,value):
        '''Store the value on the auto saving interval slider'''

        LOGGER.info('Change auto saving interval to %s' %value)
        self.new_values['saving/auto_save_min']=value

        return


    def loadBibExportOptions(self):
        '''Load widgets for the bibtex Export category'''

        scroll, va=self.createFrame('Bibtex Export')
        self.groupbox=self.createOmitKeyGroup()
        va.addWidget(self.groupbox)

        va.addWidget(getHLine())

        label=QtWidgets.QLabel('File path type')
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)

        self.pathtype_radiogroup=self.createPathTypeGroup('bib')
        va.addWidget(self.pathtype_radiogroup)

        return scroll


    def loadRISExportOptions(self):
        '''Load widgets for the RIS Export category'''

        scroll, va=self.createFrame('RIS Export')

        label=QtWidgets.QLabel('File path type')
        label.setStyleSheet(self.label_color)
        label.setFont(self.title_label_font)

        self.pathtype_radiogroup=self.createPathTypeGroup('ris')
        va.addWidget(self.pathtype_radiogroup)

        va.addStretch()

        return scroll


    def createPathTypeGroup(self, export_type):
        '''Create radiobutton group for file path type selection'''

        groupbox=QtWidgets.QGroupBox('Use relative or absolute paths for files.')
        ha=QtWidgets.QHBoxLayout()
        path_type=self.settings.value('export/%s/path_type' %export_type,str)

        for ii in ['Relative', 'Absolute']:
            buttonii=QtWidgets.QRadioButton(ii)
            if ii.lower()==path_type:
                buttonii.setChecked(True)
            buttonii.toggled.connect(lambda on: self.pathTypeChanged(on, export_type))
            ha.addWidget(buttonii)

        groupbox.setLayout(ha)

        return groupbox


    @pyqtSlot(bool, str)
    def pathTypeChanged(self,on, export_type):
        '''Collect check states in the path type radiobutton group'''

        LOGGER.debug('export_type = %s' %export_type)
        for rii in self.pathtype_radiogroup.findChildren(QtWidgets.QRadioButton):
            if rii.isChecked():
                self.new_values['export/%s/path_type' %export_type]=rii.text().lower()
                break

        return


    def omitKeyChanged(self,on):
        '''Store changes in the omit keys checkbox group'''

        self.new_values['export/bib/omit_fields']=self.getOmitKeys()

        return


    def omitKeysGroupChanged(self, on, groupbox):
        '''Change check states in the omit keys checkbox group as a whole'''

        omit_keys=[]

        for box in groupbox.findChildren(QtWidgets.QCheckBox):
            box.stateChanged.disconnect()
            box.setChecked(on)
            box.setEnabled(True)
            box.stateChanged.connect(self.omitKeyChanged)
            if box.isChecked():
                omit_keys.append(box.text())

        self.new_values['export/bib/omit_fields']=omit_keys

        return


    def getOmitKeys(self):
        '''Collect check states in the omit key checkbox group'''

        omit_keys=[]

        for box in self.groupbox.findChildren(QtWidgets.QCheckBox):
            if box.isChecked():
                omit_keys.append(box.text())

        return omit_keys


    def loadCitationStyleOptions(self):
        '''Load widgets for the Citaiton Style category'''

        scroll, va=self.createFrame('Citation Styles')
        va.addStretch()

        return scroll


    def loadMiscellaneousOptions(self):
        '''Load widgets for the Miscellaneous category'''

        scroll, va=self.createFrame('Auto Open')

        #-------Open last database on launch section-------
        checkbox=QtWidgets.QCheckBox('Automatically Open Last Database on Start-up?')
        checkbox.stateChanged.connect(self.changeAutoOpenLast)
        auto_open_last=self.settings.value('file/auto_open_last',type=int)
        if auto_open_last==1:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)

        va.addWidget(checkbox)
        va.addWidget(getHLine(self))

        #--------------Recent number section--------------
        label1=QtWidgets.QLabel('Number of Recently Opened Database')
        label1.setStyleSheet(self.label_color)
        label1.setFont(self.title_label_font)
        va.addWidget(label1)

        slider2=LabeledSlider(0,10,1,parent=self)
        slider2.sl.setValue(self.settings.value('file/recent_open_num',type=int))
        slider2.sl.valueChanged.connect(self.changeRecentNumber)
        slider2.setMaximumWidth(400)

        va.addWidget(slider2)
        va.addWidget(getHLine())

        #------------Duplicate check min score------------
        label2=QtWidgets.QLabel('Duplicate Check')
        label2.setStyleSheet(self.label_color)
        label2.setFont(self.title_label_font)
        va.addWidget(label2)

        label3=QtWidgets.QLabel('Minimum Similarity Score to Define Duplicate (1-100)')
        self.spinbox=QtWidgets.QSpinBox()
        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(100)
        self.spinbox.setValue(self.settings.value('duplicate_min_score',type=int))
        self.spinbox.valueChanged.connect(self.changeDuplicateMinScore)

        ha=QtWidgets.QHBoxLayout()
        ha.addWidget(label3)
        ha.addWidget(self.spinbox)
        va.addLayout(ha)

        #----------------thumbnail dpi section----------------
        va.addWidget(getHLine(self))
        label4=QtWidgets.QLabel('PDF thumbnail DPI')
        label4.setStyleSheet(self.label_color)
        label4.setFont(self.title_label_font)
        va.addWidget(label4)
        va.addWidget(getHLine(self))

        slider3=LabeledSlider(10,30,5,parent=self)
        slider3.sl.setValue(self.settings.value('view/thumbnail_dpi',30,type=int))
        slider3.sl.valueChanged.connect(self.changeThumbnailDPI)
        slider3.setMaximumWidth(400)

        va.addWidget(slider3)

        va.addStretch()

        return scroll


    def changeAutoOpenLast(self,on):
        '''Store the check state of the auto open checkbox'''

        if on:
            self.new_values['file/auto_open_last']=1
        else:
            self.new_values['file/auto_open_last']=0

        LOGGER.info('Change auto open last to %s' %on)

        return


    def changeRecentNumber(self,value):
        '''Store the value on the recent open slider'''

        LOGGER.info('Change recent database number to %s' %value)
        self.new_values['file/recent_open_num']=value

        return


    def changeThumbnailDPI(self,value):
        '''Store the value on the thumbnail dpi slider'''

        LOGGER.debug('Change thumbnail dpi number to %s' %value)
        self.new_values['view/thumbnail_dpi']=value

        return


    def changeDuplicateMinScore(self,value):
        '''Store the value in the duplicate minimum score spinbox'''

        LOGGER.info('Change min duplicate score to %s' %value)
        self.new_values['duplicate_min_score']=value

        return


class LabeledSlider(QtWidgets.QWidget):
    def __init__(self, minimum, maximum, interval=1, orientation=Qt.Horizontal,
            labels=None, parent=None):
        '''Slider widget with labels

        Args:
            minimum (int): min value.
            maximum (int): max value.
            interval (int): interval.
        Kwargs:
            orientation (int): orientation.
            labels (str or None): labels.
            parent (QWidget or None): parent widget.
        '''

        super(LabeledSlider, self).__init__(parent=parent)

        levels=range(minimum, maximum+interval, interval)
        if labels is not None:
            if not isinstance(labels, (tuple, list)):
                raise Exception("<labels> is a list or tuple.")
            if len(labels) != len(levels):
                raise Exception("Size of <labels> doesn't match levels.")
            self.levels=list(zip(levels,labels))
        else:
            self.levels=list(zip(levels,map(str,levels)))

        if orientation==Qt.Horizontal:
            self.layout=QtWidgets.QVBoxLayout(self)
        elif orientation==Qt.Vertical:
            self.layout=QtWidgets.QHBoxLayout(self)
        else:
            raise Exception("<orientation> wrong.")

        # gives some space to print labels
        self.left_margin=10
        self.top_margin=10
        self.right_margin=10
        self.bottom_margin=10

        self.layout.setContentsMargins(self.left_margin,self.top_margin,
                self.right_margin,self.bottom_margin)

        self.sl=QtWidgets.QSlider(orientation, self)
        self.sl.setMinimum(minimum)
        self.sl.setMaximum(maximum)
        self.sl.setValue(minimum)
        if orientation==Qt.Horizontal:
            self.sl.setTickPosition(QtWidgets.QSlider.TicksBelow)
            #self.sl.setMinimumWidth(300) # just to make it easier to read
        else:
            self.sl.setTickPosition(QtWidgets.QSlider.TicksLeft)
            #self.sl.setMinimumHeight(300) # just to make it easier to read
        self.sl.setTickInterval(interval)
        self.sl.setSingleStep(1)

        self.layout.addWidget(self.sl)

    def paintEvent(self, e):

        super(LabeledSlider,self).paintEvent(e)

        style=self.sl.style()
        painter=QPainter(self)
        st_slider=QStyleOptionSlider()
        st_slider.initFrom(self.sl)
        st_slider.orientation=self.sl.orientation()

        length=style.pixelMetric(QStyle.PM_SliderLength, st_slider, self.sl)
        available=style.pixelMetric(QStyle.PM_SliderSpaceAvailable, st_slider, self.sl)

        for v, v_str in self.levels:

            # get the size of the label
            rect=painter.drawText(QRect(), Qt.TextDontPrint, v_str)

            if self.sl.orientation()==Qt.Horizontal:
                # I assume the offset is half the length of slider, therefore
                # + length//2
                x_loc=QStyle.sliderPositionFromValue(self.sl.minimum(),
                        self.sl.maximum(), v, available)+length//2

                # left bound of the text = center - half of text width + L_margin
                left=x_loc-rect.width()//2+self.left_margin
                bottom=self.rect().bottom()

                # enlarge margins if clipping
                if v==self.sl.minimum():
                    if left<=0:
                        self.left_margin=rect.width()//2-x_loc
                    if self.bottom_margin<=rect.height():
                        self.bottom_margin=rect.height()

                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

                if v==self.sl.maximum() and rect.width()//2>=self.right_margin:
                    self.right_margin=rect.width()//2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            else:
                y_loc=QStyle.sliderPositionFromValue(self.sl.minimum(),
                        self.sl.maximum(), v, available, upsideDown=True)

                bottom=y_loc+length//2+rect.height()//2+self.top_margin-3
                # there is a 3 px offset that I can't attribute to any metric

                left=self.left_margin-rect.width()
                if left<=0:
                    self.left_margin=rect.width()+2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            pos=QPoint(left, bottom)
            painter.drawText(pos, v_str)

        return

