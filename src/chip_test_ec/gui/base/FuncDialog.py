# -*- coding: utf-8 -*-

"""This module defines FormDialog, a dialog for user input forms with OK/cancel.
"""

import PyQt4.QtCore as QtCore
from PyQt4.QtCore import pyqtSlot, pyqtSignal
import PyQt4.QtGui as QtGui

from .TitledForm import TitledForm
from .LogWidget import LogWidget


class WorkerThread(QtCore.QThread):

    update = pyqtSignal(str)

    def __init__(self, fun, ctrl, params):
        super(WorkerThread, self).__init__()
        self.fun = fun
        self.ctrl = ctrl
        self.params = params
        self.stop = False

    def run(self):
        self.fun(self, self.ctrl, **self.params)

    def println(self, msg, log_file=None):
        self.update.emit(msg)
        if log_file is not None:
            log_file.write(msg + '\n')
            log_file.flush()

    def abort_task(self):
        return self.stop


class FuncDialog(QtGui.QDialog):
    """A general dialog for user input forms
    """
    def __init__(self, parent, ctrl, conf_path, name, fun, specs, font_size=11):
        """Create a new FormDialog.

        Parameters
        ----------
        parent :
            the parent of this dialog.
        ctrl :
            the controller object.
        conf_path : str
            the configuration directory path.
        name : str
            name of this dialog.
        fun : callable
            the function to execute.
        specs : list[tuple]
            list of parameter specifications.
        font_size : int
            the font size.
        """
        super(FuncDialog, self).__init__(parent)

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        self.setWindowTitle(name)
        self.fun = fun
        self.ctrl = ctrl
        self.thread = None

        self.setModal(True)

        self.param_edit = TitledForm(name, conf_path, specs, font_size=font_size,
                                     show_title=False)
        self.ok_button = QtGui.QPushButton('Start')
        self.cancel_button = QtGui.QPushButton('Abort')
        self.ok_button.clicked.connect(self.start_task)
        self.cancel_button.clicked.connect(self.abort_task)
        self.cancel_button.setEnabled(False)

        self.logger = LogWidget()

        bot_lay = QtGui.QHBoxLayout()
        bot_lay.addWidget(self.ok_button)
        bot_lay.addWidget(self.cancel_button)
        bot_frame = QtGui.QFrame()
        bot_frame.setLayout(bot_lay)

        lay = QtGui.QVBoxLayout()
        self.setLayout(lay)
        lay.addWidget(self.param_edit)
        lay.addWidget(bot_frame)
        lay.addWidget(self.logger)

    @pyqtSlot(str)
    def update_msg(self, msg):
        self.logger.println(msg)

    @pyqtSlot()
    def start_task(self):
        if self.thread is None:
            self.ok_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            params = self.param_edit.get_form_values()
            self.thread = WorkerThread(self.fun, self.ctrl, params)

            self.thread.finished.connect(self.finish_task)
            self.thread.update[str].connect(self.update_msg)
            self.thread.start()

    @pyqtSlot()
    def abort_task(self):
        self.thread.stop = True

    @pyqtSlot()
    def finish_task(self):
        self.ok_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.thread = None
