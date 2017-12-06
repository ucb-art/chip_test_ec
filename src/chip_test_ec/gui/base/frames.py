# -*- coding: utf-8 -*-

"""This module defines varous GUI frames."""

from typing import Dict, Any

from PyQt5 import QtCore, QtGui, QtWidgets

from .dialogs import FuncDialog
from .forms import TitledForm

# type check imports
from .displays import LogWidget
from ...backend.core import Controller


class FuncFrame(QtWidgets.QFrame):
    """A frame of various buttons that run various user defined functions.

    Parameters
    ----------
    ctrl : Controller
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
    def __init__(self, ctrl: Controller, conf_path: str, logger: LogWidget, vfunc_list, func_list, font_size=11):
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


class ControllerFrame(QtWidgets.QFrame):
    """A frame used to obtain user input needed to create a Controller instance.

    Parameters
    ----------
    conf_path : str
        path to configuration directory.
    specs : Dict[str, Any]
        Controller configuration dictionary.
    font_size : int
        font size of this component.
    """
    def __init__(self, conf_path: str, specs: Dict[str, Any], font_size: int=11) -> None:
        super(ControllerFrame, self).__init__()

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        # create forms for FPGA/scan/GPIB
        self.fpga_form = TitledForm('FPGA', conf_path, specs['fpga'], font_size=font_size)
        self.scan_form = TitledForm('Scan', conf_path, specs['scan'], font_size=font_size)
        gpib_specs = specs['gpib']
        self.gpib_forms = []
        for name in gpib_specs['order']:
            form = TitledForm(name, conf_path, gpib_specs[name], font_size=font_size)
            self.gpib_forms.append(form)

        self.lay = QtWidgets.QVBoxLayout()
        self.setLayout(self.lay)
        self.lay.addWidget(self.fpga_form)
        self.lay.addWidget(self.scan_form)
        for form in self.gpib_forms:
            self.lay.addWidget(form)

    def get_controller_specs(self) -> Dict[str, Any]:
        """Returns the Controller specification dictionary.

        Returns
        -------
        ctrl_specs : Dict[str, Any]
            the Controller specification dictionary.
        """
        fpga_params = self.fpga_form.get_form_values()
        fpga_module = fpga_params.pop('module')
        fpga_class = fpga_params.pop('class')
        fpga_info = {'module': fpga_module,
                     'class': fpga_class,
                     'params': fpga_params}

        scan_info = self.scan_form.get_form_values()

        gpib_info = {}
        for form in self.gpib_forms:
            cur_params = form.get_form_values()
            cur_module = cur_params.pop('module')
            cur_class = cur_params.pop('class')
            cur_info = {'module': cur_module,
                        'class': cur_class,
                        'params': cur_params}
            gpib_info[form.name] = cur_info

        return dict(fpga=fpga_info, scan=scan_info, gpib=gpib_info)
