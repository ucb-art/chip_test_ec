# -*- coding: utf-8 -*-


"""This package contains GUI components for SERDES receiver testing.
"""

import os
import pkg_resources

import yaml

from PyQt5 import QtWidgets, QtCore, QtGui

from ...backend.core import Controller
from ..base.displays import LogWidget
from ..base.frames import FrameBase, ScanDisplayFrame, ScanControlFrame

activity_gif = pkg_resources.resource_filename('chip_test_ec.gui', os.path.join('resources', 'ajax-loader.gif'))


class RXControlFrame(FrameBase):
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

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget, font_size: int=11, parent=None):
        super(RXControlFrame, self).__init__(ctrl, font_size=font_size, parent=parent)
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
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', cur_dir, 'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Saving to file: %s' % fname)
            attrs = dict(step_size=self.step_box.value(),
                         refresh_rate=self.update_box.value(),
                         supply_idx=self.sup_field.currentIndex(),
                         )
            self.ctrl.fpga.save_scan_to_file(fname, rx_gui=attrs)

    @QtCore.pyqtSlot()
    def _load_from(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load File', cur_dir, 'YAML files (*.yaml *.yml)',
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
