# -*- coding: utf-8 -*-

"""This module defines various threads related classes to perform time-consuming tasks outside of main event loop."""

from typing import TYPE_CHECKING, Callable

from PyQt5 import QtCore

if TYPE_CHECKING:
    from ...backend.core import Controller


class WorkerThread(QtCore.QThread):

    update = QtCore.pyqtSignal(str)

    def __init__(self, fun: Callable[['WorkerThread', Controller, ...], None], ctrl, params):
        super(WorkerThread, self).__init__()
        self.fun = fun
        self.ctrl = ctrl
        self.params = params
        self.stop = False

    def run(self):
        self.fun(self, self.ctrl, **self.params)

    def println(self, msg, log_file=None):
        # noinspection PyUnresolvedReferences
        self.update.emit(msg)
        if log_file is not None:
            log_file.write(msg + '\n')
            log_file.flush()

    def abort_task(self):
        return self.stop
