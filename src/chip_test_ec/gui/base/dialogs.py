# -*- coding: utf-8 -*-

"""This module defines various dialogs.
"""

from PyQt5 import QtWidgets


class FormDialog(QtWidgets.QDialog):
    """A general dialog for user input forms, with OK and Cancel buttons.

    Parameters
    ----------
    parent :
        the parent of this dialog.
    frame :
        the center frame of this dialog.
    title : str
        the dialog title.
    """
    def __init__(self, parent, frame, title):
        super(FormDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.ok_button = QtWidgets.QPushButton('OK')
        self.cancel_button = QtWidgets.QPushButton('Cancel')
        # noinspection PyUnresolvedReferences
        self.ok_button.clicked.connect(self.accept)
        # noinspection PyUnresolvedReferences
        self.cancel_button.clicked.connect(self.reject)

        bot_lay = QtWidgets.QHBoxLayout()
        bot_lay.addWidget(self.ok_button)
        bot_lay.addWidget(self.cancel_button)
        bot_frame = QtWidgets.QFrame()
        bot_frame.setLayout(bot_lay)

        self.lay = QtWidgets.QVBoxLayout()
        self.setLayout(self.lay)
        self.lay.addWidget(frame)
        self.lay.addWidget(bot_frame)
