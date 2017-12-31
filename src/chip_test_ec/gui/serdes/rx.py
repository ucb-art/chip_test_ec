# -*- coding: utf-8 -*-


"""This package contains GUI components for SERDES receiver testing.
"""

import os
import pkg_resources

import yaml
import numpy as np
from sklearn.isotonic import IsotonicRegression

from PyQt5 import QtWidgets, QtCore, QtGui

from ...backend.core import Controller
from ..base.displays import LogWidget

activity_gif = pkg_resources.resource_filename('chip_test_ec.gui', os.path.join('resources', 'ajax-loader.gif'))


class RXControlFrame(QtWidgets.QFrame):
    """A Frame that displays all RX controls and real time update of RX output.

    Parameters
    ----------
    ctrl : Controller
        the controller object
    specs_fname : str
        the specification file name.
    logger : LogWidget
        the LogWidget used to display messages.
    font_size : int
        the font size for this frame.]
    """
    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget, font_size: int=11):
        super(RXControlFrame, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ctrl = ctrl
        self.logger = logger

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
        tmp = self.create_panel_controls()
        pc_frame, self.update_button, self.activity_movie, self.refresh_timer, self.sup_field = tmp

        # populate frame
        self.lay = QtWidgets.QVBoxLayout()
        self.lay.setSpacing(0)
        self.lay.setContentsMargins(0, 0, 0, 0)
        # add displays
        disp_frame, disp_lay = self.create_sub_frame()
        row_idx, col_idx = 0, 0
        for label, disp_field, _, _, _, _, _ in self.disp_widgets:
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

    def create_panel_controls(self):
        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

        frame, lay = self.create_sub_frame()
        step_box = QtWidgets.QSpinBox(parent=self)
        step_box.setSingleStep(1)
        step_box.setMinimum(1)
        step_box.setMaximum(128)
        step_box.setValue(1)
        # noinspection PyUnresolvedReferences
        step_box.valueChanged[int].connect(self.update_step_size)
        step_label = QtWidgets.QLabel('Step size:', parent=self)
        step_label.setAlignment(align_label)

        refresh_timer = QtCore.QTimer(parent=self)
        refresh_timer.setInterval(200)
        # noinspection PyUnresolvedReferences
        refresh_timer.timeout.connect(self.update_display)

        update_box = QtWidgets.QSpinBox(parent=self)
        update_box.setSingleStep(1)
        update_box.setMinimum(0)
        update_box.setMaximum(5000)
        update_box.setValue(refresh_timer.interval())
        # noinspection PyUnresolvedReferences
        update_box.valueChanged[int].connect(self.update_refresh_rate)
        update_label = QtWidgets.QLabel('Refresh rate (ms):', parent=self)
        update_label.setAlignment(align_label)

        check_box = QtWidgets.QCheckBox('Real-time refresh', parent=self)
        check_box.setCheckState(QtCore.Qt.Unchecked)
        # noinspection PyUnresolvedReferences
        check_box.stateChanged[int].connect(self.update_refresh)

        activity_movie = QtGui.QMovie(activity_gif, parent=self)
        activity_movie.jumpToNextFrame()
        update_button = QtWidgets.QPushButton('Update', parent=self)
        update_button.setIcon(QtGui.QIcon(activity_movie.currentPixmap()))
        update_button.setEnabled(True)
        # noinspection PyUnresolvedReferences
        update_button.clicked.connect(self.update_display)

        sup_field = QtWidgets.QLineEdit(parent=self)
        sup_field.setText('SERDES_AVDD')
        sup_label = QtWidgets.QLabel('Supply:', parent=self)
        sup_label.setAlignment(align_label)
        imeas_button = QtWidgets.QPushButton('Measure Current', parent=self)
        # noinspection PyUnresolvedReferences
        imeas_button.clicked.connect(self.measure_current)

        save_button = QtWidgets.QPushButton('Save As...', parent=self)
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self.save_as)
        load_button = QtWidgets.QPushButton('Load From...', parent=self)
        # noinspection PyUnresolvedReferences
        load_button.clicked.connect(self.load_from)

        lay.addWidget(step_label, 0, 0)
        lay.addWidget(step_box, 0, 1)
        lay.addWidget(update_label, 0, 2)
        lay.addWidget(update_box, 0, 3)
        lay.addWidget(check_box, 0, 4)
        lay.addWidget(update_button, 0, 5)
        lay.addWidget(sup_label, 1, 0)
        lay.addWidget(sup_field, 1, 1)
        lay.addWidget(imeas_button, 1, 2, 1, 2)
        lay.addWidget(save_button, 1, 4)
        lay.addWidget(load_button, 1, 5)

        return frame, update_button, activity_movie, refresh_timer, sup_field

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
            widgets.append((label, disp_field, chain_name, bus_name, disp_type, num_bits, (0, 1)))
            if des_num > 1:
                for idx in range(des_num):
                    label = QtWidgets.QLabel(bus_name + ('[%d]' % idx), parent=self)
                    label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    start = des_num - idx - 1
                    disp_field = QtWidgets.QLabel(disp_str[start::des_num],
                                                  parent=self)
                    disp_field.setFont(disp_font)
                    widgets.append((label, disp_field, chain_name, bus_name, disp_type, num_bits, (start, des_num)))

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
                if len(entry) < 3:
                    fname, scale, unit = None, 1.0, ''
                else:
                    fname, scale, unit = entry[2:5]

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
                        spin_box.setMaximum(max_val)
                        spin_box.setMinimum(offset)
                        if scan_val < offset or scan_val > max_val:
                            raise ValueError('Default scan values outside characterization bounds')
                        spin_box.setValue(scan_val)
                        val_text = '%.4g %s' % (yvec_mono[scan_val - offset] * scale, unit)
                        val_label = QtWidgets.QLabel(val_text, parent=self)
                        val_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                        val_label_lookup[obj_name] = (val_label, offset, scale, unit, yvec_mono)
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
        val_label, offset, scale, unit, yvec = self.val_lookup[obj_name]
        val_label.setText('%.4g %s' % (yvec[val - offset] * scale, unit))

    @QtCore.pyqtSlot('int')
    def update_step_size(self, val):
        for spin_box in self.spin_box_list:
            spin_box.setSingleStep(val)

    @QtCore.pyqtSlot('int')
    def update_refresh(self, val):
        if val == QtCore.Qt.Checked:
            self.update_button.setEnabled(False)
            self.refresh_timer.start()
        else:
            self.update_button.setEnabled(True)
            self.update_button.setText('Update')
            self.refresh_timer.stop()

    @QtCore.pyqtSlot('int')
    def update_refresh_rate(self, val):
        self.refresh_timer.setInterval(val)

    @QtCore.pyqtSlot()
    def update_display(self):
        update_chains = set()
        for (_, _, chain_name, _, _, _, _) in self.disp_widgets:
            update_chains.add(chain_name)

        fpga = self.ctrl.fpga
        for chain_name in update_chains:
            fpga.update_scan(chain_name)

        for (_, disp_field, chain_name, bus_name, disp_type, nbits, (start, des_num)) in self.disp_widgets:
            scan_val = fpga.get_scan(chain_name, bus_name)
            if disp_type == 'int':
                disp_str = str(scan_val)
            else:
                disp_str = np.binary_repr(scan_val, nbits)[start::des_num]
            disp_field.setText(disp_str)

        self.activity_movie.jumpToNextFrame()
        self.update_button.setIcon(QtGui.QIcon(self.activity_movie.currentPixmap()))

    @QtCore.pyqtSlot()
    def measure_current(self):
        sup_name = self.sup_field.text()
        try:
            current = self.ctrl.fpga.read_current(sup_name)
            self.logger.println('%s current: %.6g mA' % (sup_name, current * 1e3))
        except KeyError as ex:
            self.logger.println(str(ex))

    @QtCore.pyqtSlot()
    def save_as(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', cur_dir, 'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Saving to file: %s' % fname)

    @QtCore.pyqtSlot()
    def load_from(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load File', cur_dir, 'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Loading from file: %s' % fname)
