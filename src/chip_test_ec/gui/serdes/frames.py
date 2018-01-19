# -*- coding: utf-8 -*-

from typing import Optional

import yaml
import numpy as np

from PyQt5 import QtCore, QtWidgets
import pyqtgraph

# type check imports
from ..base.frames import FrameBase
from ..base.displays import LogWidget
from ..base.threads import WorkerThread
from ...backend.core import Controller


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
    color_cursor = (175, 238, 238)

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget,
                 conf_path: str = '', font_size: int = 11, parent: Optional[QtCore.QObject] = None):
        super(EyePlotFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)
        self.logger = logger
        self.color_arr = None
        self.err_arr = None
        self.worker = None
        self.max_err = None

        with open(specs_fname, 'r') as f:
            self.config = yaml.load(f)

        self.img_item, plot_widget = self.create_eye_plot(self.config)

        # create panel control frame
        pc_frame, self.widgets, self.run, self.cancel, self.save = self.create_panel_controls(self.config)

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
        # add sweep range spin boxes
        t_min, t_max = config['t_range']
        y_min, y_max = config['y_range']
        t_start, t_stop, t_step = config['t_sweep']
        y_start, y_stop, y_step = config['y_sweep']
        max_err = config['max_err']
        ber = config['ber']

        ctrl_info = [[dict(name='t_start', dtype='int', vmin=t_min, vmax=t_max, vdef=t_start),
                      dict(name='t_stop', dtype='int', vmin=t_min, vmax=t_max, vdef=t_stop),
                      dict(name='t_step', dtype='int', vmin=t_min, vmax=t_max, vdef=t_step),
                      ],
                     [dict(name='y_start', dtype='int', vmin=y_min, vmax=y_max, vdef=y_start),
                      dict(name='y_stop', dtype='int', vmin=y_min, vmax=y_max, vdef=y_stop),
                      dict(name='y_step', dtype='int', vmin=y_min, vmax=y_max, vdef=y_step),
                      ],
                     [dict(name='y_guess', dtype='int', vmin=y_min, vmax=y_max),
                      dict(name='max_err', dtype='int', vmin=0, vmax=(1 << 31) - 1, vdef=max_err),
                      dict(name='ber', dtype='float', vmin=0, vmax=1, decimals=4, vdef=ber),
                      ],
                     ]

        # create input controls
        frame, lay = self.create_sub_frame()
        widget_list = self.create_input_controls(ctrl_info, lay)
        row_idx, col_idx = 3, 0

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
        return frame, widget_list, run_button, cancel_button, save_button

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

            mod_name = self.config['eye_module']
            cls_name = self.config['eye_class']
            input_vals = self.get_input_values(self.widgets)
            self.max_err = input_vals['max_err']
            eye_config = {
                'module': mod_name,
                'class': cls_name,
                'params': input_vals,
            }

            self.worker = WorkerThread(self.ctrl, eye_config)
            self.worker.update.connect(self._update_plot)
            self.worker.start()

        self.run.setEnabled(False)
        self.cancel.setEnabled(True)
        self.save.setEnabled(False)

    @QtCore.pyqtSlot(str)
    def _update_plot(self, msg):
        info = yaml.load(msg)
        t_idx = info['t_idx']
        y_idx = info['y_idx']
        cnt = info['err_cnt']
        self.err_arr[t_idx, y_idx, :] = cnt
        if cnt < 0:
            self.data_arr[t_idx, y_idx, :] = self.color_cursor
        else:
            self.data_arr[t_idx, y_idx, :] = int(round((self.max_err - cnt) * 255 / self.max_err))
            self.img_item.setImage(self.data_arr, levels=(0, 255))

    @QtCore.pyqtSlot()
    def _stop_measurement(self):
        if self.worker is not None:
            self.worker.stop = True
            self.worker.wait()
            self.worker = None

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
