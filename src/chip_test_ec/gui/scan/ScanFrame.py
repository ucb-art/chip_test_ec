# -*- coding: utf-8 -*-

"""This module defines a frame that provides scan chain editing functionality.
"""

import os

import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui
from PyQt4.QtCore import pyqtSlot

from .ScanItemModel import ScanItemModel
from .. import util


class ScanSortFilterProxyModel(QtGui.QSortFilterProxyModel):
    """A subclass of QSortFilterProxyModel that works on
    full scan bus name.
    """
    def __init__(self, parent=None):
        super(ScanSortFilterProxyModel, self).__init__(parent)

    def filterAcceptsRow(self, row, parent):
        source = self.sourceModel()
        cur_idx = source.index(row, self.filterKeyColumn(), parent)
        if not cur_idx.isValid():
            return False
        cur_name = source.data(cur_idx, QtCore.Qt.DisplayRole)
        idx = cur_idx.parent()
        while idx is not None and idx.isValid():
            cur_name = source.data(idx, QtCore.Qt.DisplayRole) + '.' + cur_name
            idx = idx.parent()
        if self.filterRegExp().indexIn(cur_name) >= 0:
            return True
        max_row = source.rowCount(cur_idx)
        for r in xrange(max_row):
            if self.filterAcceptsRow(r, cur_idx):
                return True
        return False

    @pyqtSlot(str)
    def update_filter(self, text):
        new_exp = QtCore.QRegExp(text)
        new_exp.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setFilterRegExp(new_exp)


class ScanDelegate(QtGui.QStyledItemDelegate):
    """A subclass of QStyledItemDelegate that creates spin boxes
    for editing scan buses, with smart max/min values and adjustable
    step size.
    """
    def __init__(self, parent=None):
        super(ScanDelegate, self).__init__(parent)
        self.step = 1

    def createEditor(self, parent, option, index):
        nbits = index.data(QtCore.Qt.UserRole)
        nmax = 2**nbits - 1

        editor = QtGui.QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(0)
        editor.setMaximum(nmax)
        editor.setSingleStep(min(self.step, nmax))

        @pyqtSlot()
        def modify(value):
            self.setModelData(editor, index.model(), index)

        editor.valueChanged[int].connect(modify)
        return editor

    @pyqtSlot(int)
    def setStepSize(self, step):
        """Set the step size of the QSpinBox

        Parameters
        ----------
        step : int
            the new step size.
        """
        self.step = step

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        if value is not None:
            editor.setValue(value)

    def setModelData(self, editor, model, index):
        editor.interpretText()
        value = editor.value()
        cur_value = model.data(index, QtCore.Qt.EditRole)
        if cur_value != value:
            model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class ScanFrame(QtGui.QFrame):
    def __init__(self, scan_ctrl, font_size=11, max_step=8192):
        """Create a new ScanFrame to display the given scan data.

        Parameters
        ----------
        scan_ctrl : scan.Scan
            the scan chain object.
        """
        super(ScanFrame, self).__init__()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        model = ScanItemModel(scan_ctrl)
        self.model = model
        self.delegate = ScanDelegate()

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        # configure filter
        proxy = ScanSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterKeyColumn(0)
        filter_text = QtGui.QLineEdit()
        filter_text.textChanged[str].connect(proxy.update_filter)
        top_frame = util.make_form(['Filter: '], [filter_text])

        # configure tree view
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.view = QtGui.QTreeView()
        self.view.setItemDelegate(self.delegate)
        self.view.setSortingEnabled(True)
        self.view.header().setSortIndicatorShown(True)
        self.view.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.view.header().setClickable(True)
        self.view.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.view.setModel(proxy)

        # configure step box and sync checkbox
        checkbox = QtGui.QCheckBox("Disable sync")
        checkbox.stateChanged[int].connect(model.setSyncFlag)
        self.stepbox = QtGui.QSpinBox()
        self.stepbox.setMaximum(max_step)
        self.stepbox.setValue(1)
        self.stepbox.valueChanged[int].connect(self.delegate.setStepSize)
        bot_frame = QtGui.QFrame()
        bot_lay = QtGui.QHBoxLayout()
        bot_frame.setLayout(bot_lay)
        bot_lay.addWidget(checkbox)
        bot_lay.addWidget(util.make_form(['Step Size: '], [self.stepbox]))

        save_button = QtGui.QPushButton('Save To File...')
        save_button.clicked.connect(self.save_to_file)
        set_button = QtGui.QPushButton('Set From File')
        set_button.clicked.connect(self.set_from_file)

        temp1 = QtGui.QFrame()
        temp2 = QtGui.QHBoxLayout()
        temp1.setLayout(temp2)
        temp2.addWidget(save_button)
        temp2.addWidget(set_button)

        # add all GUI elements
        self.lay.addWidget(top_frame)
        self.lay.addWidget(self.view)
        self.lay.addWidget(bot_frame)
        self.lay.addWidget(temp1)

    @pyqtSlot()
    def set_from_file(self):
        cur_dir = os.getcwd()
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select File', cur_dir)
        if fname:
            self.model.setFromFile(fname)

    @pyqtSlot()
    def save_to_file(self):
        cur_dir = os.getcwd()
        fname = QtGui.QFileDialog.getSaveFileName(self, 'Select File', cur_dir)
        if fname:
            self.model.saveToFile(fname)
