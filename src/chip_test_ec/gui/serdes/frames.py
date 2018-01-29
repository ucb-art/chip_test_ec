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

    color_unfilled = (143, 188, 143)
    color_cursor = (0, 206, 209)

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget,
                 conf_path: str = '', font_size: int = 11, parent: Optional[QtCore.QObject] = None):
        super(EyePlotFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)
        self.logger = logger
        self.color_arr = None
        self.err_arr = None
        self.worker = None
        self.max_ber = None
        self.min_ber = None
        with open(specs_fname, 'r') as f:
            self.config = yaml.load(f)

        self.img_item, self.plot_widget = self.create_eye_plot(self.config)

        # create panel control frame
        pc_frame, self.widgets, self.run, self.cancel, self.save = self.create_panel_controls(self.config)

        # populate frame
        self.lay.setSpacing(0)
        self.lay.addWidget(self.plot_widget, 0, 0)
        self.lay.addWidget(pc_frame, 1, 0)

    def create_eye_plot(self, config):
        tstart, tstop, tstep = config['t_sweep']
        ystart, ystop, ystep = config['y_sweep']
        y_name = config['y_name_list'][0]
        num_ticks = config['num_ticks']
        t_label = config['t_label']
        y_label = config['y_label']

        # create plot
        plot_widget = pyqtgraph.PlotWidget()
        plt_item = plot_widget.getPlotItem()
        img_item = pyqtgraph.ImageItem()
        plt_item.addItem(img_item)
        plt_item.showGrid(x=True, y=True, alpha=1)
        for key in plt_item.axes:
            plt_item.getAxis(key).setZValue(1)
        plt_item.setLabel('bottom', t_label)
        plt_item.setMouseEnabled(x=False, y=False)

        self._init_data(plt_item, img_item, y_label, y_name, tstart, tstop, tstep,
                        ystart, ystop, ystep, num_ticks)

        return img_item, plot_widget

    def create_panel_controls(self, config):
        # add sweep range spin boxes
        t_min, t_max = config['t_range']
        y_min, y_max = config['y_range']
        t_start, t_stop, t_step = config['t_sweep']
        y_start, y_stop, y_step = config['y_sweep']
        y_name_list = config['y_name_list']
        max_ber = config['max_ber']
        ber = config['ber']
        data_length = config['data_length']

        ctrl_info = [[dict(name='t_start', dtype='int', vmin=t_min, vmax=t_max, vdef=t_start),
                      dict(name='t_stop', dtype='int', vmin=t_min, vmax=t_max, vdef=t_stop),
                      dict(name='t_step', dtype='int', vmin=t_min, vmax=t_max, vdef=t_step),
                      ],
                     [dict(name='y_start', dtype='int', vmin=y_min, vmax=y_max, vdef=y_start),
                      dict(name='y_stop', dtype='int', vmin=y_min, vmax=y_max, vdef=y_stop),
                      dict(name='y_step', dtype='int', vmin=y_min, vmax=y_max, vdef=y_step),
                      ],
                     [dict(name='y_name', dtype='choice', values=y_name_list),
                      dict(name='y_guess', dtype='int', vmin=y_min, vmax=y_max),
                      dict(name='max_ber', dtype='float', vmin=0, vmax=1, decimals=4, vdef=max_ber),
                      dict(name='ber', dtype='float', vmin=0, vmax=1, decimals=4, vdef=ber),
                      ],
                     [dict(name='is_pattern', dtype='bool', vdef=False),
                      dict(name='pat_data', dtype='bin', nbits=data_length, ncol=3),
                      ],
                     ]

        # create input controls
        frame, lay = self.create_sub_frame()
        widget_list = self.create_input_controls(ctrl_info, lay)
        row_idx, col_idx = 4, 0

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

    def _init_data(self, plt_item, img_item, y_label, y_name, tstart, tstop, tstep,
                   ystart, ystop, ystep, num_ticks):
        tvec = np.arange(tstart, tstop, tstep)
        yvec = np.arange(ystart, ystop, ystep)
        num_t = len(tvec)
        num_y = len(yvec)
        mat_shape = (num_t, num_y)
        if self.color_arr is None or self.err_arr.shape != mat_shape:
            self.color_arr = np.empty((num_t, num_y, 3), dtype=int)
            self.err_arr = np.empty(mat_shape)

        self.color_arr[:] = self.color_unfilled
        self.err_arr.fill(-1)
        t0, tstep, y0, ystep = tvec[0], tvec[1] - tvec[0], yvec[0], yvec[1] - yvec[0]

        # create image
        img_item.setImage(self.color_arr, levels=(0, 255))
        view_rect = QtCore.QRectF(t0 - tstep / 2, y0 - ystep / 2, tstep * num_t, ystep * num_y)
        img_item.setRect(view_rect)

        # set tick values
        view_box = plt_item.getViewBox()
        view_box.setRange(rect=view_rect, update=True)
        t_tick_step = -(-num_t // num_ticks)
        y_tick_step = -(-num_y // num_ticks)
        xtick_minor = [(val, str(val)) for val in tvec[0::t_tick_step]]
        ytick_minor = [(val, str(val)) for val in yvec[0::y_tick_step]]
        plt_item.getAxis('bottom').setTicks([[], xtick_minor])
        plt_item.getAxis('left').setTicks([[], ytick_minor])
        plt_item.setLabel('left', y_label % y_name)

    @QtCore.pyqtSlot()
    def _start_measurement(self):
        if self.worker is None:

            mod_name = self.config['eye_module']
            cls_name = self.config['eye_class']
            num_ticks = self.config['num_ticks']
            y_label = self.config['y_label']
            input_vals = self.config['params'].copy()

            input_vals.update(self.get_input_values(self.widgets))
            self.max_ber = input_vals['max_ber']
            self.min_ber = input_vals['ber']
            y_name = input_vals['y_name']
            t_start, t_stop, t_step = input_vals['t_start'], input_vals['t_stop'], input_vals['t_step']
            y_start, y_stop, y_step = input_vals['y_start'], input_vals['y_stop'], input_vals['y_step']

            eye_config = {
                'module': mod_name,
                'class': cls_name,
                'params': input_vals,
            }

            plt_item = self.plot_widget.getPlotItem()
            self._init_data(plt_item, self.img_item, y_label, y_name, t_start, t_stop, t_step,
                            y_start, y_stop, y_step, num_ticks)

            self.worker = WorkerThread(self.ctrl, eye_config)
            self.worker.update.connect(self._update_plot)
            # noinspection PyUnresolvedReferences
            self.worker.finished.connect(self._stop_measurement)
            self.worker.start()

        self.run.setEnabled(False)
        self.cancel.setEnabled(True)
        self.save.setEnabled(False)

    @QtCore.pyqtSlot(str)
    def _update_plot(self, msg):
        info = yaml.load(msg)
        t_idx = info['t_idx']
        y_idx = info['y_idx']
        ber, cnt, ntot = info['val']
        self.err_arr[t_idx, y_idx] = ber
        if cnt < 0:
            self.color_arr[t_idx, y_idx, :] = self.color_cursor
        else:
            color_ber = min(max(self.min_ber, ber), self.max_ber)
            scale = (np.log10(color_ber) - np.log10(self.min_ber)) / (np.log10(self.max_ber) - np.log10(self.min_ber))
            self.color_arr[t_idx, y_idx, :] = int(round((1 - scale) * 255))
        self.img_item.setImage(self.color_arr, levels=(0, 255))

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


class TracePlotFrame(FrameBase):
    """A frame that contains inputs for trace plotting.

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

    color_unfilled = (143, 188, 143)
    color_cursor = (0, 206, 209)

    def __init__(self, ctrl: Controller, specs_fname: str, logger: LogWidget,
                 conf_path: str = '', font_size: int = 11, parent: Optional[QtCore.QObject] = None):
        super(TracePlotFrame, self).__init__(ctrl, conf_path=conf_path, font_size=font_size, parent=parent)
        self.logger = logger
        self.color_arr = None
        self.trace_err = None
        self.t0 = None
        self.tstep = None
        self.worker = None
        with open(specs_fname, 'r') as f:
            self.config = yaml.load(f)

        self.img_item, self.plot_widget = self.create_trace_plot(self.config)

        # create panel control frame
        pc_frame, self.widgets, self.run, self.cancel, self.save = self.create_panel_controls(self.config)

        # populate frame
        self.lay.setSpacing(0)
        self.lay.addWidget(self.plot_widget, 0, 0)
        self.lay.addWidget(pc_frame, 1, 0)

    def create_trace_plot(self, config):
        tstart, tstop, tstep = config['t_sweep']
        ystart, ystop, ystep = config['y_sweep']
        num_ticks = config['num_ticks']
        t_label = config['t_label']
        y_label = config['y_label']

        # create plot
        plot_widget = pyqtgraph.PlotWidget()
        plt_item = plot_widget.getPlotItem()
        img_item = pyqtgraph.ImageItem()
        plt_item.addItem(img_item)
        plt_item.showGrid(x=True, y=True, alpha=1)
        for key in plt_item.axes:
            plt_item.getAxis(key).setZValue(1)
        plt_item.setLabel('bottom', t_label)
        plt_item.setMouseEnabled(x=False, y=False)

        self._init_data(plt_item, img_item, y_label, tstart, tstop, tstep,
                        ystart, ystop, ystep, num_ticks)

        return img_item, plot_widget

    def create_panel_controls(self, config):
        # add sweep range spin boxes
        t_min, t_max = config['t_range']
        y_min, y_max = config['y_range']
        parity = config['parity']
        num_des = config['num_des']
        num_samp = config['num_samp']
        t_start, t_stop, t_step = config['t_sweep']
        y_start, y_stop, y_step = config['y_sweep']
        num_samp_max = config.get('num_samp_max', 1000)

        ctrl_info = [[dict(name='t_start', dtype='int', vmin=t_min, vmax=t_max, vdef=t_start),
                      dict(name='t_stop', dtype='int', vmin=t_min, vmax=t_max, vdef=t_stop),
                      dict(name='t_step', dtype='int', vmin=t_min, vmax=t_max, vdef=t_step),
                      ],
                     [dict(name='y_start', dtype='int', vmin=y_min, vmax=y_max, vdef=y_start),
                      dict(name='y_stop', dtype='int', vmin=y_min, vmax=y_max, vdef=y_stop),
                      dict(name='y_step', dtype='int', vmin=y_min, vmax=y_max, vdef=y_step),
                      ],
                     [dict(name='parity', dtype='int', vmin=0, vmax=num_des - 1, vdef=parity),
                      dict(name='y_guess', dtype='int', vmin=y_min, vmax=y_max),
                      dict(name='num_samp', dtype='int', vmin=1, vmax=num_samp_max, vdef=num_samp),
                      ],
                     ]

        # create input controls
        frame, lay = self.create_sub_frame()
        widget_list = self.create_input_controls(ctrl_info, lay)
        row_idx, col_idx = 4, 0

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

    def _init_data(self, plt_item, img_item, y_label, tstart, tstop, tstep,
                   ystart, ystop, ystep, num_ticks):
        output_len = self.config['output_len']
        tper = int(round(np.ceil(1e12 / self.config['data_rate'])))
        tstop_plot = tstop + tper * output_len

        tvec = np.arange(tstart, tstop_plot, tstep)
        yvec = np.arange(ystart, ystop, ystep)
        num_t = len(tvec)
        num_y = len(yvec)
        mat_shape = (num_t, num_y)
        if self.color_arr is None or self.trace_err.shape != mat_shape:
            self.color_arr = np.empty((num_t, num_y, 3), dtype=int)
            self.trace_err = np.empty(mat_shape)

        self.color_arr[:] = self.color_unfilled
        self.trace_err.fill(-1)
        self.t0 = tstart
        self.tstep = tstep

        # create image
        img_item.setImage(self.color_arr, levels=(0, 255))
        view_rect = QtCore.QRectF(tstart - tstep / 2, ystart - ystep / 2, tstep * num_t, ystep * num_y)
        img_item.setRect(view_rect)

        # set tick values
        view_box = plt_item.getViewBox()
        view_box.setRange(rect=view_rect, update=True)
        t_tick_step = -(-num_t // num_ticks)
        y_tick_step = -(-num_y // num_ticks)
        xtick_minor = [(val, str(val)) for val in tvec[0::t_tick_step]]
        ytick_minor = [(val, str(val)) for val in yvec[0::y_tick_step]]
        plt_item.getAxis('bottom').setTicks([[], xtick_minor])
        plt_item.getAxis('left').setTicks([[], ytick_minor])
        plt_item.setLabel('left', y_label)

    @QtCore.pyqtSlot()
    def _start_measurement(self):
        if self.worker is None:
            mod_name = self.config['trace_module']
            cls_name = self.config['trace_class']
            num_ticks = self.config['num_ticks']
            y_label = self.config['y_label']
            input_vals = self.config['params'].copy()

            input_vals.update(self.get_input_values(self.widgets))
            t_start, t_stop, t_step = input_vals['t_start'], input_vals['t_stop'], input_vals['t_step']
            y_start, y_stop, y_step = input_vals['y_start'], input_vals['y_stop'], input_vals['y_step']

            eye_config = {
                'module': mod_name,
                'class': cls_name,
                'params': input_vals,
            }

            plt_item = self.plot_widget.getPlotItem()
            self._init_data(plt_item, self.img_item, y_label, t_start, t_stop, t_step,
                            y_start, y_stop, y_step, num_ticks)

            self.worker = WorkerThread(self.ctrl, eye_config)
            self.worker.update.connect(self._update_plot)
            # noinspection PyUnresolvedReferences
            self.worker.finished.connect(self._stop_measurement)
            self.worker.start()

        self.run.setEnabled(False)
        self.cancel.setEnabled(True)
        self.save.setEnabled(False)

    @QtCore.pyqtSlot(str)
    def _update_plot(self, msg):
        info = yaml.load(msg)
        tval = info['tval']
        y_idx = info['y_idx']
        val = info['val']

        t_idx = int(round((tval - self.t0) / self.tstep))
        t_idx = max(0, min(t_idx, self.trace_err.shape[0]))
        self.trace_err[t_idx, y_idx] = val
        if val == 2:
            self.color_arr[t_idx, y_idx, :] = self.color_cursor
        elif val == 0:
            self.color_arr[t_idx, y_idx, :] = 255
        else:
            self.color_arr[t_idx, y_idx, :] = 0

        self.img_item.setImage(self.color_arr, levels=(0, 255))

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
            np.save(fname, self.trace_err)
