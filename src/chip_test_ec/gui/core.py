# -*- coding: utf-8 -*-

"""This module defines the top level chip testing GUI window."""

from typing import Dict, Any

from PyQt5 import QtWidgets, QtGui, QtCore

from .base.displays import LogWidget
from .scan.core import ScanFrame
from .gpib import GPIBFrame

# type check imports
from ..backend.core import Controller
from ..util.core import import_class


class MainWindow(QtWidgets.QMainWindow):
    """The main GUI window.

    Parameters
    ----------
    ctrl : Controller
        the Controller instance.
    gui_specs : Dict[str, Any]
        the GUI specification file.
    conf_path : str
        the GUI configuration directory.
    font_size : int
        the font size.
    """
    def __init__(self, ctrl: Controller, gui_specs: Dict[str, Any], conf_path: str, font_size: int=11) -> None:
        super(MainWindow, self).__init__()

        self.ctrl = ctrl

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        self.setWindowTitle('Chip Testing Main Window')
        # try to get Qt to delete all C++ objects before Python garbage collection kicks in
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.tabs = QtWidgets.QTabWidget(parent=self)

        self.logger = LogWidget(parent=self)

        frames = [ScanFrame(ctrl, self.logger, conf_path=conf_path, font_size=font_size, parent=self),
                  GPIBFrame(ctrl, self.logger, font_size=font_size, parent=self),
                  ]
        names = ['Scan',
                 'GPIB',
                 ]

        # add custom frames
        for gui_name in sorted(gui_specs.keys()):
            gui_config = gui_specs[gui_name]
            mod_name = gui_config['module']
            cls_name = gui_config['class']
            specs_fname = gui_config['specs_fname']
            gui_cls = import_class(mod_name, cls_name)
            gui_frame = gui_cls(ctrl, specs_fname, self.logger, conf_path=conf_path,
                                font_size=font_size, parent=self)
            frames.append(gui_frame)
            names.append(gui_name)

        for idx, (f, n) in enumerate(zip(frames, names)):
            if idx != 0:
                f.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
            self.tabs.addTab(f, n)

        # noinspection PyUnresolvedReferences
        self.tabs.currentChanged[int].connect(self._update_size)

        master = QtWidgets.QFrame(parent=self)
        mlay = QtWidgets.QVBoxLayout(master)
        mlay.setSpacing(0)
        mlay.setStretch(0, 0)
        mlay.setStretch(1, 1)
        mlay.addWidget(self.tabs)
        mlay.addWidget(self.logger)

        self.setCentralWidget(master)
        self.center()

    @QtCore.pyqtSlot(int)
    def _update_size(self, idx):
        tabs = self.tabs
        for i in range(tabs.count()):
            if i != idx:
                tabs.widget(i).setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                             QtWidgets.QSizePolicy.Ignored)
        cur_widget = tabs.widget(idx)
        cur_widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                 QtWidgets.QSizePolicy.Minimum)
        cur_widget.resize(cur_widget.minimumSizeHint())
        cur_widget.adjustSize()
        tabs.resize(tabs.minimumSizeHint())
        tabs.adjustSize()

    def closeEvent(self, event):
        self.ctrl.close()
        event.accept()

    def center(self):
        window_gm = self.frameGeometry()
        cursor = QtWidgets.QApplication.desktop().cursor().pos()
        screen = QtWidgets.QApplication.desktop().screenNumber(cursor)
        center_point = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        window_gm.moveCenter(center_point)
        self.move(window_gm.topLeft())
