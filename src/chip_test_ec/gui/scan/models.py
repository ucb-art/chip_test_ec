# -*- coding: utf-8 -*-

"""This module defines various model classes for displaying scan chain hierarchy."""

from PyQt5 import QtCore, QtGui

# type check imports
from ...backend.fpga.base import FPGABase


class ScanItem(QtGui.QStandardItem):
    """A subclass of QStandardItem that represents a scan value field.

    This item has an integer edit role and keep tracks of how many bits this scan bit have in UserRole.
    """
    def __init__(self, value, nbits):
        super(ScanItem, self).__init__(str(value))
        self.value = value
        self.setData(nbits, role=QtCore.Qt.UserRole)

    def data(self, role=None, *args, **kwargs):
        if role == QtCore.Qt.EditRole:
            return self.value
        # noinspection PyArgumentList
        return super(ScanItem, self).data(role, *args, **kwargs)

    def setData(self, val, role=None, *args, **kwargs):
        if role == QtCore.Qt.EditRole:
            self.value = val
            self.setText(str(val))
            self.emitDataChanged()
        else:
            # noinspection PyArgumentList
            super(ScanItem, self).setData(val, role, *args, **kwargs)


class ScanItemModel(QtGui.QStandardItemModel):
    """The model class representing an editable scan chain.

    This model overwrites QStandardItemModel such that setting scan values will update the scan chain.
    """

    scanChainChanged = QtCore.pyqtSignal()

    def __init__(self, fpga: FPGABase, chain_name: str):
        """Create a new ScanItemModel based on the given scan control object.

        Parameters
        ----------
        fpga : FPGABase
            the fpga object used to control scan chains.
        chain_name : str
            the scan chain this model represents.
        """
        super(ScanItemModel, self).__init__()
        self.fpga = fpga
        self.chain_name = chain_name
        self.item_dict = self._build_model()
        self.sync_flag = True
        self.setHorizontalHeaderLabels(['Scan Name', 'Value'])
        # noinspection PyUnresolvedReferences
        fpga.add_callback(self.scanChainChanged.emit)
        # noinspection PyUnresolvedReferences
        self.scanChainChanged.connect(self._update)

    def set_sync_flag(self, state: int):
        """Change whether the GUI display syncs to scan chain in real time.

        Parameters
        ----------
        state : int
            the QT state indicator.  If checked, disable sync.
        """
        if state == QtCore.Qt.Checked:
            self.sync_flag = False
        else:
            self.sync_flag = True
            self._update_scan_from_model()

    def _build_model(self):
        """Builds this model from the Scan instance.

        Returns
        -------
        item_dict: dict[str, QtGui.QStandardItem]
            the name-to-QStandardItem dictionary.
        """

        item_dict = {}
        for name in self.fpga.get_scan_names(self.chain_name):
            nbits = self.fpga.get_scan_length(self.chain_name, name)
            defval = self.fpga.get_scan(self.chain_name, name)
            parts = name.split('.')
            parent = self.invisibleRootItem()
            for idx in range(len(parts)):
                item_name = '.'.join(parts[:idx+1])
                if item_name in item_dict:
                    parent = item_dict[item_name]
                else:
                    temp = QtGui.QStandardItem(parts[idx])
                    temp.setEditable(False)
                    if idx == len(parts) - 1:
                        val = ScanItem(defval, nbits)
                    else:
                        val = QtGui.QStandardItem('')
                        val.setEditable(False)
                    parent.appendRow([temp, val])
                    parent = temp
                    item_dict[item_name] = temp

        return item_dict

    def _update_scan_from_model(self):
        for name in self.fpga.get_scan_names(self.chain_name):
            old_val = self.fpga.get_scan(self.chain_name, name)
            item = self.item_dict[name]
            idx = self.indexFromItem(item)
            val_idx = idx.sibling(idx.row(), 1)
            new_val = self.data(val_idx, QtCore.Qt.EditRole)
            if old_val != new_val:
                self.fpga.set_scan(self.chain_name, name, new_val)
        self.fpga.update_scan(self.chain_name)

    @QtCore.pyqtSlot()
    def _update(self):
        """Update this model to have the same content as the scan control.
        """
        for name in self.fpga.get_scan_names(self.chain_name):
            val = self.fpga.get_scan(self.chain_name, name)
            item = self.item_dict[name]
            idx = self.indexFromItem(item)
            val_idx = idx.sibling(idx.row(), 1)
            old_val = self.data(val_idx, QtCore.Qt.EditRole)
            if old_val != val:
                super(ScanItemModel, self).setData(val_idx, val, QtCore.Qt.EditRole)

    def setData(self, index, value, role=None):
        if not self.sync_flag:
            return super(ScanItemModel, self).setData(index, value, role)
        else:
            if role == QtCore.Qt.EditRole:
                # set corresponding scan chain, then shift.
                name_idx = index.sibling(index.row(), 0)
                name = self.itemFromIndex(name_idx).text()
                # get full scan bus name
                while name_idx.parent().isValid():
                    name_idx = name_idx.parent()
                    name = self.itemFromIndex(name_idx).text() + '.' + name
                self.fpga.set_scan(self.chain_name, name, value)
                self.fpga.update_scan(self.chain_name)
                return True
            else:
                return super(ScanItemModel, self).setData(index, value, role)


class ScanSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """A subclass of QSortFilterProxyModel that works on full scan bus name.
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
        for r in range(max_row):
            if self.filterAcceptsRow(r, cur_idx):
                return True
        return False

    @QtCore.pyqtSlot(str)
    def update_filter(self, text):
        new_exp = QtCore.QRegExp(text)
        new_exp.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setFilterRegExp(new_exp)
