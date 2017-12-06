# -*- coding: utf-8 -*-

"""This module defines a frame that provides scan chain editing functionality.
"""

import os

from PyQt5 import QtWidgets, QtCore, QtGui

from .models import ScanItemModel, ScanSortFilterProxyModel


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
        filter_label = QtWidgets.QLabel('&Filter:')
        filter_label.setBuddy(filter_text)

        # configure tree view
        self.view = QtWidgets.QTreeView()
        self.view.setItemDelegate(self.delegate)
        self.view.setSortingEnabled(True)
        self.view.header().setSortIndicatorShown(True)
        self.view.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.view.header().setSectionsClickable(True)
        self.view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.view.setModel(proxy)

        # configure step box, sync checkbox, and buttons
        checkbox = QtWidgets.QCheckBox('Disable sync')
        # noinspection PyUnresolvedReferences
        checkbox.stateChanged[int].connect(model.set_sync_flag)
        self.stepbox = QtWidgets.QSpinBox()
        self.stepbox.setMaximum(max_step)
        self.stepbox.setValue(1)
        # noinspection PyUnresolvedReferences
        self.stepbox.valueChanged[int].connect(self.delegate.set_step_size)
        step_label = QtWidgets.QLabel('&Step Size:')
        step_label.setBuddy(self.stepbox)
        save_button = QtWidgets.QPushButton('Save To File...')
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self.save_to_file)
        set_button = QtWidgets.QPushButton('Set From File')
        # noinspection PyUnresolvedReferences
        set_button.clicked.connect(self.set_from_file)

        # the bottom frame
        self.lay = QtWidgets.QGridLayout()
        self.lay.addWidget(filter_label, 0, 0)
        self.lay.addWidget(filter_text, 0, 1, 1, 3)
        self.lay.addWidget(self.view, 1, 0, 1, 4)
        self.lay.addWidget(checkbox, 2, 0, 1, 2)
        self.lay.addWidget(step_label, 2, 2)
        self.lay.addWidget(self.stepbox, 2, 3)
        self.lay.addWidget(save_button, 3, 0, 1, 2)
        self.lay.addWidget(set_button, 3, 2, 1, 2)

        self.lay.setRowStretch(0, 0)
        self.lay.setRowStretch(1, 1)
        self.lay.setRowStretch(2, 0)
        self.lay.setRowStretch(3, 0)
        self.lay.setColumnStretch(0, 0)
        self.lay.setColumnStretch(1, 0)
        self.lay.setColumnStretch(2, 0)
        self.lay.setColumnStretch(3, 1)

        self.setLayout(self.lay)

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
