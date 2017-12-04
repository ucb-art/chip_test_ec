# -*- coding: utf-8 -*-

"""This module defines GPIBFrame, an interactive window for GPIB devices.
"""

import PyQt4.QtGui as QtGui
from PyQt4.QtCore import pyqtSlot

from .. import base


class GPIBFrame(QtGui.QFrame):
    def __init__(self, name_list, dev_list, logger):
        super(GPIBFrame, self).__init__()

        self.name_list = name_list
        self.dev_list = dev_list
        self.dev_sel = QtGui.QComboBox()
        self.dev_sel.addItems(name_list)
        self.q_cmd = base.LineEditHist(num_hist=200)
        self.w_cmd = base.LineEditHist(num_hist=200)
        self.logger = logger

        self.q_cmd.returnPressed.connect(self.send_query)
        self.w_cmd.returnPressed.connect(self.send_write)

        lay = QtGui.QFormLayout()
        self.setLayout(lay)
        lay.addRow('Device: ', self.dev_sel)
        lay.addRow('Query Cmd: ', self.q_cmd)
        lay.addRow('Write Cmd: ', self.w_cmd)

    @pyqtSlot()
    def send_query(self):
        dev = self.dev_list[self.dev_sel.currentIndex()]
        cmd = self.q_cmd.text()
        if dev is None:
            msg = 'No device to send query: {}'.format(cmd)
        else:
            msg = dev.query(cmd)
        self.logger.println(msg)
        self.q_cmd.selectAll()

    @pyqtSlot()
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
