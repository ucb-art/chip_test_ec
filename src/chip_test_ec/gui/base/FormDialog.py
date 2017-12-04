# -*- coding: utf-8 -*-

"""This module defines FormDialog, a dialog for user input forms with OK/cancel.
"""

from PyQt4 import QtGui as QtGui


class FormDialog(QtGui.QDialog):
    """A general dialog for user input forms
    """
    def __init__(self, parent, frame, title):
        """Create a new FormDialog.

        Parameters
        ----------
        parent :
            the parent of this dialog.
        frame :
            the center frame of this dialog.
        title : str
            the dialog title.
        """
        super(FormDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.ok_button = QtGui.QPushButton('OK')
        self.cancel_button = QtGui.QPushButton('Cancel')
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        bot_lay = QtGui.QHBoxLayout()
        bot_lay.addWidget(self.ok_button)
        bot_lay.addWidget(self.cancel_button)
        bot_frame = QtGui.QFrame()
        bot_frame.setLayout(bot_lay)

        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.lay.addWidget(frame)
        self.lay.addWidget(bot_frame)
