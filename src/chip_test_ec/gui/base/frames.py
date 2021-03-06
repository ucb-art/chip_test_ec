# -*- coding: utf-8 -*-

"""This module defines varous GUI frames."""

from typing import Dict, Any, Optional

import os
import pkg_resources

import yaml
import numpy as np
from sklearn.isotonic import IsotonicRegression

from PyQt5 import QtCore, QtGui, QtWidgets

from .dialogs import FuncDialog

# type check imports
from .displays import LogWidget, BERDisplay
from .fields import LineEditBinary
from ...backend.core import Controller

activity_gif = pkg_resources.resource_filename('chip_test_ec.gui', os.path.join('resources', 'ajax-loader.gif'))


class FrameBase(QtWidgets.QFrame):
    """The base class of all GUI frames.

    Parameters
    ----------
    ctrl : Controller
        the controller object.
    conf_path : str
        Default path to save/load configuration files.
        If empty, defaults to current working directory
    font_size : int
        the font size for this frame.
    parent : Optional[QtCore.QObject]
        the parent object
    """
    def __init__(self, ctrl: Controller, conf_path: str='',
                 font_size: int=11, parent: Optional[QtCore.QObject]=None):
        super(FrameBase, self).__init__(parent=parent)
        self.conf_path = os.getcwd() if not conf_path else conf_path

        # set to delete on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        # set controller attribute
        self.ctrl = ctrl

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        # set layout manager
        self.lay = QtWidgets.QGridLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Minimum)

    def create_sub_frame(self):
        """Create a sub-frame with outline, using QGridLayout."""
        frame = QtWidgets.QFrame(parent=self)
        frame.setLineWidth(1)
        frame.setMidLineWidth(1)
        frame.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        lay = QtWidgets.QGridLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)

        frame.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                            QtWidgets.QSizePolicy.Minimum)

        return frame, lay

    def create_input_controls(self, row_list, lay, row_offset=0, col_offset=0):
        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        align_value = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        row_idx, col_idx = row_offset, col_offset
        widget_list = []
        for row_info in row_list:
            for item_info in row_info:
                name = item_info['name']
                dtype = item_info['dtype']
                ncol = item_info.get('ncol', 1)
                obj_name = dtype + '_' + name

                name_label = QtWidgets.QLabel(name, parent=self)
                lay.addWidget(name_label, row_idx, col_idx, alignment=align_label)

                if dtype == 'int':
                    vmin = item_info['vmin']
                    vmax = item_info['vmax']
                    vdef = item_info.get('vdef', (vmin + vmax) // 2)
                    step = item_info.get('step', 1)

                    widget = QtWidgets.QSpinBox(parent=self)
                    widget.setSingleStep(step)
                    widget.setMaximum(vmax)
                    widget.setMinimum(vmin)
                    widget.setValue(vdef)
                elif dtype == 'str':
                    vdef = item_info.get('vdef', '')
                    widget = QtWidgets.QLineEdit(vdef, parent=self)
                elif dtype == 'float':
                    vmin = item_info['vmin']
                    vmax = item_info['vmax']
                    vdef = item_info.get('vdef', (vmin + vmax) // 2)
                    ndec = item_info.get('decimals', 4)

                    widget = QtWidgets.QLineEdit(str(vdef), parent=self)
                    validator = QtGui.QDoubleValidator(vmin, vmax, ndec, parent=widget)
                    widget.setValidator(validator)
                elif dtype == 'bool':
                    vdef = item_info.get('vdef', False)

                    widget = QtWidgets.QCheckBox(parent=self)
                    state = QtCore.Qt.Checked if vdef else QtCore.Qt.Unchecked
                    widget.setCheckState(state)
                elif dtype == 'bin':
                    vdef = item_info.get('vdef', 0)
                    nbits = item_info['nbits']

                    widget = LineEditBinary(vdef, nbits, parent=self)
                elif dtype == 'choice':
                    values = item_info['values']
                    vdef = item_info.get('vdef', 0)

                    widget = QtWidgets.QComboBox(parent=self)
                    widget.addItems(values)
                    widget.setCurrentIndex(vdef)
                else:
                    raise ValueError('Unknown control data type: ' + dtype)

                widget.setObjectName(obj_name)
                lay.addWidget(widget, row_idx, col_idx + 1, 1, ncol, alignment=align_value)
                widget_list.append(widget)
                col_idx += ncol + 1

            row_idx += 1
            col_idx = col_offset

        return widget_list

    @classmethod
    def get_input_values(cls, widget_list):
        table = {}
        for widget in widget_list:
            obj_name = widget.objectName()
            dtype, name = obj_name.split('_', 1)
            if dtype == 'int':
                table[name] = widget.value()
            elif dtype == 'str' or dtype == 'bin':
                table[name] = widget.text()
            elif dtype == 'float':
                table[name] = float(widget.text())
            elif dtype == 'bool':
                table[name] = (widget.checkState() == QtCore.Qt.Checked)
            elif dtype == 'choice':
                table[name] = widget.currentText()
            else:
                raise ValueError('Unknown control widget: %s' % widget)

        return table


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
    def __init__(self, ctrl: Controller, conf_path: str, logger: LogWidget, vfunc_list, func_list,
                 font_size=11, parent=None):
        super(FuncFrame, self).__init__(parent=parent)

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

        lay = QtWidgets.QVBoxLayout(self)

        for slot, flist in zip([self.run_vfunc, self.run_func],
                               [vfunc_list, func_list]):
            mapper = QtCore.QSignalMapper(self)
            for idx, fobj in enumerate(flist):
                fun_name = fobj[0]
                button = QtWidgets.QPushButton(fun_name, parent=self)
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
    conf_path : str
        Default path to save/load configuration files.
        If empty, defaults to current working directory
    font_size : int
        the font size for this frame.
    parent : Optional[QtCore.QObject]
        the parent object
    """

    scanChainChanged = QtCore.pyqtSignal(str)

    def __init__(self, ctrl: Controller, specs: Dict[str, Any], conf_path: str='',
                 font_size: int=11, parent: Optional[QtCore.QObject]=None):
        super(ScanDisplayFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)

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
        self.disp_list, self.comp_list, self.chain_names = self.create_displays(self.ctrl.fpga, specs, font_size)

    def create_displays(self, fpga, specs, font_size):
        disp_font = QtGui.QFont('Monospace')
        disp_font.setStyleHint(QtGui.QFont.TypeWriter)
        disp_font.setPointSize(font_size)

        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        disp_list = []
        comp_list = []
        row_idx, col_idx = 0, 0
        update_chains = set()
        for disp_col in specs:
            for disp_info in disp_col:
                chain_name = disp_info['chain']
                bus_name = disp_info['bus']
                disp_type = disp_info['dtype']
                start = disp_info.get('start', 0)
                step = disp_info.get('step', 1)
                compare = disp_info.get('compare', False)
                ber = disp_info.get('ber', None)

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
                disp_field.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                disp_field.setFont(disp_font)

                if compare:
                    comp_button = QtWidgets.QPushButton('compare %s' % label_name, parent=self)
                    comp_button.setObjectName(str(len(comp_list)))
                    # noinspection PyUnresolvedReferences
                    comp_button.clicked.connect(self._update_compare)
                    comp_field = QtWidgets.QLineEdit(disp_str, parent=self)
                    comp_field.setFont(disp_font)
                    self.lay.addWidget(comp_button, row_idx, col_idx)
                    self.lay.addWidget(comp_field, row_idx, col_idx + 1)
                    row_idx += 1
                    comp_list.append((disp_field, comp_field))

                self.lay.addWidget(label, row_idx, col_idx)
                self.lay.addWidget(disp_field, row_idx, col_idx + 1)
                disp_list.append((disp_field, chain_name, bus_name, disp_type, num_bits, (start, step)))
                row_idx += 1
                if ber:
                    data_rate = ber['data_rate']
                    confidence = ber['confidence']
                    err_max = ber['err_max']
                    targ_ber = ber['targ_ber']
                    ber_display = BERDisplay(data_rate, confidence, err_max, targ_ber, parent=self)
                    ber_display.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                    ber_display.setFont(disp_font)
                    disp_list.append((ber_display, chain_name, bus_name, disp_type, num_bits, (start, step)))
                    clear_button = QtWidgets.QPushButton('reset %s' % label_name, parent=self)
                    # noinspection PyUnresolvedReferences
                    clear_button.clicked.connect(ber_display.reset_error_count)

                    self.lay.addWidget(clear_button, row_idx, col_idx)
                    self.lay.addWidget(ber_display, row_idx, col_idx + 1)
                    row_idx += 1

            row_idx = 0
            col_idx += 2

        return disp_list, comp_list, update_chains

    @QtCore.pyqtSlot()
    def _update_compare(self):
        idx = int(self.sender().objectName())
        disp_field, comp_field = self.comp_list[idx]
        shift_text = comp_field.text()
        disp_text = disp_field.text()

        nbits = len(disp_text)
        if nbits == len(shift_text):
            num_err = nbits
            check_str = shift_text * 2
            shift = 0
            for idx in range(nbits):
                num_err_cur = 0
                for pos in range(nbits):
                    if disp_text[pos] != check_str[idx + pos]:
                        num_err_cur += 1
                if num_err_cur < num_err:
                    num_err = num_err_cur
                    shift = idx

            comp_field.setText(check_str[shift:shift + nbits])

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
    conf_path : str
        Default path to save/load configuration files.
        If empty, defaults to current working directory
    font_size : int
        the font size for this frame.
    parent : Optional[QtCore.QObject]
        the parent object
    """

    scanChainChanged = QtCore.pyqtSignal(str)

    def __init__(self, ctrl: Controller, specs: Dict[str, Any], conf_path: str='',
                 font_size: int=11, parent: Optional[QtCore.QObject]=None):
        super(ScanControlFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)

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
        tmp = self.create_controls(self.ctrl.fpga, specs)
        self.spin_box_list, self.check_box_list, self.line_edit_list, self.val_lookup = tmp

    def create_controls(self, fpga, specs):
        char_dir = specs['char_dir']
        spin_boxes = specs['spin_box']
        check_boxes = specs['check_box']

        # add spin boxes
        align_value = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        spin_box_list = []
        line_edit_list = []
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
                dtype = spin_info.get('dtype', 'int')

                scan_val = fpga.get_scan(chain_name, bus_name)
                num_bits = fpga.get_scan_length(chain_name, bus_name)

                obj_name = '%s.%s' % (chain_name, bus_name)

                # create and add label
                name_label = QtWidgets.QLabel(label_name, parent=self)
                self.lay.addWidget(name_label, row_idx, col_idx, 1, 2)
                row_idx += 1

                # create and add spin box
                if dtype == 'int':
                    # integer control: use spin box.
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
                    spin_box_list.append(spin_box)
                elif dtype == 'bin':
                    line_edit = LineEditBinary(0, num_bits, parent=self)
                    line_edit.setObjectName(obj_name)
                    self.lay.addWidget(line_edit, row_idx, col_idx, 1, 2)
                    # noinspection PyUnresolvedReferences
                    line_edit.editingFinished.connect(self._update_scan_le)
                    line_edit_list.append(line_edit)
                else:
                    raise ValueError('Unknown display type: %s' % dtype)

                row_idx += 1

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

        return spin_box_list, check_box_list, line_edit_list, val_label_lookup

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
        # update line edits
        for line_edit in self.line_edit_list:
            obj_name = line_edit.objectName()
            cur_chain_name, bus_name = obj_name.split('.', 1)
            cur_text = line_edit.text()
            if cur_chain_name == chain_name:
                new_value = fpga.get_scan(chain_name, bus_name)
                new_text = np.binary_repr(new_value, fpga.get_scan_length(chain_name, bus_name))
                if cur_text != new_text:
                    line_edit.setText(new_text)
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

    @QtCore.pyqtSlot()
    def _update_scan_le(self):
        send_obj = self.sender()
        val = int(send_obj.text(), 2)
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


class DispCtrlFrame(FrameBase):
    """A Frame that contains both a display frame and a control frame.

    Parameters
    ----------
    ctrl : Controller
        the controller object
    specs_fname : str
        the specification file name.
    logger : LogWidget
        the LogWidget used to display messages.
    conf_path : str
        Default path to save/load configuration files.
        If empty, defaults to current working directory
    font_size : int
        the font size for this frame.
    parent : Optional[QtCore.QObject]
        the parent object
    """

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget,
                 conf_path: str='', font_size: int=11, parent: Optional[QtCore.QObject]=None):
        super(DispCtrlFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)
        self.logger = logger

        with open(specs_fname, 'r') as f:
            config = yaml.load(f)

        # create display frame
        self.disp_frame = ScanDisplayFrame(self.ctrl, config['displays'], font_size=font_size, parent=self)
        # create control frame
        ctrl_frame = ScanControlFrame(self.ctrl, config['controls'], font_size=font_size, parent=self)

        # create panel control frame
        tmp = self.create_panel_controls(ctrl_frame, config['supplies'])
        pc_frame = tmp[0]
        self.step_box = tmp[1]
        self.update_box = tmp[2]
        self.check_box = tmp[3]
        self.update_button = tmp[4]
        self.sup_field = tmp[5]
        self.activity_movie = tmp[6]
        self.refresh_timer = tmp[7]

        # populate frame
        self.lay.setSpacing(0)
        self.lay.addWidget(self.disp_frame, 0, 0)
        self.lay.addWidget(ctrl_frame, 1, 0)
        self.lay.addWidget(pc_frame, 2, 0)

    def create_panel_controls(self, ctrl_frame, supply_list):
        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        align_box = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        step_box = QtWidgets.QSpinBox(parent=self)
        step_box.setSingleStep(1)
        step_box.setMinimum(1)
        step_box.setMaximum(128)
        step_box.setValue(1)
        # noinspection PyUnresolvedReferences
        step_box.valueChanged[int].connect(ctrl_frame.update_step_size)
        step_label = QtWidgets.QLabel('Step Size:', parent=self)
        step_label.setAlignment(align_label)

        # refresh timer object
        refresh_timer = QtCore.QTimer(parent=self)
        refresh_timer.setInterval(200)
        # noinspection PyUnresolvedReferences
        refresh_timer.timeout.connect(self._refresh_display)

        # refresh interval spin box
        update_box = QtWidgets.QSpinBox(parent=self)
        update_box.setSingleStep(1)
        update_box.setMinimum(0)
        update_box.setMaximum(5000)
        update_box.setValue(refresh_timer.interval())
        # noinspection PyUnresolvedReferences
        update_box.valueChanged[int].connect(self._update_refresh_rate)

        check_box = QtWidgets.QCheckBox('Real-time refresh (ms):', parent=self)
        check_box.setCheckState(QtCore.Qt.Unchecked)
        # noinspection PyUnresolvedReferences
        check_box.stateChanged[int].connect(self._update_refresh)

        update_button = QtWidgets.QPushButton('Update', parent=self)
        update_button.setEnabled(True)
        # noinspection PyUnresolvedReferences
        update_button.clicked.connect(self._refresh_display)

        activity_movie = QtGui.QMovie(activity_gif, parent=self)
        activity_movie.jumpToNextFrame()
        activity_label = QtWidgets.QLabel(parent=self)
        activity_label.setMovie(activity_movie)

        sup_field = QtWidgets.QComboBox(parent=self)
        for sup_name in supply_list:
            sup_field.addItem(sup_name)
        sup_field.setCurrentIndex(0)

        sup_label = QtWidgets.QLabel('Supply:', parent=self)
        sup_label.setAlignment(align_label)

        imeas_button = QtWidgets.QPushButton('Measure Current', parent=self)
        # noinspection PyUnresolvedReferences
        imeas_button.clicked.connect(self._measure_current)

        save_button = QtWidgets.QPushButton('Save As...', parent=self)
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self._save_as)

        load_button = QtWidgets.QPushButton('Load From...', parent=self)
        # noinspection PyUnresolvedReferences
        load_button.clicked.connect(self._load_from)

        frame, lay = self.create_sub_frame()
        lay.addWidget(step_label, 0, 0, alignment=align_label)
        lay.addWidget(step_box, 0, 1, alignment=align_box)
        lay.addWidget(check_box, 0, 2, alignment=align_label)
        lay.addWidget(update_box, 0, 3, alignment=align_box)
        lay.addWidget(update_button, 0, 4)
        lay.addWidget(activity_label, 0, 5)
        lay.addWidget(sup_label, 1, 0, alignment=align_label)
        lay.addWidget(sup_field, 1, 1, alignment=align_box)
        lay.addWidget(imeas_button, 1, 2)
        lay.addWidget(save_button, 1, 3)
        lay.addWidget(load_button, 1, 4)

        return frame, step_box, update_box, check_box, update_button, sup_field, activity_movie, refresh_timer

    @QtCore.pyqtSlot()
    def _refresh_display(self):
        fpga = self.ctrl.fpga
        for chain_name in self.disp_frame.chain_names:
            fpga.update_scan(chain_name)

        self.activity_movie.jumpToNextFrame()

    @QtCore.pyqtSlot(int)
    def _update_refresh_rate(self, val):
        self.refresh_timer.setInterval(val)

    @QtCore.pyqtSlot(int)
    def _update_refresh(self, val):
        if val == QtCore.Qt.Checked:
            self.update_button.setEnabled(False)
            self.refresh_timer.start()
        else:
            self.update_button.setEnabled(True)
            self.refresh_timer.stop()

    @QtCore.pyqtSlot()
    def _measure_current(self):
        sup_name = self.sup_field.currentText()
        try:
            current = self.ctrl.fpga.read_current(sup_name)
            self.logger.println('%s current: %.6g mA' % (sup_name, current * 1e3))
        except KeyError as ex:
            self.logger.println(str(ex))

    @QtCore.pyqtSlot()
    def _save_as(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.conf_path,
                                                         'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            if not fname.endswith('.yaml') and not fname.endswith('.yml'):
                fname += '.yaml'
            self.logger.println('Saving to file: %s' % fname)
            attrs = dict(step_size=self.step_box.value(),
                         refresh_rate=self.update_box.value(),
                         supply_idx=self.sup_field.currentIndex(),
                         )
            self.ctrl.fpga.save_scan_to_file(fname, rx_gui=attrs)

    @QtCore.pyqtSlot()
    def _load_from(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load File', self.conf_path,
                                                         'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Loading from file: %s' % fname)
            with open(fname, 'r') as f:
                config = yaml.load(f)['rx_gui']

            self.step_box.setValue(config['step_size'])
            self.update_box.setValue(config['refresh_rate'])
            self.sup_field.setCurrentIndex(config['supply_idx'])
            self.check_box.setCheckState(QtCore.Qt.Unchecked)
            self.ctrl.fpga.set_scan_from_file(fname)


class CtrlFrame(FrameBase):
    """A frame that contains only scan controls.

    Parameters
    ----------
    ctrl : Controller
        the controller object
    specs_fname : str
        the specification file name.
    logger : LogWidget
        the LogWidget used to display messages.
    conf_path : str
        Default path to save/load configuration files.
        If empty, defaults to current working directory
    font_size : int
        the font size for this frame.
    parent : Optional[QtCore.QObject]
        the parent object
    """

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget,
                 conf_path: str='', font_size: int=11, parent: Optional[QtCore.QObject]=None):
        super(CtrlFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)
        self.logger = logger

        with open(specs_fname, 'r') as f:
            config = yaml.load(f)

        # create control frame
        ctrl_frame = ScanControlFrame(self.ctrl, config['controls'], font_size=font_size, parent=self)

        # create panel control frame
        tmp = self.create_panel_controls(ctrl_frame, config['supplies'])
        pc_frame = tmp[0]
        self.step_box = tmp[1]
        self.sup_field = tmp[2]

        # populate frame
        self.lay.setSpacing(0)
        self.lay.addWidget(ctrl_frame, 0, 0)
        self.lay.addWidget(pc_frame, 1, 0)

    def create_panel_controls(self, ctrl_frame, supply_list):
        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        align_box = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        step_box = QtWidgets.QSpinBox(parent=self)
        step_box.setSingleStep(1)
        step_box.setMinimum(1)
        step_box.setMaximum(128)
        step_box.setValue(1)
        # noinspection PyUnresolvedReferences
        step_box.valueChanged[int].connect(ctrl_frame.update_step_size)
        step_label = QtWidgets.QLabel('Step Size:', parent=self)
        step_label.setAlignment(align_label)

        sup_field = QtWidgets.QComboBox(parent=self)
        for sup_name in supply_list:
            sup_field.addItem(sup_name)
        sup_field.setCurrentIndex(0)

        sup_label = QtWidgets.QLabel('Supply:', parent=self)
        sup_label.setAlignment(align_label)

        imeas_button = QtWidgets.QPushButton('Measure Current', parent=self)
        # noinspection PyUnresolvedReferences
        imeas_button.clicked.connect(self._measure_current)

        save_button = QtWidgets.QPushButton('Save As...', parent=self)
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self._save_as)

        load_button = QtWidgets.QPushButton('Load From...', parent=self)
        # noinspection PyUnresolvedReferences
        load_button.clicked.connect(self._load_from)

        frame, lay = self.create_sub_frame()
        lay.addWidget(step_label, 0, 0, alignment=align_label)
        lay.addWidget(step_box, 0, 1, alignment=align_box)
        lay.addWidget(sup_label, 0, 2, alignment=align_label)
        lay.addWidget(sup_field, 0, 3, alignment=align_box)
        lay.addWidget(imeas_button, 0, 4)
        lay.addWidget(save_button, 0, 5)
        lay.addWidget(load_button, 0, 6)

        return frame, step_box, sup_field

    @QtCore.pyqtSlot()
    def _measure_current(self):
        sup_name = self.sup_field.currentText()
        try:
            current = self.ctrl.fpga.read_current(sup_name)
            self.logger.println('%s current: %.6g mA' % (sup_name, current * 1e3))
        except KeyError as ex:
            self.logger.println(str(ex))

    @QtCore.pyqtSlot()
    def _save_as(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.conf_path,
                                                         'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            if not fname.endswith('.yaml') and not fname.endswith('.yml'):
                fname += '.yaml'
            self.logger.println('Saving to file: %s' % fname)
            attrs = dict(step_size=self.step_box.value(),
                         supply_idx=self.sup_field.currentIndex(),
                         )
            self.ctrl.fpga.save_scan_to_file(fname, rx_gui=attrs)

    @QtCore.pyqtSlot()
    def _load_from(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load File', self.conf_path,
                                                         'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Loading from file: %s' % fname)
            with open(fname, 'r') as f:
                config = yaml.load(f)['rx_gui']

            self.step_box.setValue(config['step_size'])
            self.sup_field.setCurrentIndex(config['supply_idx'])
            self.ctrl.fpga.set_scan_from_file(fname)
