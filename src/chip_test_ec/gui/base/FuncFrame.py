# -*- coding: utf-8 -*-

"""This module defines FuncFrame, which contains miscellaneous function buttons."""

from itertools import izip
from PyQt4.QtCore import pyqtSlot
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui

from .FuncDialog import FuncDialog


class FuncFrame(QtGui.QFrame):
    def __init__(self, ctrl, conf_path, logger, vfunc_list, func_list, font_size=11):
        super(FuncFrame, self).__init__()

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        self.ctrl = ctrl
        self.conf_path = conf_path
        self.font_size = font_size
        self.logger = logger
        self.vfunc_list = vfunc_list
        self.func_list = func_list

        lay = QtGui.QVBoxLayout()
        self.setLayout(lay)

        for slot, flist in izip([self.run_vfunc, self.run_func],
                                [vfunc_list, func_list]):
            mapper = QtCore.QSignalMapper(self)
            for idx, fobj in enumerate(flist):
                fun_name = fobj[0]
                button = QtGui.QPushButton(fun_name)
                button.clicked.connect(mapper.map)
                mapper.setMapping(button, idx)
                lay.addWidget(button)
            mapper.mapped[int].connect(slot)

    @pyqtSlot(int)
    def run_vfunc(self, idx):
        fun_name, fun = self.vfunc_list[idx]
        fun(self.ctrl, self.logger)

    @pyqtSlot(int)
    def run_func(self, idx):
        fun_name, fun, fun_specs = self.func_list[idx]
        d = FuncDialog(self, self.ctrl, self.conf_path, fun_name, fun, fun_specs, font_size=self.font_size)
        d.show()
