# -*- coding: utf-8 -*-

"""This module defines the top level chip testing GUI window."""

from typing import Dict, Any

from PyQt5 import QtWidgets, QtGui

from .base.displays import LogWidget
from .scan.core import ScanFrame
from .gpib import GPIBFrame

# type check imports
from ..backend.core import Controller


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

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        self.setWindowTitle('Chip Testing Main Window')
        tabs = QtWidgets.QTabWidget()

        self.logger = LogWidget()

        frames = [ScanFrame(ctrl.scan, font_size=font_size),
                  GPIBFrame(ctrl.gpib_table, self.logger),
                  ]
        names = ['Scan',
                 'GPIB',
                 ]

        for f, n in zip(frames, names):
            scroll = QtWidgets.QScrollArea()
            scroll.setWidget(f)
            tabs.addTab(f, n)

        master = QtWidgets.QFrame()
        mlay = QtWidgets.QVBoxLayout()
        mlay.setSpacing(0)
        mlay.setStretch(0, 1)
        mlay.setStretch(1, 1)
        master.setLayout(mlay)
        mlay.addWidget(tabs)
        mlay.addWidget(self.logger)

        self.setCentralWidget(master)
        self.center()

    def center(self):
        window_gm = self.frameGeometry()
        cursor = QtWidgets.QApplication.desktop().cursor().pos()
        screen = QtWidgets.QApplication.desktop().screenNumber(cursor)
        center_point = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        window_gm.moveCenter(center_point)
        self.move(window_gm.topLeft())
