# -*- coding: utf-8 -*-

"""This module defines various GUI components used to display information."""

from PyQt5 import QtWidgets, QtCore


class LogWidget(QtWidgets.QFrame):
    """A widget used to display messages, with a clear button."""
    def __init__(self):
        super(LogWidget, self).__init__()

        self.logger = QtWidgets.QPlainTextEdit()
        self.logger.setReadOnly(True)

        button = QtWidgets.QPushButton('Clear Log')
        # noinspection PyUnresolvedReferences
        button.clicked.connect(self.clear_log)

        lay = QtWidgets.QVBoxLayout()
        lay.setSpacing(0)
        lay.setStretch(0, 1)
        lay.setStretch(1, 0)
        self.setLayout(lay)
        lay.addWidget(self.logger)
        lay.addWidget(button)

    @QtCore.pyqtSlot()
    def clear_log(self):
        self.logger.setPlainText('')

    def println(self, msg):
        self.logger.appendPlainText(msg)
