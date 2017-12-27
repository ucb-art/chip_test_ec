# -*- coding: utf-8 -*-


"""This package contains GUI components for SERDES receiver testing.
"""

import os

import yaml
import numpy as np
from sklearn.isotonic import IsotonicRegression

from PyQt5 import QtWidgets, QtCore, QtGui


class RXControlFrame(QtWidgets.QFrame):
    """A Frame that displays all RX controls and real time update of RX output.

    Parameters
    ----------
    ctrl : Controller
        the controller object
    specs_fname : str
        the specification file name.
    font_size : int
        the font size for this frame.]
    """
    def __init__(self, ctrl, specs_fname, font_size=11):
        super(RXControlFrame, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ctrl = ctrl

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        with open(specs_fname, 'r') as f:
            config = yaml.load(f)

        char_dir = config['char_dir']
        controls = config['controls']
        displays = config['displays']
        num_rows_disp = config['num_rows_disp']

        self.char_dir = os.path.abspath(char_dir)
        # create controls
        tmp = self.create_controls(self.ctrl.fpga, controls, char_dir)
        ctrl_widgets, self.spin_box_list, self.val_lookup = tmp

        # create displays
        self.disp_widgets = self.create_displays(self.ctrl.fpga, displays, font_size)

        # populate frame
        self.lay = QtWidgets.QGridLayout()
        # add displays
        row_idx, col_idx = 0, 0
        for label, disp_field in self.disp_widgets:
            self.lay.addWidget(label, row_idx, col_idx)
            self.lay.addWidget(disp_field, row_idx, col_idx + 1)
            row_idx += 1
            if row_idx == num_rows_disp:
                row_idx = 0
                col_idx += 2
        # add controls
        row_idx, col_idx = num_rows_disp, 0
        for widgets_col in ctrl_widgets:
            for widgets in widgets_col:
                if len(widgets) == 1:
                    # single checkbox
                    self.lay.addWidget(widgets[0], row_idx, col_idx, 1, 2)
                    row_idx += 1
                elif len(widgets) == 2:
                    # label and spinbox
                    self.lay.addWidget(widgets[0], row_idx, col_idx, 1, 2)
                    self.lay.addWidget(widgets[1], row_idx + 1, col_idx)
                    row_idx += 2
                else:
                    # label, spinbox, and value label
                    self.lay.addWidget(widgets[0], row_idx, col_idx, 1, 2)
                    self.lay.addWidget(widgets[1], row_idx + 1, col_idx)
                    self.lay.addWidget(widgets[2], row_idx + 1, col_idx + 1)
                    row_idx += 2
            row_idx = 0
            col_idx += 2

        self.setLayout(self.lay)

    def create_displays(self, fpga, displays, font_size):
        disp_font = QtGui.QFont('Monospace')
        disp_font.setStyleHint(QtGui.QFont.TypeWriter)
        disp_font.setPointSize(font_size)

        widgets = []
        for entry in displays:
            chain_name, bus_name, disp_type = entry[:3]
            num_bits = fpga.get_scan_length(chain_name, bus_name)
            scan_val = fpga.get_scan(chain_name, bus_name)
            des_num = 1 if len(entry) < 4 else entry[3]
            label = QtWidgets.QLabel(bus_name, parent=self)
            if disp_type == 'int':
                disp_str = str(scan_val)
            else:
                disp_str = np.binary_repr(scan_val, num_bits)
            disp_field = QtWidgets.QLabel(disp_str, parent=self)
            disp_field.setFont(disp_font)
            widgets.append((label, disp_field))
            if des_num > 1:
                for idx in range(des_num):
                    label = QtWidgets.QLabel(bus_name + ('[%d]' % idx), parent=self)
                    disp_field = QtWidgets.QLabel(disp_str[des_num - idx - 1::des_num],
                                                  parent=self)
                    disp_field.setFont(disp_font)
                    widgets.append((label, disp_field))

        return widgets

    def create_controls(self, fpga, controls, char_dir):
        widgets = []
        spin_box_list = []
        val_label_lookup = {}
        for column in controls:
            widgets_col = []
            for entry in column:
                chain_name, bus_name = entry[:2]
                obj_name = '%s.%s' % (chain_name, bus_name)
                scan_val = fpga.get_scan(chain_name, bus_name)
                num_bits = fpga.get_scan_length(chain_name, bus_name)
                fname = None if len(entry) < 3 else entry[2]
                if num_bits == 1:
                    check_box = QtWidgets.QCheckBox(bus_name, parent=self)
                    check_box.setObjectName(obj_name)
                    check_box.setCheckState(scan_val)
                    # noinspection PyUnresolvedReferences
                    check_box.stateChanged[int].connect(self.update_scan)
                    widgets_col.append((check_box, ))
                else:
                    name_label = QtWidgets.QLabel(bus_name, parent=self)
                    spin_box = QtWidgets.QSpinBox(parent=self)
                    spin_box.setObjectName(obj_name)
                    spin_box.setValue(scan_val)
                    spin_box.setSingleStep(1)
                    # noinspection PyUnresolvedReferences
                    spin_box.valueChanged[int].connect(self.update_scan)
                    spin_box_list.append(spin_box)
                    if fname:
                        # load characterization file
                        mat = np.loadtxt(os.path.join(char_dir, fname))
                        # fit with monotonic regression
                        reg = IsotonicRegression(increasing='auto')
                        xvec = mat[:, 0]
                        offset = int(round(np.min(xvec)))
                        yvec_mono = reg.fit_transform(xvec, mat[:, 1])
                        # set max and min based on characterization file
                        spin_box.setMaximum(int(round(np.max(xvec))))
                        spin_box.setMinimum(offset)

                        val_text = '%.6g' % (yvec_mono[scan_val - offset])
                        val_label = QtWidgets.QLabel(val_text, parent=self)
                        val_label_lookup[obj_name] = (val_label, offset, yvec_mono)
                        # noinspection PyUnresolvedReferences
                        spin_box.valueChanged[int].connect(self.update_label)
                        widgets_col.append((name_label, spin_box, val_label))
                    else:
                        spin_box.setMaximum((1 << num_bits) - 1)
                        spin_box.setMinimum(0)
                        widgets_col.append((name_label, spin_box))
            widgets.append(widgets_col)

        return widgets, spin_box_list, val_label_lookup

    @QtCore.pyqtSlot('int')
    def update_scan(self, val):
        obj_name = self.sender().objectName()
        chain_name, bus_name = obj_name.split('.', 1)
        self.ctrl.fpga.set_scan(chain_name, bus_name, val)
        self.ctrl.fpga.update_scan(chain_name)

    @QtCore.pyqtSlot('int')
    def update_label(self, val):
        obj_name = self.sender().objectName()
        val_label, offset, yvec = self.val_lookup[obj_name]
        val_label.setText('%.6g' % yvec[val - offset])
