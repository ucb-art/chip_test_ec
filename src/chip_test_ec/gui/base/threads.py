# -*- coding: utf-8 -*-

"""This module defines various threads related classes to perform time-consuming tasks outside of main event loop."""

from typing import Dict, Any

import os

import yaml

from PyQt5 import QtCore

# type check imports
from ...backend.core import Controller
from ...util.core import import_class


class WorkerThread(QtCore.QThread):

    update = QtCore.pyqtSignal(str)

    def __init__(self, ctrl: Controller, config: Dict[str, Any]):
        super(WorkerThread, self).__init__()
        self.config = config
        self.ctrl = ctrl
        self.stop = False
        self.log_fname = config.get('log_file', None)
        if self.log_fname:
            if not config.get('append_log', False):
                os.makedirs(os.path.dirname(self.log_fname), exist_ok=True)
                with open(self.log_fname, 'w'):
                    pass

    def run(self):
        mod_name = self.config['module']
        cls_name = self.config['class']
        params = self.config['params']
        fun_cls = import_class(mod_name, cls_name)
        fun_obj = fun_cls(self, self.ctrl, params)
        fun_obj.run()

    def println(self, msg):
        # noinspection PyUnresolvedReferences
        self.update.emit(msg)
        if self.log_fname:
            with open(self.log_fname, 'a') as f:
                f.write(msg + '\n')

    def send(self, obj):
        msg = yaml.dump(obj)

        # noinspection PyUnresolvedReferences
        self.update.emit(msg)
        if self.log_fname:
            with open(self.log_fname, 'a') as f:
                f.write(msg + '\n')
