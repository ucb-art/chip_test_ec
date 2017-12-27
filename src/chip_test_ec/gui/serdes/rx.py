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

        # create panel controls
        self.refresh_rate = 200
        pc_frame, self.update_button = self.create_panel_controls(self.refresh_rate)

        # populate frame
        self.lay = QtWidgets.QVBoxLayout()
        self.lay.setSpacing(0)
        self.lay.setContentsMargins(0, 0, 0, 0)
        # add displays
        disp_frame, disp_lay = self.create_sub_frame()
        row_idx, col_idx = 0, 0
        for label, disp_field in self.disp_widgets:
            disp_lay.addWidget(label, row_idx, col_idx)
            disp_lay.addWidget(disp_field, row_idx, col_idx + 1)
            row_idx += 1
            if row_idx == num_rows_disp:
                row_idx = 0
                col_idx += 2
        self.lay.addWidget(disp_frame)

        # add controls
        ctrl_frame, ctrl_lay = self.create_sub_frame()
        row_idx, col_idx = 0, 0
        for widgets_col in ctrl_widgets:
            for widgets in widgets_col:
                if len(widgets) == 1:
                    # single checkbox
                    ctrl_lay.addWidget(widgets[0], row_idx, col_idx, 1, 2)
                    row_idx += 1
                elif len(widgets) == 2:
                    # label and spinbox
                    ctrl_lay.addWidget(widgets[0], row_idx, col_idx, 1, 2)
                    ctrl_lay.addWidget(widgets[1], row_idx + 1, col_idx)
                    row_idx += 2
                else:
                    # label, spinbox, and value label
                    ctrl_lay.addWidget(widgets[0], row_idx, col_idx, 1, 2)
                    ctrl_lay.addWidget(widgets[1], row_idx + 1, col_idx)
                    ctrl_lay.addWidget(widgets[2], row_idx + 1, col_idx + 1)
                    row_idx += 2
            row_idx = 0
            col_idx += 2
        self.lay.addWidget(ctrl_frame)

        # add configuration panel
        self.lay.addWidget(pc_frame)

        self.setLayout(self.lay)

    def create_sub_frame(self):
        frame = QtWidgets.QFrame(parent=self)
        frame.setContentsMargins(0, 0, 0, 0)
        frame.setLineWidth(1)
        frame.setMidLineWidth(1)
        frame.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
        lay = QtWidgets.QGridLayout()
        frame.setLayout(lay)
        return frame, lay

    def create_panel_controls(self, refresh_rate):
        frame, lay = self.create_sub_frame()
        step_box = QtWidgets.QSpinBox(parent=self)
        step_box.setSingleStep(1)
        step_box.setMinimum(1)
        step_box.setMaximum(128)
        step_box.setValue(1)
        # noinspection PyUnresolvedReferences
        step_box.valueChanged[int].connect(self.update_step_size)
        step_label = QtWidgets.QLabel('Step size:', parent=self)
        step_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        update_box = QtWidgets.QSpinBox(parent=self)
        update_box.setSingleStep(1)
        update_box.setMinimum(0)
        update_box.setMaximum(5000)
        update_box.setValue(refresh_rate)
        # noinspection PyUnresolvedReferences
        update_box.valueChanged[int].connect(self.update_refresh_rate)
        update_label = QtWidgets.QLabel('Refresh rate (ms):', parent=self)
        update_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        check_box = QtWidgets.QCheckBox('Real-time refresh', parent=self)
        check_box.setCheckState(QtCore.Qt.Unchecked)
        # noinspection PyUnresolvedReferences
        check_box.stateChanged[int].connect(self.update_refresh)

        update_button = QtWidgets.QPushButton('Update', parent=self)
        update_button.setEnabled(True)
        # noinspection PyUnresolvedReferences
        update_button.clicked.connect(self.update_display)

        lay.addWidget(step_label, 0, 0)
        lay.addWidget(step_box, 0, 1)
        lay.addWidget(update_label, 0, 2)
        lay.addWidget(update_box, 0, 3)
        lay.addWidget(check_box, 0, 4)
        lay.addWidget(update_button, 0, 5)

        return frame, update_button

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
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
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
                    label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
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
                    check_state = QtCore.Qt.Checked if scan_val else QtCore.Qt.Unchecked
                    check_box.setCheckState(check_state)
                    # noinspection PyUnresolvedReferences
                    check_box.stateChanged[int].connect(self.update_scan)
                    widgets_col.append((check_box, ))
                else:
                    name_label = QtWidgets.QLabel(bus_name, parent=self)
                    spin_box = QtWidgets.QSpinBox(parent=self)
                    spin_box.setObjectName(obj_name)
                    spin_box.setSingleStep(1)
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
                        max_val = int(round(np.max(xvec)))
                        spin_box.setMaximum(int(round(np.max(xvec))))
                        spin_box.setMinimum(offset)
                        if scan_val < offset or scan_val > max_val:
                            raise ValueError('Default scan values outside characterization bounds')
                        spin_box.setValue(scan_val)

                        val_text = '%.4e' % (yvec_mono[scan_val - offset])
                        val_label = QtWidgets.QLabel(val_text, parent=self)
                        val_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                        val_label_lookup[obj_name] = (val_label, offset, yvec_mono)
                        # noinspection PyUnresolvedReferences
                        spin_box.valueChanged[int].connect(self.update_label)
                        widgets_col.append((name_label, spin_box, val_label))
                    else:
                        spin_box.setMaximum((1 << num_bits) - 1)
                        spin_box.setMinimum(0)
                        spin_box.setValue(scan_val)
                        widgets_col.append((name_label, spin_box))

                    # noinspection PyUnresolvedReferences
                    spin_box.valueChanged[int].connect(self.update_scan)

            widgets.append(widgets_col)

        return widgets, spin_box_list, val_label_lookup

    @QtCore.pyqtSlot('int')
    def update_scan(self, val):
        send_obj = self.sender()
        if isinstance(send_obj, QtWidgets.QCheckBox):
            val = 1 if val == QtCore.Qt.Checked else 0
        obj_name = send_obj.objectName()
        chain_name, bus_name = obj_name.split('.', 1)
        self.ctrl.fpga.set_scan(chain_name, bus_name, val)
        self.ctrl.fpga.update_scan(chain_name)

    @QtCore.pyqtSlot('int')
    def update_label(self, val):
        obj_name = self.sender().objectName()
        val_label, offset, yvec = self.val_lookup[obj_name]
        val_label.setText('%.4e' % yvec[val - offset])

    @QtCore.pyqtSlot('int')
    def update_step_size(self, val):
        for spin_box in self.spin_box_list:
            spin_box.setSingleStep(val)

    @QtCore.pyqtSlot('int')
    def update_refresh(self, val):
        if val == QtCore.Qt.Checked:
            self.update_button.setEnabled(False)
            self.update_button.setText('|')
        else:
            self.update_button.setEnabled(True)
            self.update_button.setText('Update')

    @QtCore.pyqtSlot('int')
    def update_refresh_rate(self, val):
        self.refresh_rate = val

    @QtCore.pyqtSlot()
    def update_display(self):
        pass
