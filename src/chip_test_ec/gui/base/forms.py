# -*- coding: utf-8 -*-

"""This module defines GUI components for creating forms.
"""

from typing import Sequence, Dict, Any

import os

import yaml
from PyQt5 import QtGui, QtWidgets, QtCore

from .fields import FileField, MetricSpinBox


def make_form(name_list: Sequence[str], widget_list: Sequence[QtWidgets.QWidget]) -> QtWidgets.QFrame:
    """Create a QFrame containing labels to the left of the widgets.

    Parameters
    ----------
    name_list : Sequence[str]
        names of the widgets.
    widget_list : Sequence[QtWidgets.QWidget]
        the widgets.

    Returns
    -------
    frame : QtWidgets.QFrame
        a QFrame containing labels and widgets.
    """
    frame = QtWidgets.QFrame()
    lay = QtWidgets.QFormLayout()
    frame.setLayout(lay)
    for name, widget in zip(name_list, widget_list):
        lay.addRow('&%s:' % name, widget)
    return frame


class TitledForm(QtWidgets.QGroupBox):
    """A general titled form with load/save utility.

    Parameters
    ----------
    name : str
        the form name.
    conf_path : str
        path to configuration directory.
    specs : Dict[str, Any]
        list of parameter specifications.
    font_size : int
        font size of this component.
    buttons : bool
        True to include Apply/Revert buttons.
    show_title : bool
        True to show title.
    """

    committed = QtCore.pyqtSignal()

    def __init__(self, name: str, conf_path: str, specs: Dict[str, Any],
                 font_size: int=11, buttons: bool=False, show_title: bool=True):
        super(TitledForm, self).__init__()

        # set font
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        if show_title:
            self.setTitle(name)

        self._form_name = name
        self.conf_fname = os.path.join(conf_path, '{}.yaml'.format(name))

        self.values = {}
        if os.path.exists(self.conf_fname):
            with open(self.conf_fname, 'r') as f:
                self.values = yaml.load(f)
        else:
            self.values = {}

        # add components
        self.params = []
        self.components = []
        labels = []
        for par_name in specs['order']:
            par_info = specs[par_name]
            par_type = par_info['type']
            init_val = self.values.get(par_name, par_info['default'])
            self.values[par_name] = init_val
            if par_type == 'directory':
                comp = FileField(init_val, get_dir=True)
            elif par_type == 'file':
                comp = FileField(init_val, get_dir=False)
            elif par_type == 'str':
                comp = QtWidgets.QLineEdit(init_val)
            elif par_type == 'int':
                comp = QtWidgets.QSpinBox()
                comp.setMinimum(par_info['min'])
                comp.setMaximum(par_info['max'])
                comp.setSingleStep(par_info.get('step', 1))
                comp.setValue(init_val)
            elif par_type == 'float':
                comp = MetricSpinBox(par_info['min'], par_info['max'], par_info['step'], par_info['precision'])
                comp.setValue(init_val)
            elif par_type == 'bool':
                comp = QtWidgets.QCheckBox('')
                comp.setChecked(init_val)
            elif par_type == 'select':
                comp = QtWidgets.QComboBox()
                sel_idx = 0
                for idx, val in enumerate(par_info['values']):
                    if val == init_val:
                        sel_idx = idx
                    comp.addItem(str(val), val)
                comp.setCurrentIndex(sel_idx)
            else:
                raise Exception('Unknown parameter information: {}'.format(par_info))

            self.params.append(par_name)
            self.components.append(comp)
            labels.append(par_name)

        body = make_form(labels, self.components)

        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)
        lay.addWidget(body)

        if buttons:
            apply_button = QtWidgets.QPushButton('Apply')
            revert_button = QtWidgets.QPushButton('Revert')
            # noinspection PyUnresolvedReferences
            apply_button.clicked.connect(self.submit)
            # noinspection PyUnresolvedReferences
            revert_button.clicked.connect(self.revert)

            bot_lay = QtWidgets.QHBoxLayout()
            bot_lay.addWidget(apply_button)
            bot_lay.addWidget(revert_button)
            bot_frame = QtWidgets.QFrame()
            bot_frame.setLayout(bot_lay)
            lay.addWidget(bot_frame)

    @property
    def name(self):
        return self._form_name

    def get_form_values(self) -> Dict[str, Any]:
        """Returns the form values as a dictionary."""
        # clear so old entries from init file will get flushed.
        self.values.clear()
        for par, comp in zip(self.params, self.components):
            if isinstance(comp, QtWidgets.QLineEdit):
                self.values[par] = comp.text()
            elif isinstance(comp, QtWidgets.QAbstractSpinBox):
                comp.interpretText()
                self.values[par] = comp.value()
            elif isinstance(comp, QtWidgets.QCheckBox):
                self.values[par] = comp.isChecked()
            elif isinstance(comp, QtWidgets.QComboBox):
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

        return self.values.copy()

    @QtCore.pyqtSlot()
    def submit(self) -> None:
        # noinspection PyUnresolvedReferences
        self.committed.emit()

    @QtCore.pyqtSlot()
    def revert(self) -> None:
        for par, comp in zip(self.params, self.components):
            if isinstance(comp, QtWidgets.QLineEdit):
                comp.setText(self.values[par])
            elif isinstance(comp, QtWidgets.QSpinBox):
                comp.setValue(self.values[par])
            elif isinstance(comp, MetricSpinBox):
                comp.setValue(self.values[par])
            elif isinstance(comp, QtWidgets.QCheckBox):
                comp.setChecked(self.values[par])
            elif isinstance(comp, QtWidgets.QComboBox):
                for idx in range(comp.count()):
                    if comp.itemData(idx) == self.values[par]:
                        comp.setCurrentIndex(idx)
                        break
            elif isinstance(comp, FileField):
                comp.setText(self.values[par])
            else:
                raise Exception('Unknown component: {}'.format(comp))
