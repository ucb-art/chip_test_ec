# -*- coding: utf-8 -*-


"""This package contains GUI components for SERDES receiver testing.
"""

from PyQt5 import QtWidgets, QtCore, QtGui


class RXControlFrame(QtWidgets.QFrame):
    """A Frame that displays all RX controls and real time update of RX output.

    Parameters
    ----------
    fpga : chip_test_ec.backend.fpga.base.FPGABase
        the scan chain object.
    font_size : int
        the font size for this frame.]
    """
    def __init__(self, fpga, font_size=11):
        super(RXControlFrame, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.fpga = fpga

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)
