# -*- coding: utf-8 -*-

"""This module defines various GUI components used to display information."""

import time

from PyQt5 import QtWidgets, QtCore

from ...math.serdes import get_ber


class LogWidget(QtWidgets.QFrame):
    """A widget used to display messages, with a clear button."""
    def __init__(self, parent=None):
        super(LogWidget, self).__init__(parent=parent)

        self.logger = QtWidgets.QPlainTextEdit(parent=self)
        self.logger.setReadOnly(True)

        button = QtWidgets.QPushButton('Clear Log', parent=self)
        # noinspection PyUnresolvedReferences
        button.clicked.connect(self.clear_log)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setStretch(0, 1)
        lay.setStretch(1, 0)
        lay.addWidget(self.logger)
        lay.addWidget(button)

    @QtCore.pyqtSlot()
    def clear_log(self):
        self.logger.setPlainText('')

    def println(self, msg):
        self.logger.appendPlainText(msg)


class BERDisplay(QtWidgets.QLabel):
    """A widget that displays BER."""
    def __init__(self, data_rate, confidence, err_max, targ_ber, parent=None):
        super(BERDisplay, self).__init__('NaN', parent=parent)

        self.cur_err = None
        self.cum_err = 0
        self.data_rate = data_rate
        self.confidence = confidence
        self.ref_time = 0
        self.err_max = err_max
        self.tol = targ_ber * 1e-3

    def setText(self, err_string):
        cur_time = time.time()
        cur_err = int(err_string)
        if self.cur_err is None:
            self.ref_time = cur_time
            self.cum_err = 0
            super(BERDisplay, self).setText('NaN')
        else:
            delta = cur_err - self.cur_err
            if delta < 0:
                delta += self.err_max
            nbits = int((cur_time - self.ref_time) * self.data_rate)
            self.cum_err += delta
            super(BERDisplay, self).setText('%.6g' % get_ber(self.confidence, nbits, self.cum_err, tol=self.tol))

        self.cur_err = cur_err

    @QtCore.pyqtSlot()
    def reset_error_count(self):
        cur_time = time.time()
        self.cur_err = None
        self.ref_time = cur_time
        self.cum_err = 0
        super(BERDisplay, self).setText('NaN')
