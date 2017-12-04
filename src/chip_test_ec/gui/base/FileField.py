# -*- coding: utf-8 -*-

"""This module contains FileField, a QFrame containing a QLineEdit and a button
that browses for file.
"""

import os
import PyQt4.QtGui as QtGui


class FileField(QtGui.QFrame):
    def __init__(self, init_text, get_dir=False):
        super(FileField, self).__init__()

        self.edit = QtGui.QLineEdit(init_text)
        self.get_dir = get_dir
        browse = QtGui.QPushButton('...')

        browse.clicked.connect(self.open_browser)

        self.lay = QtGui.QHBoxLayout()
        self.setLayout(self.lay)
        self.lay.addWidget(self.edit)
        self.lay.addWidget(browse)
        self.lay.setStretch(0, 1)
        self.lay.setStretch(1, 0)

    def open_browser(self):
        cur_file = self.edit.text()
        if os.path.exists(cur_file):
            cur_dir = os.path.dirname(cur_file)
        else:
            cur_dir = os.getcwd()
        if not self.get_dir:
            fname = QtGui.QFileDialog.getOpenFileName(self, 'Select File', cur_dir)
        else:
            fname = QtGui.QFileDialog.getExistingDirectory(self, 'Select Directory', cur_dir)
        if fname:
            self.edit.setText(fname)

    def text(self):
        return self.edit.text()

    def setText(self, val):
        self.edit.setText(val)
