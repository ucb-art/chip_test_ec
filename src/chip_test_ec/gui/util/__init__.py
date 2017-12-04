# -*- coding: utf-8 -*-

"""This package contains various convenience functions for Qt
"""

from itertools import izip
import PyQt4.QtGui as QtGui


def make_form(name_list, widget_list):
    """Create a QFrame containing labels to the left of the widgets.

    Parameters
    ----------
    name_list : list[str]
        names of the widgets.
    widget_list : list[QtGui.QWidget]
        the widgets.

    Returns
    -------
    frame : QtGui.QFrame
        a QFrame containing labels and widgets.
    """
    frame = QtGui.QFrame()
    lay = QtGui.QFormLayout()
    frame.setLayout(lay)
    for name, widget in izip(name_list, widget_list):
        lay.addRow(name, widget)
    return frame
