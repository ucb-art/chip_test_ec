# -*- coding: utf-8 -*-

"""This module defines ScanItemModel, a subclass of QAbstractItemModel used for
displaying scan chain hierarchy."""

import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui
from PyQt4.QtCore import pyqtSignal, pyqtSlot


class ScanItem(QtGui.QStandardItem):
    """A subclass of QStandardItem that represents a scan value field, which has an integer edit role
    and keep tracks of how many bits this scan bit have in UserRole.
    """
    def __init__(self, value, nbits):
        super(ScanItem, self).__init__(str(value))
        self.value = value
        self.setData(nbits, role=QtCore.Qt.UserRole)

    def data(self, role=None, *args, **kwargs):
        if role == QtCore.Qt.EditRole:
            return self.value
        return super(ScanItem, self).data(role, *args, **kwargs)

    def setData(self, val, role=None, *args, **kwargs):
        if role == QtCore.Qt.EditRole:
            self.value = val
            self.setText(str(val))
            self.emitDataChanged()
        else:
            super(ScanItem, self).setData(val, role, *args, **kwargs)


class ScanItemModel(QtGui.QStandardItemModel):
    """This model overwrites QStandardItemModel such that setting scan values
    will update the scan chain.

    """

    scanChainChanged = pyqtSignal()

    def __init__(self, ctrl):
        """Create a new ScanItemModel based on the given scan control object.

        Parameters
        ----------
        ctrl : scan.Scan
            the scan chain data structure object.
        """
        super(ScanItemModel, self).__init__()
        self.ctrl = ctrl
        self.item_dict = self._build_model()
        self.sync_flag = True
        self.setHorizontalHeaderLabels(['Scan Name', 'Value'])
        ctrl.add_listener(self)
        self.scanChainChanged.connect(self._update)

    def setSyncFlag(self, state):
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
            self._updateScanFromModel()

    def scanChanged(self):
        """This method is called whenever the scan chain changed.
        """
        self.scanChainChanged.emit()

    def _build_model(self):
        """Builds this model from the Scan instance.

        Returns
        -------
        item_dict: dict[str, QtGui.QStandardItem]
            the name-to-QStandardItem dictionary.
        """

        item_dict = {}
        for name in self.ctrl.get_scan_names():
            nbits = self.ctrl.get_numbits(name)
            defval = self.ctrl.get_value(name)
            parts = name.split('.')
            parent = self.invisibleRootItem()
            for idx in xrange(len(parts)):
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

    def _updateScanFromModel(self):
        for name, old_val in self.ctrl.value.iteritems():
            item = self.item_dict[name]
            idx = self.indexFromItem(item)
            val_idx = idx.sibling(idx.row(), 1)
            new_val = self.data(val_idx, QtCore.Qt.EditRole)
            if old_val != new_val:
                self.ctrl.set(name, new_val)
        self.ctrl.write_twice()

    @pyqtSlot()
    def _update(self):
        """Update this model to have the same content as the scan control.
        """
        # print "updating"
        for name, val in self.ctrl.value.iteritems():
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
                self.ctrl.set(name, value)
                self.ctrl.write_twice()
                return True
            else:
                return super(ScanItemModel, self).setData(index, value, role)

    def setFromFile(self, fname):
        self.ctrl.set_from_file(fname)

    def saveToFile(self, fname):
        self.ctrl.save_to_file(fname)
