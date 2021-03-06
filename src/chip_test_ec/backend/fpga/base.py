# -*- coding: utf-8 -*-

"""This module defines various classes for controlling FPGAs.

The FPGABase class is the base class for all FPGA controllers.

The FPGASerial class is a class that controls an FPGA using a serial port.
It can be used to control Xilinx GTX
"""

from typing import List, Tuple, Callable, Dict, Any, Optional

import os
import abc
import logging

import yaml

from ...base import LoggingBase


class FPGABase(LoggingBase, metaclass=abc.ABCMeta):
    """The base class that represents all FPGAs.

    This class defines methods that all FPGA controller have to implement.

    The scan chain definition file uses the YAML format so it is easy to support
    various custom scan chain features.  The format is described below:

    1. the file has at least the following 2 attributes:

       nbits_addr : number of address bits.
       chains : a dictionary from chain name to scan chains.  Each scan chain is
       represented by a dictionary.

    2. Each scan chain has at least the following 2 attributes:

       addr : the address of this chain.
       content : a list of all the scan buses in this chain.  The MSB scan bus
       is listed first (corresponds to index 0).  Each scan bus is represented by
       a dictionary.

       scan chain cannot contain the attribute named 'nbits'.  This is calculated
       automatically.

    3. Each scan has at least the following 3 attributes:

       name : name of the scan bus.
       nbits : number of bits in this scan bus.
       value : default value of this bus.  If not given, defaults to 0.

    Parameters
    ----------
    scan_file : str
        scan chain file name.
    fake_scan : bool
        If True, then will not actually do the scan procedure.  This is useful for
        debugging.
    check_scan : bool
        True to check every scan operation.
    """
    def __init__(self, scan_file: str, fake_scan: bool=False, check_scan: bool=False) -> None:
        LoggingBase.__init__(self)

        self._scan_config = None
        self._chain_value = {}
        self._chain_order = {}
        self._chain_blen = {}
        self._callbacks = []
        self._fake_scan = fake_scan
        self._check_scan = check_scan
        self._chain_names = None

        # parse scan chain file
        with open(scan_file, 'r') as f:
            self._scan_config = yaml.load(f)

        chain_sort = []
        for chain_name, chain_info in self._scan_config['chains'].items():
            chain_sort.append((chain_info['addr'], chain_name))
            chain_value = {}
            chain_order = []
            chain_blen = {}
            chain_nbits = 0
            for bus_info in chain_info['content']:
                bus_name = bus_info['name']
                bus_nbits = bus_info['nbits']
                chain_nbits += bus_nbits
                chain_order.append(bus_name)
                chain_value[bus_name] = bus_info.get('value', 0)
                chain_blen[bus_name] = bus_nbits

            if 'nbits' in chain_info:
                raise ValueError('chain %s contains reserved attribute nbits.')
            chain_info['nbits'] = chain_nbits

            self._chain_value[chain_name] = chain_value
            self._chain_order[chain_name] = chain_order
            self._chain_blen[chain_name] = chain_blen

        self._chain_names = [item[1] for item in sorted(chain_sort)]

    @abc.abstractmethod
    def close(self) -> None:
        """Close the FPGA controller, free up resources.."""
        pass

    @abc.abstractmethod
    def update_pins(self, chain_info: Dict[str, Any], value: List[int], numbits: List[int]) -> List[int]:
        """Read/Write to IO pins.

        Parameters
        ----------
        chain_info : Dict[str, Any]
            the scan chain information dictionary.
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

    @abc.abstractmethod
    def is_scan_read_only(self, chain_name: str, bus_name: str) -> bool:
        """Returns True if the given scan bus is read only, False otherwise.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        bus_name : str
            the scan bus name.

        Returns
        -------
        is_read_only : bool
            True if the given scan bus is read only.
        """
        return False

    @abc.abstractmethod
    def scan_in_and_read_out(self, chain_info: Dict[str, Any], value: List[int], numbits: List[int]) -> List[int]:
        """Scan in the given chain and return the content after scan.

        Parameters
        ----------
        chain_info : Dict[str, Any]
            the scan chain information dictionary.
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

    @abc.abstractmethod
    def send_i2c_cmds(self,
                      i2c_name: str,
                      cmd_list: List[Tuple[int, List[int], int]],
                      ) -> List[Optional[List[int]]]:
        """Issue the given I2C commands with the FPGA.

        Parameters
        ----------
        i2c_name : str
            I2C controller name.
        cmd_list : List[Tuple[int, List[int], int]]
            List of I2C commands to send.

            Each command is a tuple of slave address, list of data bytes to
            send, and number of bytes to read.  For a write command, the
            third argument is 0, For a read command, the third argument is
            positive, and the second argument is ignored.

        Returns
        -------
        values : List[Optional[List[int]]]
            List of data bytes returned from slave for each command.  For a
            write command, the corresponding return value will be an empty
            list.  If a command fails, the return value for that command and
            all subsequent commands will be None.
        """
        return [None] * len(cmd_list)

    @abc.abstractmethod
    def set_voltage(self, sup_name: str, val: float) -> None:
        """Sets the voltage of the given supply.

        Parameters
        ----------
        sup_name : str
            the supply name.
        val : float
            the supply voltage, in volts.

        Raises
        ------
        KeyError
            If the given supply is not defined.
        """
        raise NotImplementedError('Not implemented.')

    @abc.abstractmethod
    def read_current(self, sup_name: str) -> float:
        """Returns the current reading for the given supply.

        Parameter
        ---------
        sup_name : str
            the supply name.

        Returns
        -------
        current : float
            the supply current, in Amperes.

        Raises
        ------
        KeyError
            If the given supply is not defined.
        """
        raise NotImplementedError('Not implemented')

    @property
    def is_fake_scan(self) -> bool:
        return self._fake_scan

    @property
    def addr_len(self) -> int:
        return self._scan_config['nbits_addr']

    def check_scan_success(self, chain_name: str, in_list: List[int], out_list: List[int]) -> None:
        """Check that scan procedure is successful.

        This method should raise a ValueError with detailed error message if the scan procedure failed.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        in_list : List[int]
            the list of scan in values for each scan bus.
        out_list : List[int]
            the list of scan out values for each scan bus.
        """
        msg = 'chain %s input: %s' % (chain_name, in_list)
        self.log_msg(msg, level=logging.INFO)
        msg = 'chain %s output: %s' % (chain_name, out_list)
        self.log_msg(msg, level=logging.INFO)
        name_list = self.get_scan_names(chain_name)
        for name, val_in, val_out in zip(name_list, in_list, out_list):
            if not self.is_scan_read_only(chain_name, name) and val_in != val_out:
                emsg = 'scan bus %s.%s value = %d != %d' % (chain_name, name, val_out, val_in)
                self.log_msg(emsg, level=logging.ERROR)
                raise ValueError(emsg)

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
        check = check or self._check_scan
        chain_info = self.get_scan_chain_info(chain_name)
        scan_values = self._chain_value[chain_name]

        # get value and numbits list
        value, numbits = [], []
        for bus_info in chain_info['content']:
            bus_name = bus_info['name']
            bus_nbits = bus_info['nbits']
            value.append(scan_values[bus_name])
            numbits.append(bus_nbits)

        if self.is_fake_scan:
            self.log_msg('updating chain %s in fake scan mode' % chain_name, level=logging.INFO)
            output = value
        elif chain_info.get('is_pin', False):
            # this chain represents IO pins
            output = self.update_pins(chain_info, value, numbits)
        else:
            self.log_msg('scanning chain %s' % chain_name, level=logging.INFO)
            output = self.scan_in_and_read_out(chain_info, value, numbits)

        if len(value) != len(output):
            msg = 'Scan chain %s output length different than scan input.' % chain_name
            self.log_msg(msg, level=logging.ERROR)
            raise ValueError(msg)
        if check:
            self.log_msg('Checking scan chain %s correctness' % chain_name, level=logging.INFO)
            self.check_scan_success(chain_name, value, output)
            self.log_msg('Scan chain %s checking passed' % chain_name, level=logging.DEBUG)

        for name, val_out in zip(self._chain_order[chain_name], output):
            scan_values[name] = val_out

        self.log_msg('running callback functions after scan.', level=logging.INFO)
        for fun in self._callbacks:
            fun(chain_name)
        self.log_msg('scan update done.', level=logging.INFO)

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
            scan_dict = yaml.load(f)['scan_content']

        for chain_name, chain_values in scan_dict.items():
            changed = False
            for key, val in chain_values.items():
                if not self.is_scan_read_only(chain_name, key) and val != self.get_scan(chain_name, key):
                    changed = True
                    self.set_scan(chain_name, key, val)
            if changed:
                self.update_scan(chain_name)

    def save_scan_to_file(self, fname: str, **kwargs) -> None:
        """Save the current scan chain content to the given file.

        Parameters
        ----------
        fname : str
            the file to write.
        **kwargs
            Optional attributes to add to the file.
        """
        if os.path.isdir(fname):
            raise ValueError('Cannot save scan to a directory: %s' % fname)

        save_val = dict(scan_content=self._chain_value)
        if kwargs:
            save_val.update(kwargs)

        with open(fname, 'w') as f:
            yaml.dump(save_val, f)

    def add_callback(self, fun: Callable[[str], None]) -> None:
        """Adds a function which will be called if a scan chain changed.

        Parameters
        ----------
        fun : Callable[[str], None]
            the function to call if a scan chain updated.  This function should take
            a single string argument, which is the scan chain name.
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

    def get_scan_chain_info(self, chain_name: str) -> Dict[str, Any]:
        """Returns information about the given scan chain.

        Parameters
        ----------
        chain_name : str
            the scan chain name.

        Returns
        -------
        chain_info : Dict[str, Any]
            the scan chain information dictionary.
        """
        return self._scan_config['chains'][chain_name]

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
        chain_table = self._chain_value[chain_name]
        if bus_name not in chain_table:
            msg = 'Cannot find scan bus named %s in chain %s' % (bus_name, chain_name)
            self.log_msg(msg, level=logging.ERROR)
            raise ValueError(msg)

        num_bits = self._chain_blen[chain_name][bus_name]
        if value < 0 or value >= (1 << num_bits):
            msg = 'Scan value %d illegal for scan bus %s.%s' % (value, chain_name, bus_name)
            self.log_msg(msg, level=logging.ERROR)
            raise ValueError(msg)

        self.log_msg('Scan: setting {}/{} to {}'.format(chain_name, bus_name, value))
        chain_table[bus_name] = value

    def set_scan_vals(self, chain_name: str, val_dict: Dict[str, int]) -> None:
        """Sets scan buses values using keyword argument.

        Parameters
        ----------
        chain_name : str
            the scan chain name.
        val_dict : Dict[str, int]
            scan bus values in dictionary format.
        """
        for key, val in val_dict.items():
            self.set_scan(chain_name, key, val)

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


class FPGAFake(FPGABase):
    """A fake FPGA class used for testing purposes only.

    Parameters
    ----------
    scan_file : str
        scan chain file name.
    fake_scan : bool
        If True, then will not actually do the scan procedure.  This is useful for
        debugging.
    check_scan : bool
        True to check every scan operation.
    """
    def __init__(self, scan_file: str, fake_scan: bool=False, check_scan: bool=False) -> None:
        FPGABase.__init__(self, scan_file, fake_scan=fake_scan, check_scan=check_scan)

    def close(self) -> None:
        pass

    def update_pins(self, chain_info: Dict[str, Any], value: List[int], numbits: List[int]) -> List[int]:
        return value

    def is_scan_read_only(self, chain_name: str, bus_name: str) -> bool:
        chain_info = self.get_scan_chain_info(chain_name)
        return chain_info.get('read_only', False)

    def scan_in_and_read_out(self, chain_info: Dict[str, Any], value: List[int], numbits: List[int]) -> List[int]:
        return value

    def send_i2c_cmds(self,
                      i2c_name: str,
                      cmd_list: List[Tuple[int, List[int], int]],
                      ) -> List[Optional[List[int]]]:
        return [None] * len(cmd_list)

    def set_voltage(self, sup_name: str, val: float) -> None:
        pass

    def read_current(self, sup_name: str) -> float:
        return 0
