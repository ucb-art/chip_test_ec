# -*- coding: utf-8 -*-

"""This module defines LogWidget, a widget for displaying log messages.
"""

import PyQt4.QtGui as QtGui


class LogWidget(QtGui.QFrame):
    def __init__(self):
        super(LogWidget, self).__init__()

        self.logger = QtGui.QPlainTextEdit()
        self.logger.setReadOnly(True)

        button = QtGui.QPushButton('Clear Log')
        button.clicked.connect(self.clear_log)

        lay = QtGui.QVBoxLayout()
        self.setLayout(lay)
        lay.addWidget(self.logger)
        lay.addWidget(button)

    def clear_log(self):
        self.logger.setPlainText('')

    def println(self, msg):
        self.logger.appendPlainText(msg)
