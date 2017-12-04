# -*- coding: utf-8 -*-

"""This module defines TitledForm.  A general user input form with title and load/save functionality.
"""

import os
from itertools import izip

import yaml
from PyQt4 import QtGui as QtGui
from PyQt4.QtCore import pyqtSlot, pyqtSignal

from .FileField import FileField
from .MetricSpinBox import MetricSpinBox
from .. import util


class TitledForm(QtGui.QGroupBox):
    """A general titled form with load/save utility.
    """

    committed = pyqtSignal()

    def __init__(self, name, conf_path, specs, font_size=11, buttons=False,
                 show_title=True):
        """Create a new Form for users to fill in the given parameters.

        Parameters
        ----------
        name : str
            name of this form.
        conf_path : str
            path to configuration directory.
        specs : list[tuple]
            list of parameter specifications.
        font_size : int
            font size of this group box.
        buttons : bool
            True to include Apply/Revert buttons.
        show_title : bool
            True to show title.
        """
        super(TitledForm, self).__init__()

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        if show_title:
            self.setTitle(name)

        self.form_name = name
        self.conf_fname = os.path.join(conf_path, '{}.yaml'.format(name))
        self.components = []

        self.values = {}
        if os.path.exists(self.conf_fname):
            with open(self.conf_fname, 'r') as f:
                self.values = yaml.load(f)
        else:
            self.values = {}

        # add components
        self.params = []
        for spec in specs:
            par = spec[0]
            spec = spec[1:]
            init_val = self.values.get(par, spec[1])
            self.values[par] = init_val
            if spec[0] == str:
                if len(spec) > 2 and spec[2] == 'file':
                    comp = FileField(init_val)
                elif len(spec) > 2 and spec[2] == 'directory':
                    comp = FileField(init_val, get_dir=True)
                else:
                    comp = QtGui.QLineEdit(init_val)
            elif spec[0] == int:
                comp = QtGui.QSpinBox()
                comp.setMinimum(spec[2])
                comp.setMaximum(spec[3])
                comp.setSingleStep(spec[4])
                comp.setValue(init_val)
            elif spec[0] == float:
                comp = MetricSpinBox(spec[2], spec[3], spec[4], spec[5])
                comp.setValue(init_val)
            elif spec[0] == bool:
                comp = QtGui.QCheckBox('')
                comp.setChecked(init_val)
            elif isinstance(spec[0], list):
                comp = QtGui.QComboBox()
                sel_idx = 0
                for idx, val in enumerate(spec[0]):
                    if val == init_val:
                        sel_idx = idx
                    comp.addItem(str(val), val)
                comp.setCurrentIndex(sel_idx)
            else:
                raise Exception('Unknown spec: {}'.format(spec))

            self.params.append(par)
            self.components.append(comp)

        labels = [par + ': ' for par in self.params]
        body = util.make_form(labels, self.components)

        lay = QtGui.QVBoxLayout()
        self.setLayout(lay)
        lay.addWidget(body)

        if buttons:
            apply_button = QtGui.QPushButton('Apply')
            revert_button = QtGui.QPushButton('Revert')
            apply_button.clicked.connect(self.submit)
            revert_button.clicked.connect(self.revert)

            bot_lay = QtGui.QHBoxLayout()
            bot_lay.addWidget(apply_button)
            bot_lay.addWidget(revert_button)
            bot_frame = QtGui.QFrame()
            bot_frame.setLayout(bot_lay)
            lay.addWidget(bot_frame)

    def get_form_values(self):
        # clear so old entries from init file will get flushed.
        self.values.clear()
        for par, comp in izip(self.params, self.components):
            if isinstance(comp, QtGui.QLineEdit):
                self.values[par] = comp.text()
            elif isinstance(comp, QtGui.QAbstractSpinBox):
                comp.interpretText()
                self.values[par] = comp.value()
            elif isinstance(comp, QtGui.QCheckBox):
                self.values[par] = comp.isChecked()
            elif isinstance(comp, QtGui.QComboBox):
                self.values[par] = comp.itemData(comp.currentIndex())
            elif isinstance(comp, FileField):
                self.values[par] = comp.text()
            else:
                raise Exception('Unknown component: {}'.format(comp))

        # save current values.
        dirname = os.path.dirname(self.conf_fname)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(self.conf_fname, 'w') as f:
            yaml.dump(self.values, f)

        return self.values

    @pyqtSlot()
    def submit(self):
        self.committed.emit()

    @pyqtSlot()
    def revert(self):
        for par, comp in izip(self.params, self.components):
            if isinstance(comp, QtGui.QLineEdit):
                comp.setText(self.values[par])
            elif isinstance(comp, QtGui.QSpinBox):
                comp.setValue(self.values[par])
            elif isinstance(comp, MetricSpinBox):
                comp.setValue(self.values[par])
            elif isinstance(comp, QtGui.QCheckBox):
                comp.setChecked(self.values[par])
            elif isinstance(comp, QtGui.QComboBox):
                for idx in xrange(comp.count()):
                    if comp.itemData(idx) == self.values[par]:
                        comp.setCurrentIndex(idx)
                        break
            elif isinstance(comp, FileField):
                comp.setText(self.values[par])
            else:
                raise Exception('Unknown component: {}'.format(comp))
