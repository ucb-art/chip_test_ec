# -*- coding: utf-8 -*-

"""This module defines varous GUI frames."""

from typing import TYPE_CHECKING

from PyQt5 import QtCore, QtGui, QtWidgets

from .dialogs import FuncDialog

if TYPE_CHECKING:
    from .displays import LogWidget


class FuncFrame(QtWidgets.QFrame):
    """A frame of various buttons that run various user defined functions.

    Parameters
    ----------
    ctrl :
        the controller object.
    conf_path : str
        the function settings configuration directory.
    logger : LogWidget
        the LogWidget instance.
    vfunc_list : List[Tuple[str, Callable]]
        list of functions that do not require user input.

        each element is a two-element tuple, where the first element is the text on the button,
        the second element is the Python function object.  The function takes two inputs, the contrller
        object and the logger object.
    func_list :
        list of functions that require user input.

        each element is a three-element tuple.  The first element is the name of the function,
        the second element is the Python function object.  The third element is the input parameters
        specification dictionary to be passed to function dialog.

        the first argument of the function should be worker thread, the second argument of the
        function should be the controller object, the rest of the parameters are passed as keyword
        arguments.
    font_size : int
        the frame font size.
    """
    def __init__(self, ctrl, conf_path: str, logger: LogWidget, vfunc_list, func_list, font_size=11):
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

        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)

        for slot, flist in zip([self.run_vfunc, self.run_func],
                               [vfunc_list, func_list]):
            mapper = QtCore.QSignalMapper(self)
            for idx, fobj in enumerate(flist):
                fun_name = fobj[0]
                button = QtWidgets.QPushButton(fun_name)
                # noinspection PyUnresolvedReferences
                button.clicked.connect(mapper.map)
                mapper.setMapping(button, idx)
                lay.addWidget(button)
            # noinspection PyUnresolvedReferences
            mapper.mapped[int].connect(slot)

    @QtCore.pyqtSlot(int)
    def run_vfunc(self, idx):
        fun_name, fun = self.vfunc_list[idx]
        fun(self.ctrl, self.logger)

    @QtCore.pyqtSlot(int)
    def run_func(self, idx):
        fun_name, fun, fun_specs = self.func_list[idx]
        d = FuncDialog(self, self.ctrl, self.conf_path, fun_name, fun, fun_specs, font_size=self.font_size)
        d.show()
