# -*- coding: utf-8 -*-

"""This module defines various custom fields, which are GUI components that retrieve one value from the user.
"""

import os
import math

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot


class FileField(QtWidgets.QFrame):
    """This is a widget that allows user to select a file.

    Parameters
    ----------
    init_text : str
        the default text to display.
    get_dir : bool
        True if this field is for selecting a directory.
    """
    def __init__(self, init_text: str, get_dir: bool=False) -> None:
        super(FileField, self).__init__()

        self.edit = QtWidgets.QLineEdit(init_text)
        self.get_dir = get_dir
        browse = QtWidgets.QPushButton('...')

        # noinspection PyUnresolvedReferences
        browse.clicked.connect(self._open_browser)

        self.lay = QtWidgets.QHBoxLayout()
        self.setLayout(self.lay)
        self.lay.addWidget(self.edit)
        self.lay.addWidget(browse)
        self.lay.setStretch(0, 1)
        self.lay.setStretch(1, 0)

    @pyqtSlot()
    def _open_browser(self) -> None:
        cur_file = self.edit.text()
        if os.path.exists(cur_file):
            cur_dir = os.path.dirname(cur_file)
        else:
            cur_dir = os.getcwd()
        if not self.get_dir:
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', cur_dir)
        else:
            fname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory', cur_dir)
        if fname:
            self.edit.setText(fname)

    def text(self) -> str:
        return self.edit.text()

    # noinspection PyPep8Naming
    def setText(self, val: str) -> None:
        self.edit.setText(val)


class MetricSpinBox(QtWidgets.QDoubleSpinBox):
    """A spinbox field with metric prefix display.

    Parameters
    ----------
    vmin : float
        the minimum value.
    vmax : float
        the maximum value.
    vstep : float
        the spinbox step size.
    precision : int
        the displayed precision.
    """

    # metric prefix names and exponents
    prefix_names = ['y', 'z', 'a', 'f', 'p', 'n', 'u', 'm', '',
                    'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    prefix_exp = [-24, -21, -18, -15, -12, -9, -6, -3, 0,
                  3, 6, 9, 12, 15, 18, 21, 24]

    def __init__(self, vmin: float, vmax: float, vstep: float, precision: int) -> None:
        super(MetricSpinBox, self).__init__()
        exp = int(math.floor(math.log10(vstep)))
        if exp < self.prefix_exp[0] or exp > self.prefix_exp[-1]:
            prefix = 'e{}'.format(exp)
            self.scale = 10.0**exp
        elif exp in self.prefix_exp:
            prefix = self.prefix_names[self.prefix_exp.index(exp)]
            self.scale = 10.0**exp
        else:
            idx = None
            for i in range(len(self.prefix_exp)):
                if self.prefix_exp[i + 1] > exp:
                    idx = i + 1
                    break
            prefix = self.prefix_names[idx]
            diff = self.prefix_exp[idx] - exp
            precision = max(precision, diff)
            self.scale = 10.0**self.prefix_exp[idx]

        vstep = int(round(vstep / self.scale * 10.0**precision)) * 10.0**(-precision)
        vmin /= self.scale
        vmax /= self.scale
        self.setSingleStep(vstep)
        self.setMinimum(vmin)
        self.setMaximum(vmax)
        self.setDecimals(precision)
        self.setSuffix(' ' + prefix)

    def value(self) -> float:
        val = super(MetricSpinBox, self).value()
        return val * self.scale

    def setValue(self, val: float) -> None:
        super(MetricSpinBox, self).setValue(val / self.scale)
