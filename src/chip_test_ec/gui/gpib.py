# -*- coding: utf-8 -*-

"""This module defines GUI components that let users interact with GPIB devices."""

from typing import TYPE_CHECKING, Sequence

from PyQt5 import QtWidgets, QtCore

from .base.fields import LineEditHist

if TYPE_CHECKING:
    from ..backend.gpib.core import GPIBController
    from .base.displays import LogWidget


class GPIBFrame(QtWidgets.QFrame):
    """A simple frame that contains text boxes that let user communicate with a GPIB device.

    This component allows user to send arbitrary commands to a GPIB device.  This is mainly
    used as a debugging tool.

    Parameters
    ----------
    name_list : Sequence[str]
        a list of GPIB device names.
    dev_list : Sequence[GPIBController]
        a list of GPIB device controllers.
    logger : LogWidget
        the LogWidget used to display messages.

    """
    def __init__(self, name_list: Sequence[str], dev_list: Sequence[GPIBController], logger: LogWidget):
        super(GPIBFrame, self).__init__()

        self.name_list = name_list
        self.dev_list = dev_list
        self.dev_sel = QtWidgets.QComboBox()
        self.dev_sel.addItems(name_list)
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
        dev = self.dev_list[self.dev_sel.currentIndex()]
        cmd = self.q_cmd.text()
        if dev is None:
            msg = 'No device to send query: {}'.format(cmd)
        else:
            msg = dev.query(cmd)
        self.logger.println(msg)
        self.q_cmd.selectAll()

    @QtCore.pyqtSlot()
    def send_write(self):
        dev = self.dev_list[self.dev_sel.currentIndex()]
        cmd = self.w_cmd.text()
        if dev is None:
            msg = 'No device to send command: {}'.format(cmd)
        else:
            dev.write(cmd)
            msg = 'Command sent: {}'.format(cmd)
        self.logger.println(msg)
        self.w_cmd.selectAll()
