# -*- coding: utf-8 -*-

from typing import Optional

import yaml
import numpy as np

from PyQt5 import QtCore, QtWidgets
import pyqtgraph

# type check imports
from ..base.frames import FrameBase
from ..base.displays import LogWidget
from ...backend.core import Controller
from ...util.core import import_class


class EyePlotFrame(FrameBase):
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

    color_unfilled = (240, 255, 240)
    color_error = (0, 0, 0)
    color_cursor = (175, 238, 238)

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget,
                 conf_path: str='', font_size: int=11, parent: Optional[QtCore.QObject]=None):
        super(EyePlotFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)
        self.logger = logger
        self.color_arr = None
        self.err_arr = None
        self.worker = None

        with open(specs_fname, 'r') as f:
            self.config = yaml.load(f)

        self.img_item, plot_widget = self.create_eye_plot(self.config)

        # create panel control frame
        pc_frame, self.var_boxes, self.run, self.cancel, self.save = self.create_panel_controls(self.config)

        # populate frame
        self.lay.setSpacing(0)
        self.lay.addWidget(plot_widget, 0, 0)
        self.lay.addWidget(pc_frame, 1, 0)

    def create_eye_plot(self, config):
        tstart, tstop, tstep = config['time_sweep']
        ystart, ystop, ystep = config['y_sweep']
        yname = config['y_name']
        tick_step = config['tick_step']

        img_item = pyqtgraph.ImageItem()
        img_item.setOpts(axisOrder='row-major')
        tvec, yvec = self._init_data(img_item, tstart, tstop, tstep, ystart, ystop, ystep)

        # create plot
        plot_widget = pyqtgraph.PlotWidget()
        plt_item = plot_widget.getPlotItem()
        plt_item.addItem(img_item)
        plt_item.showGrid(x=True, y=True, alpha=1)
        plt_item.setLabel('left', yname)
        plt_item.setLabel('bottom', 'time')
        plt_item.setMouseEnabled(x=False, y=False)

        # set tick values
        xtick_minor = [(val, str(val)) for val in tvec[0::tick_step]]
        ytick_minor = [(val, str(val)) for val in yvec[0::tick_step]]
        plt_item.getAxis('bottom').setTicks([[], xtick_minor])
        plt_item.getAxis('left').setTicks([[], ytick_minor])

        return img_item, plot_widget

    def create_panel_controls(self, config):
        align_label = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        align_box = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        # add sweep range spin boxes
        frame, lay = self.create_sub_frame()
        row_idx, col_idx = 0, 0
        var_boxes = {}
        for var_name in ('time', 'y'):
            vmin, vmax = config[var_name + '_range']
            vstart, vstop, vstep = config[var_name + '_sweep']
            box_list = []
            for val, name in ((vstart, 'start'), (vstop, 'stop'), (vstep, 'step')):
                cur_label = QtWidgets.QLabel('%s %s:' % (var_name, name), parent=self)
                cur_label.setAlignment(align_label)
                cur_box = QtWidgets.QSpinBox(parent=self)
                cur_box.setSingleStep(1)
                cur_box.setMinimum(vmin)
                cur_box.setMaximum(vmax)
                cur_box.setValue(val)

                box_list.append(cur_box)
                lay.addWidget(cur_label, row_idx, col_idx, alignment=align_label)
                lay.addWidget(cur_box, row_idx, col_idx + 1, alignment=align_box)
                col_idx += 2

            var_boxes[var_name] = box_list
            col_idx = 0
            row_idx += 1

        # add Run/Cancel buttons
        run_button = QtWidgets.QPushButton('Run', parent=self)
        run_button.setEnabled(True)
        # noinspection PyUnresolvedReferences
        run_button.clicked.connect(self._start_measurement)
        lay.addWidget(run_button, row_idx, 0, 1, 2)
        cancel_button = QtWidgets.QPushButton('Cancel', parent=self)
        cancel_button.setEnabled(False)
        # noinspection PyUnresolvedReferences
        cancel_button.clicked.connect(self._stop_measurement)
        lay.addWidget(cancel_button, row_idx, 2, 1, 2)
        save_button = QtWidgets.QPushButton('Save', parent=self)
        save_button.setEnabled(True)
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self._save_as)
        lay.addWidget(save_button, row_idx, 4, 1, 2)
        return frame, var_boxes, run_button, cancel_button, save_button

    def _init_data(self, img_item, tstart, tstop, tstep, ystart, ystop, ystep):
        tvec = np.arange(tstart, tstop, tstep)
        yvec = np.arange(ystart, ystop, ystep)
        num_t = len(tvec)
        num_y = len(yvec)
        mat_shape = (num_t, num_y)
        if self.data_arr is None or self.data_arr.shape != mat_shape:
            self.data_arr = np.empty((num_t, num_y, 3), dtype=int)
            self.err_arr = np.empty(mat_shape)

        self.data_arr[:] = self.color_unfilled
        self.err_arr.fill(-1)
        t0, tstep, y0, ystep = tvec[0], tvec[1] - tvec[0], yvec[0], yvec[1] - yvec[0]

        # create image
        img_item.setImage(self.data_arr, levels=(0, 255))
        img_item.setRect(QtCore.QRectF(t0 - tstep / 2, y0 - ystep / 2, tstep * num_t, ystep * num_y))

        return tvec, yvec

    @QtCore.pyqtSlot()
    def _start_measurement(self):
        if self.worker is None:

            tstart, tstop, tstep = self.var_boxes['time']
            ystart, ystop, ystep = self.var_boxes['y']

            tstart = tstart.value()
            tstop = tstop.value()
            tstep = tstep.value()
            ystart = ystart.value()
            ystop = ystop.value()
            ystep = ystep.value()

            tvec, yvec = self._init_data(self.img_item, tstart, tstop, tstep, ystart, ystop, ystep)

            """
            mod_name = self.config['module']
            cls_name = gui_config['class']
            specs_fname = gui_config['specs_fname']
            gui_cls = import_class(mod_name, cls_name)
            gui_frame = gui_cls(ctrl, specs_fname, self.logger, conf_path=conf_p
            """
            self.run.setEnabled(False)
            self.cancel.setEnabled(True)
            self.save.setEnabled(False)

    @QtCore.pyqtSlot()
    def _stop_measurement(self):
        pass

        self.run.setEnabled(True)
        self.cancel.setEnabled(False)
        self.save.setEnabled(True)

    @QtCore.pyqtSlot()
    def _save_as(self):
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.conf_path,
                                                         'Numpy data files (*.npy)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            if not fname.endswith('.npy'):
                fname += '.npy'
            self.logger.println('Saving to file: %s' % fname)
            np.save(fname, self.err_arr)
