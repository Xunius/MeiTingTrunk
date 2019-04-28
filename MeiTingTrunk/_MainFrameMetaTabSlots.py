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
from subprocess import Popen
import subprocess
import multiprocessing
import threading
#import pyinotify
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QTemporaryFile,\
        QProcess
from PyQt5 import QtWidgets, QtGui
from .lib.widgets import Master
from concurrent.futures import ThreadPoolExecutor as Pool

def Popen_forked(jobid, *args, **kwargs):  # pylint: disable=invalid-name
    """Forks process and runs Popen with the given args and kwargs."""
    try:
        pid = os.fork()
    except OSError:
        return False
    if pid == 0:
        os.setsid()
        print(args)
        kwargs['stdin'] = open(os.devnull, 'r')
        kwargs['stdout'] = kwargs['stderr'] = open(os.devnull, 'w')
        proc=Popen(*args, **kwargs)
        proc.wait()
        print('# <Popen_forked>: close wait')
        os._exit(0)  # pylint: disable=protected-access
    else:
        os.wait()
    return True


def popenAndCall(onExit, popenArgs):
    """
    Runs the given args in a subprocess.Popen, and then calls the function
    onExit when the subprocess completes.
    onExit is a callable object, and popenArgs is a list/tuple of args that
    would give to subprocess.Popen.
    """
    import psutil
    def runInThread(onExit, popenArgs):
        print(popenArgs)
        tmppath=popenArgs[0][-1]
        proc = subprocess.Popen(*popenArgs)
        proc.wait()

        # find the latest editor process in the list of all running processes
        editor_processes = []
        for p in psutil.process_iter():
            try:
                process_name = p.name()
                if editor_cmd in process_name:
                    editor_processes.append((process_name, p.pid))
            except:
                pass
        editor_proc = psutil.Process(editor_processes[-1][1])

        print(editor_proc)
        rec=editor_proc.wait()

        print('# <runInThread>: onexit', tmppath)
        onExit(tmppath)
        os.remove(tmppath)
        return
    thread = threading.Thread(target=runInThread, args=(onExit, popenArgs))
    thread.start()
    # returns immediately after the thread starts
    return thread

class EditorWorker(QObject):
    file_close_sig = pyqtSignal()
    edit_done_sig = pyqtSignal()

    def __init__(self, command, parent=None):
        super(EditorWorker, self).__init__(parent)
        self._temp_file = QTemporaryFile(self)
        self._process = QProcess(self)
        #self._process.finished.connect(self.on_file_close)
        self.file_close_sig.connect(self.on_file_close)
        self._text = ""
        if self._temp_file.open():
            #program, *arguments = command
            self._process.start(
                program, arguments + [self._temp_file.fileName()]
            )
            tmpfile=self._temp_file.fileName()
            # start a thread to monitor file saving/closing
            self.monitor_thread = threading.Thread(target=self.monitorFile,
                    args=(tmpfile, self.file_close_sig))
            self.monitor_thread.start()

    @pyqtSlot()
    def on_file_close(self):
        if self._temp_file.isOpen():
            print('open')
            self._text = self._temp_file.readAll().data().decode()
            self.edit_done_sig.emit()
        else:
            print('not open')

    @property
    def text(self):
        return self._text

    def __del__(self):
        try:
            self._process.kill()
        except:
            pass

    def monitorFile(self, path, sig):

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

        action_text=action.text()
        print('# <openEditorTriggered>: action',action,action.text())

        if action_text=='Open Editor':
            editor_cmd=self.settings.value('editor',type=str)
            if editor_cmd == '':
                editor_cmd='vim'

        elif action_text=='Choose Editor':
            pass

        #----------------Get exiting texts----------------
        old_lines=self.note_textedit.toPlainText()

        fd, filepath=tempfile.mkstemp()
        print('# <openEditorTriggered>: filepath=',filepath)

        #editor=EditorWorker(['gvim'], self)
        #editor.edit_done_sig.connect(self.onEditingDone)


        def cb(f, tmppath):
            print('# <cb>: cb tmppath=',tmppath)
            if f.exception() is not None:
                print('# <cb>: failed!')
            else:
                with open(tmppath, 'r') as tmp:
                    lines=tmp.readlines()
                    for ii in lines:
                        print('# <openEditorTriggered>: ii',ii)

                    self.note_textedit.setText('\n'.join(lines))
            return

        try:
            with os.fdopen(fd, 'w') as tmp:
                # do stuff with temp file
                tmp.write(old_lines)
                print('# <openEditorTriggered>: close')
                tmp.close()

            with open(filepath, 'r') as tmp:

                cmdflag='--'
                cmd=[os.environ['TERMCMD'], cmdflag, editor_cmd, filepath]
                print('# <cb>: cmd',cmd)

                #pool=Pool(max_workers=1)
                #f=pool.submit(subprocess.call, cmd)
                #f.add_done_callback(lambda f: cb(f, filepath))
                #pool.shutdown(wait=False)
                #Popen_forked(cmd, env=os.environ)
                '''
                self.note_editor_master=Master(Popen_forked,
                        [(0, cmd)],
                        1,
                        close_on_finish=True)
                self.note_editor_master.all_done_signal.connect(lambda:
                        cb(filepath))
                self.note_editor_master.run()
                '''
                td=popenAndCall(cb, cmd)
                #print('# <cb>: rec=',rec)

                #proc=subprocess.call([
                    #editor_cmd, filepath])
                print('# <openEditorTriggered>: #####################')
                #if proc==0:
                    #lines=tmp.readlines()
                    #for ii in lines:
                        #print('# <openEditorTriggered>: ii',ii)

                    #self.note_textedit.setText('\n'.join(lines))
        finally:
            #os.remove(filepath)
            pass

        return






    @pyqtSlot()
    def onEditingDone(self):
        worker = self.sender()
        prev_cursor = self.note_textedit.textCursor()
        self.note_textedit.moveCursor(QtGui.QTextCursor.End)
        self.note_textedit.insertPlainText(worker.text)
        self.note_textedit.setTextCursor(prev_cursor)
        worker.deleteLater()
