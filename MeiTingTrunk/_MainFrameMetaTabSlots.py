'''
Contains a few functions manipulating the meta tab.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import tempfile
import logging
from subprocess import Popen
import subprocess
import multiprocessing
import threading
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QTemporaryFile,\
        QProcess, QFileSystemWatcher
from PyQt5 import QtWidgets, QtGui
from .lib.widgets import Master, ChooseAppDialog

#import platform
#CURRENT_OS=platform.system()
#if CURRENT_OS=='Linux':
    #import pyinotify
#elif CURRENT_OS=='Darwin':
    #pass

# list of editors that run in terminal
TERMINAL_EDITORS=['vi', 'vim', 'nano']




def getTerminal():
    '''Get the default terminal'''

    term=os.environ.get('TERMCMD', os.environ['TERM'])

    # Handle aliases of xterm and urxvt, rxvt.
    # Match 'xterm', 'xterm-256color'
    if term.startswith('xterm'):
        term = 'xterm'
    if term in ['urxvt', 'rxvt-unicode']:
        term = 'urxvt'
    if term in ['rxvt', 'rxvt-256color']:
        term = 'rxvt'

    # check term
    prop=subprocess.Popen('which %s' %term, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    rec=prop.communicate()
    if len(rec[0])==0 and len(rec[1])>0:
        term='xterm'

    # Choose correct cmdflag accordingly
    if term in ['xfce4-terminal', 'mate-terminal', 'terminator']:
        cmdflag = '-x'
    elif term in ['xterm', 'urxvt', 'rxvt', 'lxterminal',
                  'konsole', 'lilyterm', 'cool-retro-term',
                  'terminology', 'pantheon-terminal', 'termite',
                  'st', 'stterm']:
        cmdflag = '-e'
    elif term in ['gnome-terminal', ]:
        cmdflag = '--'
    elif term in ['tilda', ]:
        cmdflag = '-c'
    else:
        cmdflag = '-e'

    return term, cmdflag



class EditorWorker(QObject):

    file_change_sig = pyqtSignal()

    def __init__(self, command, old_text, parent=None):
        super(EditorWorker, self).__init__(parent)

        self._temp_file = QTemporaryFile(self)
        self._process = QProcess(self)
        self._text = ""
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self.onFileChange)
        self.logger=logging.getLogger(__name__)

        # write existing lines
        if self._temp_file.open():
            self._temp_file.write(old_text.encode('utf-8'))
            self._temp_file.close()

        if self._temp_file.open():
            self._file_path=self._temp_file.fileName()
            self._watcher.addPath(self._file_path)
            self.logger.debug('_file_path = %s' %self._file_path)

            program=command[0]
            arguments = command[1:]
            self._process.start(
                program, arguments + [self._temp_file.fileName()]
            )

    @pyqtSlot()
    def onFileChange(self):
        if self._temp_file.isOpen():

            #self._temp_file.seek(0)
            #self._text = self._temp_file.readAll().data().decode()

            # has to use with open and read(), the above doesn't work for
            # some editors, like xed
            with open(self._temp_file.fileName()) as tmp:
                self._text=tmp.read()

            # Re-add watch file, again for xed.
            self._watcher.removePath(self._file_path)
            self._watcher.addPath(self._file_path)

            self.file_change_sig.emit()

    @property
    def text(self):
        return self._text

    def __del__(self):
        self._process.kill()


class MainFrameMetaTabSlots:

    #######################################################################
    #                            Meta tab slots                           #
    #######################################################################

    def clearMetaTab(self):

        for kk,vv in self._current_meta_dict.items():
            if kk=='files_l':
                self.t_meta.delFileField()
            else:
                vv.clear()
                vv.setReadOnly(True)

        for tii in [self.note_textedit, self.bib_textedit]:
            tii.clear()
            tii.setReadOnly(True)

        self.confirm_review_frame.setVisible(False)

        self.logger.debug('Meta tab cleared.')

        return


    def enableMetaTab(self):

        for kk,vv in self._current_meta_dict.items():
            if kk!='files_l':
                vv.setReadOnly(False)

        for tii in [self.note_textedit, ]:
            tii.setReadOnly(False)

        return


    @pyqtSlot()
    def confirmReviewButtonClicked(self):
        """Confirm meta data of a doc is correct

        This involves:
            * set DocMeta['confirmed']='true'
            * hide self.confirm_reivew_frame.
            * update current doc table
            * remove docid from the Needs Review folder (id='-2')
        """

        docid=self._current_doc

        self.meta_dict[docid]['confirmed']='true'

        self.logger.debug("doc id = %s. meta_dict[docid]['confirmed'] = %s"\
                %(docid, self.meta_dict[docid]['confirmed']))

        self.confirm_review_frame.setVisible(False)
        idx=self.doc_table.currentIndex()
        self.doc_table.model().dataChanged.emit(idx,idx)

        # del doc from needs review folder
        if docid in self.folder_data['-2']:
            self.folder_data['-2'].remove(docid)

        self.loadDocTable(folder=self._current_folder,sortidx=None,
                sel_row=idx.row())

        return


    @pyqtSlot(QtWidgets.QAction)
    def openEditorTriggered(self, action):
        '''Open editor externally

        Args:
            action (QAction): action triggered
        '''

        action_text=action.text()
        self.logger.debug('action = %s' %action_text)

        if action_text=='Open Editor':
            editor_cmd=self.settings.value('editor',type=str)
            if editor_cmd == '':
                editor_cmd='vim'
            self.logger.debug('editor_cmd = %s' %editor_cmd)

            #----------------Get exiting texts----------------
            old_text=self.note_textedit.toPlainText()

            #-------------------Get terminal-------------------
            if editor_cmd in TERMINAL_EDITORS:
                term, cmdflag=getTerminal()
                self.logger.debug('term = %s, cmdflag = %s' %(term, cmdflag))

                cmd=[term, cmdflag, editor_cmd]
            else:
                cmd=[editor_cmd,]

            #--------------------Get editor--------------------
            self.note_textedit.editor=EditorWorker(cmd, old_text, self)
            self.note_textedit.editor.file_change_sig.connect(self.onEditingDone)

        elif action_text=='Choose Editor':
            diag=ChooseAppDialog('Choose Editor', 'editor', self.settings,
                    self)
            choice=diag.exec_()

            if choice==QtWidgets.QDialog.Accepted:
                editor_cmd=diag.le.text()
                self.logger.debug('New editor_cmd = %s' %editor_cmd)
                self.settings.setValue('editor', editor_cmd)
            elif choice==QtWidgets.QDialog.Rejected:
                pass

        return


    @pyqtSlot()
    def onEditingDone(self):
        worker = self.sender()
        self.note_textedit.clear()
        prev_cursor = self.note_textedit.textCursor()
        self.note_textedit.moveCursor(QtGui.QTextCursor.End)
        self.note_textedit.insertPlainText(worker.text)
        self.note_textedit.setTextCursor(prev_cursor)
        self.note_textedit.note_edited_signal.emit()
        #worker.deleteLater()

        return


    @pyqtSlot(int)
    def currentTabChange(self, idx):
        '''Slot to currentChanged signal of QTabWidget

        Args:
            idx (int): idx of current widget in the QTabWidget

        This is only used to force a call of loadPDFThumbnail()
        '''

        current_widget=self.tabs.widget(idx)

        if current_widget==self.t_pdf:
            docid=self._current_doc
            self.loadPDFThumbnail(docid)

        return





"""
class EditorWorker_old(QObject):

    file_close_sig = pyqtSignal()  # emit on file closing/writing
    edit_done_sig = pyqtSignal()   # emit after text reading in

    def __init__(self, command, old_text, parent=None):
        '''Worker to handle launching external editor and reading in saved text

        Args:
            command (list): list of command strings to pass to QProcess.
            old_text (str): exisiting texts in textedit.
        Kwargs:
            parent (QObject): parent widget.
        '''

        super(EditorWorker, self).__init__(parent)

        self._temp_file = QTemporaryFile(self)
        self._process = QProcess(self)
        self.file_close_sig.connect(self.on_file_close)
        self._text = ""

        # write existing lines
        if self._temp_file.open():
            self._temp_file.write(old_text.encode('utf-8'))
            self._temp_file.close()

        # launch editor
        if self._temp_file.open():

            tmpfile=self._temp_file.fileName()
            program = command[0]
            arguments=command[1:]

            try:
                self._process.start(program, arguments + [self._temp_file.fileName()])
            except Exception:
                msg=QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText("Failed to launch editor.")
                msg.exec_()
                logger=logging.getLogger(__name__)
                logger.exception('failed to launch editor')
            else:
                # start a thread to monitor file saving/closing
                self.monitor_thread = threading.Thread(target=self.monitorFile,
                        args=(tmpfile, self.file_close_sig), daemon=True)
                self.monitor_thread.start()


    @pyqtSlot()
    def on_file_close(self):

        if self._temp_file.isOpen():
            self._text = self._temp_file.readAll().data().decode()
            self.edit_done_sig.emit()


    @property
    def text(self):
        return self._text


    def __del__(self):
        try:
            self._process.kill()
        except:
            pass


    def monitorFile(self, path, sig):
        '''Monitor a given file and fire signal on file writing/closing

        Args:
            path (str): abs file path to monitor
            sig (pyqtSignal): signal to emit on event happening
        '''

        class PClose(pyinotify.ProcessEvent):
            def my_init(self):
                self.sig=sig
                self.done=False

            def process_IN_CLOSE(self, event):
                f = event.name and os.path.join(event.path, event.name) or event.path
                self.sig.emit()
                self.done=True

        wm = pyinotify.WatchManager()
        eventHandler=PClose()
        notifier = pyinotify.Notifier(wm, eventHandler)
        wm.add_watch(path, pyinotify.IN_CLOSE_WRITE)

        try:
            while not eventHandler.done:
                notifier.process_events()
                if notifier.check_events():
                    notifier.read_events()
        except KeyboardInterrupt:
            notifier.stop()
            return
"""
