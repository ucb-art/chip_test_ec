# -*- coding: utf-8 -*-

"""This module defines a frame that provides scan chain editing functionality.
"""

import os

from PyQt5 import QtWidgets, QtCore, QtGui

from .models import ScanItemModel, ScanSortFilterProxyModel
from ..base.forms import make_form


class ScanDelegate(QtWidgets.QStyledItemDelegate):
    """A subclass of QStyledItemDelegate that creates spin boxes for editing scan buses

    This delegate create spin boxes with smart max/min values and adjustable step size.
    """
    def __init__(self, parent=None):
        super(ScanDelegate, self).__init__(parent)
        self.step = 1

    def createEditor(self, parent, option, index):
        nbits = index.data(QtCore.Qt.UserRole)
        nmax = 2**nbits - 1

        editor = QtWidgets.QSpinBox(parent)
        editor.setFrame(False)
        editor.setMinimum(0)
        editor.setMaximum(nmax)
        editor.setSingleStep(min(self.step, nmax))

        # noinspection PyUnusedLocal
        @QtCore.pyqtSlot()
        def modify(value):
            self.setModelData(editor, index.model(), index)

        # noinspection PyUnresolvedReferences
        editor.valueChanged[int].connect(modify)
        return editor

    @QtCore.pyqtSlot(int)
    def set_step_size(self, step):
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


class ScanFrame(QtWidgets.QFrame):
    """A Frame that displays the scan chain, and allows for user editing.

    Parameters
    ----------
    scan_ctrl : chip_test_ec.backend.scan.core.Scan
        the scan chain object.
    font_size : int
        the font size for this frame.
    max_step : int
        maximum scan bus spinbox step size.
    """
    def __init__(self, scan_ctrl, font_size=11, max_step=8192):
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
        filter_text = QtWidgets.QLineEdit()
        # noinspection PyUnresolvedReferences
        filter_text.textChanged[str].connect(proxy.update_filter)
        top_frame = make_form(['Filter: '], [filter_text])

        # configure tree view
        self.lay = QtWidgets.QVBoxLayout()
        self.setLayout(self.lay)
        self.view = QtWidgets.QTreeView()
        self.view.setItemDelegate(self.delegate)
        self.view.setSortingEnabled(True)
        self.view.header().setSortIndicatorShown(True)
        self.view.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.view.header().setSectionsClickable(True)
        self.view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.view.setModel(proxy)

        # configure step box and sync checkbox
        checkbox = QtWidgets.QCheckBox("Disable sync")
        # noinspection PyUnresolvedReferences
        checkbox.stateChanged[int].connect(model.set_sync_flag)
        self.stepbox = QtWidgets.QSpinBox()
        self.stepbox.setMaximum(max_step)
        self.stepbox.setValue(1)
        # noinspection PyUnresolvedReferences
        self.stepbox.valueChanged[int].connect(self.delegate.set_step_size)
        bot_frame = QtWidgets.QFrame()
        bot_lay = QtWidgets.QHBoxLayout()
        bot_frame.setLayout(bot_lay)
        bot_lay.addWidget(checkbox)
        bot_lay.addWidget(make_form(['Step Size: '], [self.stepbox]))

        save_button = QtWidgets.QPushButton('Save To File...')
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self.save_to_file)
        set_button = QtWidgets.QPushButton('Set From File')
        # noinspection PyUnresolvedReferences
        set_button.clicked.connect(self.set_from_file)

        temp1 = QtWidgets.QFrame()
        temp2 = QtWidgets.QHBoxLayout()
        temp1.setLayout(temp2)
        temp2.addWidget(save_button)
        temp2.addWidget(set_button)

        # add all GUI elements
        self.lay.addWidget(top_frame)
        self.lay.addWidget(self.view)
        self.lay.addWidget(bot_frame)
        self.lay.addWidget(temp1)

    @QtCore.pyqtSlot()
    def set_from_file(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', cur_dir)
        if fname:
            self.model.set_from_file(fname)

    @QtCore.pyqtSlot()
    def save_to_file(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select File', cur_dir)
        if fname:
            self.model.save_to_file(fname)
