# -*- coding: utf-8 -*-

"""This module defines LineEditHist, a line edit that keeps track of histories, and can
move between histories with up/down arrow.
"""

from collections import deque
from PyQt4.QtCore import pyqtSlot
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui


class LineEditHist(QtGui.QLineEdit):
    def __init__(self, hist_queue=None, num_hist=200):
        super(LineEditHist, self).__init__()
        if hist_queue is None:
            self.histories = deque(maxlen=num_hist)
        else:
            self.histories = hist_queue
        self.cur_idx = 0
        self.returnPressed.connect(self.addHistory)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Up:
            if self.cur_idx - 1 >= 0:
                self.cur_idx -= 1
                self.setText(self.histories[self.cur_idx])
                self.selectAll()
        elif event.key() == QtCore.Qt.Key_Down:
            if self.cur_idx + 1 <= len(self.histories):
                self.cur_idx += 1
                if self.cur_idx == len(self.histories):
                    ntext = ''
                else:
                    ntext = self.histories[self.cur_idx]
                self.setText(ntext)
                self.selectAll()
        else:
            super(LineEditHist, self).keyPressEvent(event)

    @pyqtSlot()
    def addHistory(self):
        cmd = self.text()
        self.histories.append(cmd)
        self.cur_idx = len(self.histories)
