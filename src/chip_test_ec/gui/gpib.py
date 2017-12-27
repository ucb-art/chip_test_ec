# -*- coding: utf-8 -*-

"""This module defines GUI components that let users interact with GPIB devices."""

from PyQt5 import QtWidgets, QtCore

from .base.fields import LineEditHist

# type check imports
from ..backend.core import Controller
from .base.displays import LogWidget


class GPIBFrame(QtWidgets.QFrame):
    """A simple frame that contains text boxes that let user communicate with a GPIB device.

    This component allows user to send arbitrary commands to a GPIB device.  This is mainly
    used as a debugging tool.

    Parameters
    ----------
    ctrl : Controller
        The controller object.
    logger : LogWidget
        the LogWidget used to display messages.

    """
    def __init__(self, ctrl: Controller, logger: LogWidget):
        super(GPIBFrame, self).__init__()

        self.ctrl = ctrl
        gpib_table = ctrl.gpib_table
        self.name_list = sorted(gpib_table.keys())
        self.dev_sel = QtWidgets.QComboBox()
        self.dev_sel.addItems(self.name_list)
        self.q_cmd = LineEditHist(num_hist=200)
        self.w_cmd = LineEditHist(num_hist=200)
        self.logger = logger

        # noinspection PyUnresolvedReferences
        self.q_cmd.returnPressed.connect(self.send_query)
        # noinspection PyUnresolvedReferences
        self.w_cmd.returnPressed.connect(self.send_write)

        lay = QtWidgets.QFormLayout()
        self.setLayout(lay)
        lay.addRow('Device: ', self.dev_sel)
        lay.addRow('Query Cmd: ', self.q_cmd)
        lay.addRow('Write Cmd: ', self.w_cmd)

    @QtCore.pyqtSlot()
    def send_query(self):
        dev_name = self.name_list[self.dev_sel.currentIndex()]
        dev = self.ctrl.gpib_table[dev_name]
        cmd = self.q_cmd.text()
        if dev is None:
            msg = 'No device to send query: {}'.format(cmd)
        else:
            msg = dev.query(cmd)
        self.logger.println(msg)
        self.q_cmd.selectAll()

    @QtCore.pyqtSlot()
    def send_write(self):
        dev_name = self.name_list[self.dev_sel.currentIndex()]
        dev = self.ctrl.gpib_table[dev_name]
        cmd = self.w_cmd.text()
        if dev is None:
            msg = 'No device to send command: {}'.format(cmd)
        else:
            dev.write(cmd)
            msg = 'Command sent: {}'.format(cmd)
        self.logger.println(msg)
        self.w_cmd.selectAll()
