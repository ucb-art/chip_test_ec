# -*- coding: utf-8 -*-

"""This module defines a frame that provides scan chain editing functionality.
"""

import os

from PyQt5 import QtWidgets, QtCore, QtGui

from ...backend.core import Controller
from ..base.fields import BigIntSpinbox
from ..base.displays import LogWidget
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
        nmax = (1 << nbits) - 1

        editor = BigIntSpinbox(parent)
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
    ctrl : Controller
        the controller object.
    logger : LogWidget
        the LogWidget use to display messages.
    font_size : int
        the font size for this frame.
    max_step : int
        maximum scan bus spinbox step size.
    """

    scanChainChanged = QtCore.pyqtSignal(str)

    def __init__(self, ctrl: Controller, logger: LogWidget, font_size: int=11, max_step: int=8192, parent=None):
        super(ScanFrame, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.ctrl = ctrl
        self.chain_names = ctrl.fpga.get_scan_chain_names()
        self.delegate = ScanDelegate(parent=self)
        self.logger = logger
        # noinspection PyUnresolvedReferences
        ctrl.fpga.add_callback(self.scanChainChanged.emit)
        # noinspection PyUnresolvedReferences
        self.scanChainChanged[str].connect(self._update_models)

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        # create scan models and configure chain selection box
        self.models = []
        self.model_idx = 0
        chain_sel = QtWidgets.QComboBox(parent=self)
        sel_label = QtWidgets.QLabel('&Scan Chain:', parent=self)
        sel_label.setBuddy(chain_sel)
        for chain_name in self.chain_names:
            self.models.append(ScanItemModel(ctrl, chain_name, parent=self))
            chain_sel.addItem(chain_name, chain_name)
        chain_sel.setCurrentIndex(0)
        # noinspection PyUnresolvedReferences
        chain_sel.currentIndexChanged[int].connect(self.change_model)

        # configure filter
        self.proxy = ScanSortFilterProxyModel(parent=self)
        self.proxy.setSourceModel(self.models[0])
        self.proxy.setFilterKeyColumn(0)
        filter_text = QtWidgets.QLineEdit(parent=self)
        # noinspection PyUnresolvedReferences
        filter_text.textChanged[str].connect(self.proxy.update_filter)
        filter_label = QtWidgets.QLabel('&Filter:', parent=self)
        filter_label.setBuddy(filter_text)

        # configure tree view
        self.view = QtWidgets.QTreeView(parent=self)
        self.view.setItemDelegate(self.delegate)
        self.view.setSortingEnabled(True)
        self.view.header().setSortIndicatorShown(True)
        self.view.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.view.header().setSectionsClickable(True)
        self.view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.view.header().setStretchLastSection(False)
        self.view.setModel(self.proxy)

        # configure step box, sync checkbox, and buttons
        checkbox = QtWidgets.QCheckBox('Disable sync', parent=self)
        # noinspection PyUnresolvedReferences
        checkbox.stateChanged[int].connect(self.set_model_sync_flag)
        self.stepbox = QtWidgets.QSpinBox(parent=self)
        self.stepbox.setMaximum(max_step)
        self.stepbox.setValue(1)
        # noinspection PyUnresolvedReferences
        self.stepbox.valueChanged[int].connect(self.delegate.set_step_size)
        step_label = QtWidgets.QLabel('&Step Size:', parent=self)
        step_label.setBuddy(self.stepbox)
        save_button = QtWidgets.QPushButton('Save To File...', parent=self)
        # noinspection PyUnresolvedReferences
        save_button.clicked.connect(self.save_to_file)
        set_button = QtWidgets.QPushButton('Set From File', parent=self)
        # noinspection PyUnresolvedReferences
        set_button.clicked.connect(self.set_from_file)

        # populate frame
        self.lay = QtWidgets.QGridLayout(self)
        self.lay.addWidget(sel_label, 0, 0)
        self.lay.addWidget(chain_sel, 0, 1, 1, 2)
        self.lay.addWidget(filter_label, 1, 0)
        self.lay.addWidget(filter_text, 1, 1, 1, 3)
        self.lay.addWidget(self.view, 2, 0, 1, 4)
        self.lay.addWidget(checkbox, 3, 0, 1, 2)
        self.lay.addWidget(step_label, 3, 2)
        self.lay.addWidget(self.stepbox, 3, 3)
        self.lay.addWidget(save_button, 4, 0, 1, 2)
        self.lay.addWidget(set_button, 4, 2, 1, 2)

        self.lay.setRowStretch(0, 0)
        self.lay.setRowStretch(1, 0)
        self.lay.setRowStretch(2, 1)
        self.lay.setRowStretch(3, 0)
        self.lay.setRowStretch(4, 0)
        self.lay.setColumnStretch(0, 0)
        self.lay.setColumnStretch(1, 0)
        self.lay.setColumnStretch(2, 0)
        self.lay.setColumnStretch(3, 1)

    @QtCore.pyqtSlot(int)
    def change_model(self, idx):
        self.model_idx = idx
        self.proxy.setSourceModel(self.models[idx])

    @QtCore.pyqtSlot(int)
    def set_model_sync_flag(self, state):
        self.models[self.model_idx].set_sync_flag(state)

    @QtCore.pyqtSlot(str)
    def _update_models(self, chain_name):
        for name, model in zip(self.chain_names, self.models):
            if name == chain_name:
                model.update_from_scan()

    @QtCore.pyqtSlot()
    def set_from_file(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load File', cur_dir, 'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Loading from file: %s' % fname)
            self.ctrl.fpga.set_scan_from_file(fname)

    @QtCore.pyqtSlot()
    def save_to_file(self):
        cur_dir = os.getcwd()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Select File', cur_dir, 'YAML files (*.yaml *.yml)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if fname:
            self.logger.println('Saving to file: %s' % fname)
            self.ctrl.fpga.save_scan_to_file(fname)
