# -*- coding: utf-8 -*-

"""This module defines top level functions that starts the chip testing GUI."""

from PyQt5 import QtWidgets

from chip_test_ec.gui.base.frames import ControllerFrame
from chip_test_ec.gui.base.dialogs import FormDialog
from chip_test_ec.gui.core import MainWindow
from chip_test_ec.backend.core import Controller


def run_main(conf_path, ctrl_specs, gui_specs, font_size=11):
    app = QtWidgets.QApplication([])

    frame = ControllerFrame(conf_path, ctrl_specs, font_size=font_size)
    d = FormDialog(None, frame, 'Controller Setup')
    if d.exec_() == QtWidgets.QDialog.Accepted:
        ctrl_info = frame.get_controller_specs()
        ctrl = Controller(ctrl_info)
        w = MainWindow(ctrl, gui_specs, conf_path, font_size=font_size)
        w.show()
        return app.exec_()
    else:
        return -1
