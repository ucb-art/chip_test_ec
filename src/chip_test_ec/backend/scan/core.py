# -*- coding: utf-8 -*-

"""This module defines Scan, a class for controlling a scan chain.."""

from typing import List, Optional, Callable

import os
import logging

import numpy as np

from ...base import LoggingBase

# type check imports
from ..fpga.base import FPGABase


class Scan(LoggingBase):
    """This class controls a scan chain using FPGA.

    Parameters
    ----------
    fpga : Optional[FPGABase]
        the fpga used to read and write the scan chain.  If None, this scan
        chain will run in fake scan mode.
    fname : str
        name of the scan chain file.
    pre_bytes : int
        number of extra prefix bytes read from FPGA.
    post_bytes : int
        number of extra suffix bytes read from FPGA.
    """

    def __init__(self, fpga: Optional[FPGABase], fname: str, pre_bytes: int=0, post_bytes: int=0) -> None:
        LoggingBase.__init__(self)

        self._fpga = fpga

        self._value = {}
        self._numbits = {}
        self._index = {}
        self._order = []
        self._callbacks = []
        self._read_pre_bytes = pre_bytes
        self._read_post_bytes = post_bytes
        self._pre_data = []
        self._post_data = []

        cur_idx = 0
        with open(fname, 'r') as f:
            for line in f:
                parts = line.split()
                name = parts[0]
                defval = int(parts[1])
                numbits = int(parts[2])

                self._numbits[name] = numbits
                self._value[name] = defval
                self._order.append(name)
                self._index[name] = cur_idx
                cur_idx += numbits

        self._nbits = cur_idx
        self._nbytes = -(-self._nbits // 8)

        self.write_twice()

    def set_from_file(self, fname: str) -> None:
        """Set the values in the scan chain to the values specified in the given file.

        Parameters
        ----------
        fname : str
            the file to read.
        """
        if not os.path.isfile(fname):
            self.log_msg('{0} is not a File'.format(fname))
            return

        with open(fname, 'r') as f:
            for line in f:
                parts = line.split()
                name = parts[0]
                defval = int(parts[1])
                self._value[name] = defval

        self.write_twice()

    def save_to_file(self, fname: str) -> None:
        """Save the current scan chain content to the given file.

        Parameters
        ----------
        fname : str
            the file to write.
        """
        with open(fname, 'w') as f:
            for name in self._order:
                f.write('{0}\t{1}\t{2}\n'.format(name, self._value[name], self._numbits[name]))

    def add_callback(self, fun: Callable[['Scan'], None]) -> None:
        """Adds a function which will be called with this Scan instance if the scan chain content changed.

        Parameters
        ----------
        fun : Callable[[Scan], None]
            the function to call if scan chain updated.
        """
        self._callbacks.append(fun)

    def get_scan_names(self) -> List[str]:
        """Returns a list of scan names in the order you scan in.

        Returns
        -------
        scan_list : List[str]
            a list of scan names.
        """
        return self._order

    def set(self, name: str, value: int) -> None:
        """Sets the given scan bus value.

        Parameters
        ----------
        name : str
            the scan bus to set.
        value : int
            the new value
        """
        self.log_msg('Scan: setting {} to {}'.format(name, value))
        self._value[name] = value

    def get_numbits(self, name: str) -> int:
        """Returns the number of bits in the given scan bus.

        Parameters
        ----------
        name : str
            name of the scan bus.

        Returns
        -------
        n : int
            number of bits in the given scan bus.
        """
        return self._numbits[name]

    def get_value(self, name: str) -> int:
        """Returns the current value of the given scan bus.

        Parameters
        ----------
        name : str
            name of the scan bus

        Returns
        -------
        val : int
            value of the scan bus
        """
        return self._value[name]

    def get_pre_bytes_data(self) -> List[int]:
        """Returns the last read pre-scan chain data.

        Returns
        -------
        val_list : List[int]
            list of pre-scan byte data.
        """
        return self._pre_data

    def get_post_bytes_data(self) -> List[int]:
        """Returns the last read post-scan chain data.

        Returns
        -------
        val_list : List[int]
            list of post-scan byte data.
        """
        return self._post_data

    def to_byte_array(self) -> List[int]:
        """Convert the content of this Scan object into an array of 8 bit integers.

        Returns
        -------
        arr : List[int]
            a list of byte values.
        """
        bstr = ''
        for name in self._order:
            bstr += np.binary_repr(self._value[name], self._numbits[name])

        return [int(bstr[i:i + 8], 2) for i in range(0, len(bstr), 8)]

    def _from_byte_array(self, barr: List[int]) -> None:
        """Update the content of this Scan object from the given byte array.

        Parameters
        ----------
        barr : List[int]
            a list of byte values to update.
        """
        if len(barr) != self._nbytes:
            msg = 'bytearray length {0} != {1}.'.format(len(barr), self._nbytes)
            self.log_msg(msg, level=logging.ERROR)
            raise Exception(msg)

        bstr = ''
        for val in barr:
            bstr += np.binary_repr(val, 8)
        for name in self._order:
            idx = self._index[name]
            n = self._numbits[name]
            old_val = self._value[name]
            new_val = int(bstr[idx:idx + n], 2)
            if old_val != new_val:
                self.log_msg('scan bus {} changed from {} to {}'.format(name, old_val, new_val))
                self._value[name] = new_val

    def write_twice(self) -> None:
        """Write the content of this instance to the scan chain twice,
        then update the content with what you read out.
        """

        if self._fpga is not None:
            # make integer array to write to fpga
            arr = [0x10]
            barr = self.to_byte_array()
            nbytes = len(barr)
            arr.extend(barr)

            # write twice
            self._fpga.write_ints(arr)
            self._fpga.read_ints(nbytes + self._read_pre_bytes + self._read_post_bytes)
            self._fpga.write_ints(arr)
            scan_out = self._fpga.read_ints(nbytes + self._read_pre_bytes + self._read_post_bytes)

            new_scan = scan_out[self._read_pre_bytes:len(scan_out) - self._read_post_bytes]
            self._pre_data = scan_out[:self._read_pre_bytes]
            self._post_data = scan_out[len(scan_out) - self._read_post_bytes:]

            # update values
            self._from_byte_array(new_scan)
        else:
            # update pre/post data with fake data
            self._pre_data = [0] * self._read_pre_bytes
            self._post_data = [0] * self._read_post_bytes

        for fun in self._callbacks:
            fun()
