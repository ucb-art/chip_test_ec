# -*- coding: utf-8 -*-

"""This module defines various dialogs.
"""

from typing import Callable, Dict, Any

from PyQt5 import QtWidgets, QtGui, QtCore

from .forms import TitledForm
from .displays import LogWidget
from .threads import WorkerThread

# type check imports
from ...backend.core import Controller


class FormDialog(QtWidgets.QDialog):
    """A general dialog for user input forms, with OK and Cancel buttons.

    Parameters
    ----------
    parent :
        the parent of this dialog.
    frame :
        the center frame of this dialog.
    title : str
        the dialog title.
    """
    def __init__(self, parent, frame, title):
        super(FormDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.ok_button = QtWidgets.QPushButton('OK', parent=self)
        self.cancel_button = QtWidgets.QPushButton('Cancel', parent=self)
        # noinspection PyUnresolvedReferences
        self.ok_button.clicked.connect(self.accept)
        # noinspection PyUnresolvedReferences
        self.cancel_button.clicked.connect(self.reject)

        bot_frame = QtWidgets.QFrame(parent=self)
        bot_lay = QtWidgets.QHBoxLayout(bot_frame)
        bot_lay.addWidget(self.ok_button)
        bot_lay.addWidget(self.cancel_button)

        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.addWidget(frame)
        self.lay.addWidget(bot_frame)


class FuncDialog(QtWidgets.QDialog):
    """A dialog that takes inputs from user then runs a user-defined function.

    parent :
        the parent of this dialog.
    ctrl : Controller
        the controller object.
    conf_path : str
        the configuration directory path.
    name : str
        name of this dialog.
    fun : Callable
        the function to execute.
    specs : Dict[str, Any]
        input parameter specifications dictionary.
    font_size : int
        the font size.
    """
    def __init__(self, parent, ctrl: Controller, conf_path: str, name: str, fun: Callable, specs: Dict[str, Any],
                 font_size: int=11):
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
                                     buttons=False, show_title=False, parent=self)
        self.ok_button = QtWidgets.QPushButton('Start', parent=self)
        self.cancel_button = QtWidgets.QPushButton('Abort', parent=self)
        # noinspection PyUnresolvedReferences
        self.ok_button.clicked.connect(self.start_task)
        # noinspection PyUnresolvedReferences
        self.cancel_button.clicked.connect(self.abort_task)
        self.cancel_button.setEnabled(False)

        self.logger = LogWidget()

        bot_frame = QtWidgets.QFrame(parent=self)
        bot_lay = QtWidgets.QHBoxLayout(bot_frame)
        bot_lay.addWidget(self.ok_button)
        bot_lay.addWidget(self.cancel_button)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.param_edit)
        lay.addWidget(bot_frame)
        lay.addWidget(self.logger)

    @QtCore.pyqtSlot(str)
    def update_msg(self, msg: str):
        self.logger.println(msg)

    @QtCore.pyqtSlot()
    def start_task(self):
        if self.thread is None:
            self.ok_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            params = self.param_edit.get_form_values()
            self.thread = WorkerThread(self.fun, self.ctrl, params)

            # noinspection PyUnresolvedReferences
            self.thread.finished.connect(self.finish_task)
            self.thread.update[str].connect(self.update_msg)
            self.thread.start()

    @QtCore.pyqtSlot()
    def abort_task(self):
        self.thread.stop = True

    @QtCore.pyqtSlot()
    def finish_task(self):
        self.ok_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.thread = None
