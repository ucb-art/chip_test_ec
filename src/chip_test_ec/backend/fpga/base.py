# -*- coding: utf-8 -*-

"""This module defines various classes for controlling FPGAs.

The FPGABase class is the base class for all FPGA controllers.

The FPGASerial class is a class that controls an FPGA using a serial port.
It can be used to control Xilinx GTX
"""

from typing import List, Callable, Tuple

import os
import abc
import array

import yaml

from ...base import LoggingBase


class FPGABase(LoggingBase, metaclass=abc.ABCMeta):
    """The base class that represents all FPGAs.

    This class defines methods that all FPGA controller have to implement.

    The scan chain definition file is a simple text file, with the following format:

    1. The first line contains two integers separated by space.  The first integer
       is the number of chains, the second integer is the address length.
    2. After the first line, the scan chain file contains chain definitions of each
       chain.
    3. For a chain definition, the first line contains three values separated by
       space.  The first value is the chain name, the second value is the chain
       address, the third value is the number of bits in this chain.  After that,
       the chain definition contains scan bus definitions for each scan bus in this
       chain, MSB first and LSB last.
    4. A scan bus definition is a single line with 2-4 values.  The first value is
       scan bus name, and the second value is the number of bits in the scan bus.
       If exists, the third value is the default scan bus value (defaults to 0).
       If exists, the fourth value is 0 if this scan bus should be skipped when
       checking for scan chain correctness, 1 otherwise. Note that Scan bus names
       must be unique in a chain.

    Parameters
    ----------
    scan_file : str
        scan chain file name.
    fake_scan : bool
        If True, then will not actually do the scan procedure.  This is useful for
        debugging.
    """
    def __init__(self, scan_file: str, fake_scan: bool=False) -> None:
        LoggingBase.__init__(self)

        self._chain_info = {}
        self._chain_value = {}
        self._chain_order = {}
        self._chain_check = {}
        self._chain_blen = {}
        self._callbacks = []
        self._addr_len = 1
        self._fake_scan = fake_scan
        self._chain_names = None

        # parse scan chain file
        with open(scan_file, 'r') as f:
            lines = f.readlines()
            parts = lines[0].split()
            num_chain = int(parts[0])
            self._addr_len = int(parts[1])
            line_idx = 1
            for chain_idx in range(num_chain):
                parts = lines[line_idx].split()
                chain_name = parts[0]
                chain_addr = int(parts[1])
                chain_len = int(parts[2])
                line_idx += 1
                chain_order = []
                chain_value = {}
                chain_blen = {}
                chain_check = {}
                chain_nbits = 0
                for bit_idx in range(chain_len):
                    parts = lines[line_idx].split()
                    bit_name = parts[0]
                    bit_len = int(parts[1])
                    bit_val = 0 if len(parts) < 3 else int(parts[2])
                    bit_check = True if len(parts) < 4 else bool(int(parts[3]))

                    chain_order.append(bit_name)
                    chain_value[bit_name] = bit_val
                    chain_blen[bit_name] = bit_len
                    chain_check[bit_name] = bit_check
                    line_idx += 1
                    chain_nbits += bit_len

                self._chain_info[chain_name] = (chain_addr, chain_nbits)
                self._chain_value[chain_name] = chain_value
                self._chain_order[chain_name] = chain_order
                self._chain_blen[chain_name] = chain_blen
                self._chain_check[chain_name] = chain_check

        # get chain names, sorted by address
        chain_sort = [(addr, name) for name, (addr, _) in self._chain_info.items()]
        self._chain_names = [item[1] for item in sorted(chain_sort)]

    @abc.abstractmethod
    def close(self) -> None:
        """Close the FPGA controller, free up resources.."""
        pass

    @abc.abstractmethod
    def scan_in_and_read_out(self, chain_name: str, value: List[int], numbits: List[int]) -> List[int]:
        """Scan in the given chain and return the content after scan.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        value : List[int]
            the values to scan in.  Index 0 is the MSB scan bus.
        numbits : List[int]
            number of bits of each scan bus.  Index 0 is the MSB scan bus.

        Returns
        -------
        output : List[int]
            the chain values after the scan in procedure.  Index 0 is the MSB scan bus.
        """
        return value

    @property
    def is_fake_scan(self) -> bool:
        return self._fake_scan

    @property
    def addr_len(self) -> int:
        return self._addr_len

    def update_scan(self, chain_name: str, check: bool=False) -> None:
        """Scan in the given chain, scan out the resulting data, then update

        This method sets the given chain to stored data, then read out that
        data shifted in and update the stored data values.

        Parameters
        ----------
        chain_name : str
            the chain to update.
        check : bool
            if True, will check if the updated data is the same as the data shifted
            in.  Raise an error is this is not the case.
        """
        scan_values = self._chain_value[chain_name]
        scan_blen = self._chain_blen[chain_name]
        scan_names = self.get_scan_names(chain_name)

        value = [scan_values[bus_name] for bus_name in scan_names]
        numbits = [scan_blen[bus_name] for bus_name in scan_names]
        output = value if self.is_fake_scan else self.scan_in_and_read_out(chain_name, value, numbits)

        if len(value) != len(output):
            raise ValueError('Scan output length different than scan input.')
        if check:
            scan_check = self._chain_check[chain_name]
            for name, val_in, val_out in zip(scan_names, value, output):
                if scan_check[name] and val_in != val_out:
                    msg = 'Scan check failed: %s/%s = %d != %d' % (chain_name, name, val_out, val_in)
                    raise ValueError(msg)

        for name, val_in, val_out in zip(scan_names, value, output):
            scan_values[name] = val_out

        for fun in self._callbacks:
            fun()

    def set_scan_from_file(self, fname: str) -> None:
        """Set the values in the scan chain to the values specified in the given file.

        Parameters
        ----------
        fname : str
            the file to read.
        """
        if not os.path.isfile(fname):
            raise ValueError('%s is not a file.' % fname)

        with open(fname, 'r') as f:
            scan_dict = yaml.load(f)

        for chain_name, chain_values in scan_dict.items():
            self._chain_value[chain_name].update(chain_values)
            self.update_scan(chain_name)

    def save_scan_to_file(self, fname: str) -> None:
        """Save the current scan chain content to the given file.

        Parameters
        ----------
        fname : str
            the file to write.
        """
        with open(fname, 'w') as f:
            yaml.dump(self._chain_value, f)

    def add_callback(self, fun: Callable[[], None]) -> None:
        """Adds a function which will be called if the scan chain content changed.

        Parameters
        ----------
        fun : Callable[[], None]
            the function to call if scan chain updated.
        """
        self._callbacks.append(fun)

    def get_scan_chain_names(self) -> List[str]:
        """Returns a list of scan chain names.

        Returns
        -------
        chain_names : List[str]
            a list of scan chain names.
        """
        return self._chain_names

    def get_scan_chain_info(self, chain_name: str) -> Tuple[int, int]:
        """Returns information about the given scan chain.

        Parameters
        ----------
        chain_name : str
            the scan chain name.

        Returns
        -------
        addr : int
            the chain address.
        clen : int
            the chain length.
        """
        return self._chain_info[chain_name]

    def get_scan_names(self, chain_name: str) -> List[str]:
        """Returns a list of scan bus names.  Index 0 is the MSB scan bus.

        Returns
        -------
        scan_list : List[str]
            a list of scan bus names.
        """
        return self._chain_order[chain_name]

    def set_scan(self, chain_name: str, bus_name: str, value: int) -> None:
        """Sets the given scan bus value.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        bus_name : str
            the scan bus to set.
        value : int
            the new value.
        """
        self.log_msg('Scan: setting {}/{} to {}'.format(chain_name, bus_name, value))
        self._chain_value[chain_name][bus_name] = value

    def get_scan(self, chain_name: str, bus_name: str) -> int:
        """Returns given scan bus value.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        bus_name : str
            the scan bus to set.

        Returns
        -------
        value : int
            the scan bus value.
        """
        return self._chain_value[chain_name][bus_name]

    def get_scan_length(self, chain_name: str, bus_name: str) -> int:
        """Returns the number of bits in the given scan bus.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        bus_name : str
            the scan bus to set.

        Returns
        -------
        n : int
            number of bits in the given scan bus.
        """
        return self._chain_blen[chain_name][bus_name]
