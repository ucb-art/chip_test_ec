# -*- coding: utf-8 -*-

"""This module defines varous GUI frames."""

from typing import Dict, Any

import os
import pkg_resources

import numpy as np
from sklearn.isotonic import IsotonicRegression

from PyQt5 import QtCore, QtGui, QtWidgets

from .dialogs import FuncDialog

# type check imports
from .displays import LogWidget
from ...backend.core import Controller

activity_gif = pkg_resources.resource_filename('chip_test_ec.gui', os.path.join('resources', 'ajax-loader.gif'))


class FrameBase(QtWidgets.QFrame):
    """The base class of all GUI frames.

    Parameters
    ----------
    ctrl : Controller
        the controller object.
    font_size : int
        the frame font size.
    parent : Optional[QtCore.QObject]
        the parent object.
    """
    def __init__(self, ctrl: Controller, font_size=11, parent=None):
        super(FrameBase, self).__init__(parent=parent)

        # set to delete on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        # set controller attribute
        self.ctrl = ctrl

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        # set layout manager
        self.lay = QtWidgets.QGridLayout(parent=self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lay)

    def create_sub_frame(self):
        """Create a sub-frame with outline, using QGridLayout."""
        frame = QtWidgets.QFrame(parent=self)
        frame.setLineWidth(1)
        frame.setMidLineWidth(1)
        frame.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        lay = QtWidgets.QGridLayout(parent=frame)
        lay.setContentsMargins(0, 0, 0, 0)
        frame.setLayout(lay)
        return frame, lay


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


class ScanDisplayFrame(FrameBase):
    """A frame that display scan chain values and provides real-time update utilities.

    Parameters
    ----------
    ctrl : Controller
        the controller object.
    specs : Dict[str, Any]
        the specification dictionary.
    font_size : int
        the frame font size.
    parent : Optional[QtCore.QObject]
        the parent object.
    """

    scanChainChanged = QtCore.pyqtSignal(str)

    def __init__(self, ctrl: Controller, specs: Dict[str, Any], font_size=11, parent=None):
        super(ScanDisplayFrame, self).__init__(ctrl, font_size=font_size, parent=parent)

        # add scan callback
        # noinspection PyUnresolvedReferences
        self.ctrl.fpga.add_callback(self.scanChainChanged.emit)
        # noinspection PyUnresolvedReferences
        self.scanChainChanged[str].connect(self._update_from_scan)

        # configure frame outline
        self.setLineWidth(1)
        self.setMidLineWidth(1)
        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)

        # create display frame
        self.disp_list, self.chain_names = self.create_displays(self.ctrl.fpga, specs, font_size)

    def create_displays(self, fpga, specs, font_size):
        disp_font = QtGui.QFont('Monospace')
        disp_font.setStyleHint(QtGui.QFont.TypeWriter)
        disp_font.setPointSize(font_size)

        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        disp_list = []
        row_idx, col_idx = 0, 0
        update_chains = set()
        for disp_col in specs:
            for disp_info in disp_col:
                chain_name = disp_info['chain']
                bus_name = disp_info['bus']
                disp_type = disp_info['dtype']
                start = disp_info.get('start', 0)
                step = disp_info.get('step', 1)

                num_bits = fpga.get_scan_length(chain_name, bus_name)
                scan_val = fpga.get_scan(chain_name, bus_name)

                update_chains.add(chain_name)

                if disp_type == 'int':
                    disp_str = str(scan_val)
                elif disp_type == 'bin':
                    disp_str = np.binary_repr(scan_val, num_bits)
                else:
                    raise ValueError('display type %s not supported.' % disp_type)

                if step == 1:
                    label_name = bus_name
                else:
                    label_name = '%s[%d]' % (bus_name, start)
                    # MSB binary string has index 0
                    disp_str = disp_str[step - start - 1::step]

                label = QtWidgets.QLabel(label_name, parent=self)
                label.setAlignment(align_label)

                disp_field = QtWidgets.QLabel(disp_str, parent=self)
                disp_field.setFont(disp_font)

                self.lay.addWidget(label, row_idx, col_idx)
                self.lay.addWidget(disp_field, row_idx, col_idx + 1)
                disp_list.append((disp_field, chain_name, bus_name, disp_type, num_bits, (start, step)))
                row_idx += 1

            row_idx = 0
            col_idx += 2

        return disp_list, update_chains

    @QtCore.pyqtSlot(str)
    def _update_from_scan(self, chain_name):
        if chain_name in self.chain_names:
            fpga = self.ctrl.fpga

            # update displays
            for disp_field, cur_chain_name, bus_name, disp_type, nbits, (start, step) in self.disp_list:
                scan_val = fpga.get_scan(cur_chain_name, bus_name)
                if disp_type == 'int':
                    disp_str = str(scan_val)
                else:
                    # MSB binary string has index 0
                    disp_str = np.binary_repr(scan_val, nbits)[step - start - 1::step]
                disp_field.setText(disp_str)


class ScanControlFrame(FrameBase):
    """A frame that groups various scan .

    Parameters
    ----------
    ctrl : Controller
        the controller object.
    specs : Dict[str, Any]
        the specification dictionary.
    font_size : int
        the frame font size.
    parent : Optional[QtCore.QObject]
        the parent object.
    """

    scanChainChanged = QtCore.pyqtSignal(str)

    def __init__(self, ctrl: Controller, specs: Dict[str, Any], font_size=11, parent=None):
        super(ScanControlFrame, self).__init__(ctrl, font_size=font_size, parent=parent)

        # add scan callback
        # noinspection PyUnresolvedReferences
        self.ctrl.fpga.add_callback(self.scanChainChanged.emit)
        # noinspection PyUnresolvedReferences
        self.scanChainChanged[str].connect(self._update_from_scan)

        # configure frame outline
        self.setLineWidth(1)
        self.setMidLineWidth(1)
        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)

        # create and add components
        self.spin_box_list, self.check_box_list, self.val_lookup = self.create_controls(self.ctrl.fpga, specs)

    def create_controls(self, fpga, specs):
        char_dir = specs['char_dir']
        spin_boxes = specs['spin_box']
        check_boxes = specs['check_box']

        # add spin boxes
        align_value = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        spin_box_list = []
        val_label_lookup = {}
        row_idx, col_idx = 0, 0
        for spin_box_col in spin_boxes:
            for spin_info in spin_box_col:
                chain_name = spin_info['chain']
                bus_name = spin_info['bus']
                label_name = spin_info.get('name', bus_name)
                fname = spin_info.get('fname', None)
                scale = spin_info.get('scale', 1.0)
                unit = spin_info.get('unit', '')

                scan_val = fpga.get_scan(chain_name, bus_name)
                num_bits = fpga.get_scan_length(chain_name, bus_name)

                obj_name = '%s.%s' % (chain_name, bus_name)

                # create and add label
                name_label = QtWidgets.QLabel(label_name, parent=self)
                self.lay.addWidget(name_label, row_idx, col_idx, 1, 2)
                row_idx += 1

                # create and add spin box
                spin_box = QtWidgets.QSpinBox(parent=self)
                spin_box.setObjectName(obj_name)
                spin_box.setSingleStep(1)
                self.lay.addWidget(spin_box, row_idx, col_idx)

                # set spin box value and create/add value label if necessary
                if fname:
                    # load characterization file
                    mat = np.loadtxt(os.path.join(char_dir, fname))
                    # fit with monotonic regression
                    reg = IsotonicRegression(increasing='auto')
                    xvec = mat[:, 0]
                    offset = int(round(np.min(xvec)))
                    yvec_mono = reg.fit_transform(xvec, mat[:, 1])
                    # set max and min based on characterization file
                    max_val = int(round(np.max(xvec)))
                    spin_box.setMaximum(max_val)
                    spin_box.setMinimum(offset)
                    if scan_val < offset or scan_val > max_val:
                        raise ValueError('Default scan values outside characterization bounds')
                    spin_box.setValue(scan_val)

                    val_text = '%.4g %s' % (yvec_mono[scan_val - offset] * scale, unit)
                    val_label = QtWidgets.QLabel(val_text, parent=self)
                    val_label.setAlignment(align_value)
                    val_label_lookup[obj_name] = (val_label, offset, scale, unit, yvec_mono)
                    # noinspection PyUnresolvedReferences
                    spin_box.valueChanged[int].connect(self._update_label)

                    # add value label
                    self.lay.addWidget(val_label, row_idx, col_idx + 1)
                else:
                    spin_box.setMaximum((1 << num_bits) - 1)
                    spin_box.setMinimum(0)
                    spin_box.setValue(scan_val)

                # noinspection PyUnresolvedReferences
                spin_box.valueChanged[int].connect(self._update_scan)

                row_idx += 1
                spin_box_list.append(spin_box)

            row_idx = 0
            col_idx += 2

        # add check boxes
        check_box_list = []
        for check_box_col in check_boxes:
            for check_info in check_box_col:
                chain_name = check_info['chain']
                bus_name = check_info['bus']
                label_name = check_info.get('name', bus_name)

                scan_val = fpga.get_scan(chain_name, bus_name)
                num_bits = fpga.get_scan_length(chain_name, bus_name)

                obj_name = '%s.%s' % (chain_name, bus_name)

                if num_bits != 1:
                    msg = 'Cannot represent scan bus %s with %d bits with a check box' % (obj_name, num_bits)
                    raise ValueError(msg)

                # create and add checkbox
                check_box = QtWidgets.QCheckBox(label_name, parent=self)
                check_box.setObjectName(obj_name)
                check_state = QtCore.Qt.Checked if scan_val == 1 else QtCore.Qt.Unchecked
                check_box.setCheckState(check_state)
                # noinspection PyUnresolvedReferences
                check_box.stateChanged[int].connect(self._update_scan)

                self.lay.addWidget(check_box, row_idx, col_idx)
                check_box_list.append(check_box)
                row_idx += 1

            row_idx = 0
            col_idx += 1

        return spin_box_list, check_box_list, val_label_lookup

    @QtCore.pyqtSlot(str)
    def _update_from_scan(self, chain_name):
        fpga = self.ctrl.fpga

        # update spin boxes
        for spin_box in self.spin_box_list:
            obj_name = spin_box.objectName()
            cur_chain_name, bus_name = obj_name.split('.', 1)
            cur_value = spin_box.value()
            if cur_chain_name == chain_name:
                new_value = fpga.get_scan(chain_name, bus_name)
                if cur_value != new_value:
                    spin_box.setValue(new_value)
        # update check boxes
        for check_box in self.check_box_list:
            obj_name = check_box.objectName()
            cur_chain_name, bus_name = obj_name.split('.', 1)
            cur_state = check_box.checkState()
            if cur_chain_name == chain_name:
                new_value = fpga.get_scan(chain_name, bus_name)
                new_state = QtCore.Qt.Checked if new_value == 1 else QtCore.Qt.Unchecked
                if cur_state != new_state:
                    check_box.setCheckState(new_state)

    @QtCore.pyqtSlot(int)
    def _update_label(self, val):
        obj_name = self.sender().objectName()
        val_label, offset, scale, unit, yvec = self.val_lookup[obj_name]
        val_label.setText('%.4g %s' % (yvec[val - offset] * scale, unit))

    @QtCore.pyqtSlot(int)
    def _update_scan(self, val):
        send_obj = self.sender()
        if isinstance(send_obj, QtWidgets.QCheckBox):
            val = 1 if val == QtCore.Qt.Checked else 0
        obj_name = send_obj.objectName()
        chain_name, bus_name = obj_name.split('.', 1)
        fpga = self.ctrl.fpga
        cur_val = fpga.get_scan(chain_name, bus_name)
        if cur_val != val:
            fpga.set_scan(chain_name, bus_name, val)
            fpga.update_scan(chain_name)

    @QtCore.pyqtSlot(int)
    def update_step_size(self, val):
        for spin_box in self.spin_box_list:
            spin_box.setSingleStep(val)
