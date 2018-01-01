# -*- coding: utf-8 -*-

"""This module defines various custom fields, which are GUI components that retrieve one value from the user.
"""

from typing import Optional

import os
import math
from collections import deque

import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui


class FileField(QtWidgets.QFrame):
    """This is a widget that allows user to select a file.

    Parameters
    ----------
    init_text : str
        the default text to display.
    get_dir : bool
        True if this field is for selecting a directory.
    """

    def __init__(self, init_text: str, get_dir: bool = False, parent=None) -> None:
        super(FileField, self).__init__(parent=parent)

        self.edit = QtWidgets.QLineEdit(init_text, parent=self)
        self.get_dir = get_dir
        browse = QtWidgets.QPushButton('...', parent=self)

        # noinspection PyUnresolvedReferences
        browse.clicked.connect(self._open_browser)

        self.lay = QtWidgets.QHBoxLayout(self)
        self.lay.addWidget(self.edit)
        self.lay.addWidget(browse)
        self.lay.setStretch(0, 1)
        self.lay.setStretch(1, 0)

    @QtCore.pyqtSlot()
    def _open_browser(self) -> None:
        cur_file = self.edit.text()
        if os.path.exists(cur_file):
            cur_dir = os.path.dirname(cur_file)
        else:
            cur_dir = os.getcwd()
        if not self.get_dir:
            fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', cur_dir)
        else:
            fname, _ = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory', cur_dir)
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

    def __init__(self, vmin: float, vmax: float, vstep: float, precision: int, parent=None) -> None:
        super(MetricSpinBox, self).__init__(parent=parent)
        exp = int(math.floor(math.log10(vstep)))
        if exp < self.prefix_exp[0] or exp > self.prefix_exp[-1]:
            prefix = 'e{}'.format(exp)
            self.scale = 10.0 ** exp
        elif exp in self.prefix_exp:
            prefix = self.prefix_names[self.prefix_exp.index(exp)]
            self.scale = 10.0 ** exp
        else:
            idx = None
            for i in range(len(self.prefix_exp)):
                if self.prefix_exp[i + 1] > exp:
                    idx = i + 1
                    break
            prefix = self.prefix_names[idx]
            diff = self.prefix_exp[idx] - exp
            precision = max(precision, diff)
            self.scale = 10.0 ** self.prefix_exp[idx]

        vstep = int(round(vstep / self.scale * 10.0 ** precision)) * 10.0 ** (-precision)
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


class QBigIntValidator(QtGui.QValidator):
    """A validator for big integers."""
    def __init__(self, vmin, vmax, parent=None):
        super(QBigIntValidator, self).__init__(parent)
        self._min = vmin
        self._max = vmax

    # noinspection PyShadowingBuiltins
    def validate(self, input, pos):
        if not input:
            return QtGui.QValidator.Intermediate, input, pos
        try:
            val = int(input)
        except ValueError:
            return QtGui.QValidator.Invalid, input, pos

        if val > self._max:
            return QtGui.QValidator.Invalid, input, pos
        elif val < self._min:
            return QtGui.QValidator.Intermediate, input, pos
        else:
            return QtGui.QValidator.Acceptable, input, pos

    # noinspection PyShadowingBuiltins
    def fixup(self, input):
        if not input:
            return input
        try:
            val = int(input)
        except ValueError:
            return str((self._min + self._max) // 2)
        if val > self._max:
            return str(self._max)
        return input

    # noinspection PyPep8Naming
    def setRange(self, vmin, vmax):
        self._min = vmin
        self._max = vmax


class QBinaryValidator(QtGui.QValidator):
    """A validator for big integers."""
    def __init__(self, num_bits, parent=None):
        super(QBinaryValidator, self).__init__(parent)
        self._num_bits = num_bits

    # noinspection PyShadowingBuiltins
    def validate(self, input, pos):
        if not input:
            return QtGui.QValidator.Intermediate, input, pos
        try:
            val = int(input, 2)
        except ValueError:
            return QtGui.QValidator.Invalid, input, pos

        if val < 0:
            return QtGui.QValidator.Invalid, input, pos
        else:
            input_len = len(input)
            if input_len == self._num_bits:
                return QtGui.QValidator.Acceptable, input, pos
            elif input_len > self._num_bits:
                return QtGui.QValidator.Invalid, input, pos
            else:
                return QtGui.QValidator.Intermediate, input, pos

    # noinspection PyShadowingBuiltins
    def fixup(self, input):
        if not input:
            return '0' * self._num_bits
        try:
            val = int(input, 2)
        except ValueError:
            return '0' * self._num_bits

        if val < 0:
            input = input[1:]

        input = input * (-(-self._num_bits // len(input)))
        return input[:self._num_bits]


class BigIntSpinbox(QtWidgets.QAbstractSpinBox):
    """An integer spin box that supports arbitrary integers of given length.

    This implementation is based on the solution here:
    https://stackoverflow.com/questions/15654769/
    how-to-subclass-qspinbox-so-it-could-have-int64-values-as-maxium-and-minimum
    """

    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(BigIntSpinbox, self).__init__(parent)

        self._singleStep = 1
        self._minimum = 0
        self._maximum = 100
        self._val = 0
        self._validator = QBigIntValidator(self._minimum, self._maximum, parent=self)
        self.lineEdit().setValidator(self._validator)
        # noinspection PyUnresolvedReferences
        self.lineEdit().editingFinished.connect(self.setText)

    def value(self):
        return self._val

    # noinspection PyPep8Naming
    @QtCore.pyqtSlot()
    def setText(self):
        self.setValue(int(self.lineEdit().text()))

    # noinspection PyPep8Naming
    def setValue(self, value):
        self._val = value
        self.lineEdit().setText(str(value))
        # noinspection PyUnresolvedReferences
        self.valueChanged.emit(self._val)

    # noinspection PyPep8Naming
    def singleStep(self):
        return self._singleStep

    # noinspection PyPep8Naming
    def setSingleStep(self, singleStep):
        assert isinstance(singleStep, int)
        # don't use negative values
        self._singleStep = abs(singleStep)

    def minimum(self):
        return self._minimum

    # noinspection PyPep8Naming
    def setMinimum(self, minimum):
        if isinstance(minimum, int):
            self._minimum = minimum
            self._validator.setRange(self._minimum, self._maximum)

    def maximum(self):
        return self._maximum

    # noinspection PyPep8Naming
    def setMaximum(self, maximum):
        if isinstance(maximum, int):
            self._maximum = maximum
            self._validator.setRange(self._minimum, self._maximum)

    def stepBy(self, steps):
        new_val = min(self._maximum, max(self._minimum, self._val + steps * self._singleStep))
        self.setValue(new_val)

    def stepEnabled(self):
        return self.StepUpEnabled | self.StepDownEnabled


class LineEditHist(QtWidgets.QLineEdit):
    """A subclass of QLineEdit that keeps track of histories.

    Parameters
    ----------
    hist_queue : Optional[deque]
        the history deque instance.  If None, create a new one.
    num_hist : int
        number of history to keep track of.
    """

    def __init__(self, hist_queue: Optional[deque] = None, num_hist: int = 200, parent=None):
        super(LineEditHist, self).__init__(parent=parent)
        if hist_queue is None:
            self.histories = deque(maxlen=num_hist)
        else:
            self.histories = hist_queue
        self.cur_idx = 0
        # noinspection PyUnresolvedReferences
        self.returnPressed.connect(self.add_history)

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

    @QtCore.pyqtSlot()
    def add_history(self):
        cmd = self.text()
        self.histories.append(cmd)
        self.cur_idx = len(self.histories)


class LineEditBinary(QtWidgets.QLineEdit):
    """A subclass of QLineEdit that edits a fixed-length binary string.

    Parameters
    ----------
    init_val : int
        initial value.
    num_bits : int
        number of bits in the binary string.
    parent :
        the parent QObject.
    """

    def __init__(self, init_val: int, num_bits: int, parent=None):
        init_val = init_val & ((1 << num_bits) - 1)
        init_str = np.binary_repr(init_val, num_bits)
        super(LineEditBinary, self).__init__(init_str, parent=parent)

        self.bin_validator = QBinaryValidator(num_bits, parent=self)
        self.setValidator(self.bin_validator)

        self.disp_font = QtGui.QFont('Monospace')
        self.disp_font.setStyleHint(QtGui.QFont.TypeWriter)
        self.setFont(self.disp_font)

        metric = QtGui.QFontMetrics(self.disp_font)
        self.setMinimumWidth(metric.width('0' * num_bits))
