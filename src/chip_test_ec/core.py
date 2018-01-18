# -*- coding: utf-8 -*-

"""This module defines top level functions that starts the chip testing GUI."""

from PyQt5 import QtWidgets

from chip_test_ec.gui.core import MainWindow
from chip_test_ec.backend.core import Controller


def run_main(title, conf_path, ctrl_specs, gui_specs, font_size=11):
    app = QtWidgets.QApplication([])

    ctrl = Controller(ctrl_specs)
    w = MainWindow(title, ctrl, gui_specs, conf_path, font_size=font_size)
    w.show()
    return app.exec_()
