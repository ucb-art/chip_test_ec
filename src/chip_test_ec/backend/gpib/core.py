# -*- coding: utf-8 -*-

"""This module defines Python classes that implement the GPIB interface.
"""

from typing import Optional

import abc
import logging
import traceback

try:
    import Gpib
except ImportError:
    Gpib = None

try:
    import visa
except ImportError:
    visa = None

from ...base import LoggingBase


class GPIBBase(LoggingBase, metaclass=abc.ABCMeta):
    """This is the GPIB interface abstract base class.

    Parameters
    ----------
    bid : int
        the GPIB board ID.
    pad : int
        the GPIB primiary address.
    timeout_ms : int
        the GPIB timeout, in miliseconds.
    """
    def __init__(self, bid: int, pad: int, timeout_ms: int=10000) -> None:
        LoggingBase.__init__(self)

        self._bid = bid
        self._pad = pad
        self._timeout_ms = timeout_ms

    @property
    def bid(self) -> int:
        """Returns the GPIB board address."""
        return self._bid

    @property
    def pad(self) -> int:
        """Returns the GPIB primary address."""
        return self._pad

    @property
    def timeout_ms(self) -> int:
        """Returns the GPIB timeout, in milliseconds."""
        return self._timeout_ms

    @abc.abstractmethod
    def write(self, cmd: str) -> None:
        """Sends the given GPIB command to the device.

        Parameters
        ----------
        cmd : str
            the GPIB command.
        """
        pass

    @abc.abstractmethod
    def query(self, cmd: str) -> Optional[str]:
        """Sends the given GPIB command to the device, then return device output as a string.

        Parameters
        ----------
        cmd : str
            the GPIB command.

        Returns
        -------
        output : Optional[str]
            the device output.  None if an error occurred.
        """
        return ''


class GPIBBasic(GPIBBase):
    """This class uses the Gpib package to communicate with GPIB devices.

    Parameters
    ----------
    bid : int
        the GPIB board ID.
    pad : int
        the GPIB primiary address.
    timeout_ms : int
        the GPIB timeout, in miliseconds.
    """
    def __init__(self, bid: int, pad: int, timeout_ms: int=10000):
        GPIBBase.__init__(self, bid, pad, timeout_ms=timeout_ms)
        self._dev = Gpib.Gpib(bid, pad)
        self._dev.clear()

    def write(self, cmd: str) -> None:
        """Sends the given GPIB command to the device.

        Parameters
        ----------
        cmd : str
            the GPIB command.
        """
        self.log_msg('Sending command %s to device (%d, %d)' % (cmd, self.bid, self.pad))
        self._dev.write(cmd)
        self._process_status(self._dev.ibsta())

    def query(self, cmd: str) -> Optional[str]:
        """Sends the given GPIB command to the device, then return device output as a string.

        Parameters
        ----------
        cmd : str
            the GPIB command.

        Returns
        -------
        output : Optional[str]
            the device output.  None if an error occurred.
        """
        self.log_msg('Sending query %s to device (%d, %d)' % (cmd, self.bid, self.pad))
        self.write(cmd)
        # noinspection PyBroadException
        try:
            val = self._dev.read(len=2048)
        except Exception:
            self.log_msg(traceback.format_exc(), level=logging.ERROR)
            val = None

        self.log_msg('Receive output %s from device (%d, %d)' % (val, self.bid, self.pad))
        return val

    def _process_status(self, sta: int) -> None:
        """Process the given GPIB status code.

        Parameters
        ----------
        sta : int
            the GPIB status code.
        """
        # do nothing for now
        pass


class GPIBVisa(GPIBBase):
    """This class uses the National Instruments visa package to communicate with GPIB devices.

    Parameters
    ----------
    bid : int
        the GPIB board ID.
    pad : int
        the GPIB primiary address.
    timeout_ms : int
        the GPIB timeout, in miliseconds.
    """
    def __init__(self, bid: int, pad: int, timeout_ms: int=10000):
        GPIBBase.__init__(self, bid, pad, timeout_ms=timeout_ms)

        self._rm = visa.ResourceManager()
        resources = self._rm.list_resources()
        sid = 'GPIB{0}::{1}::INSTR'.format(self.bid, self.pad)
        if sid not in resources:
            raise ValueError('GPIB resource {0} not found.  Available resources are:\n{1}'.format(sid, resources))
        self._dev = self._rm.open_resource(sid)
        self._dev.timeout = timeout_ms

    def write(self, cmd: str) -> None:
        """Sends the given GPIB command to the device.

        Parameters
        ----------
        cmd : str
            the GPIB command.
        """
        self.log_msg('Sending command %s to device (%d, %d)' % (cmd, self.bid, self.pad))
        self._dev.write(cmd)

    def query(self, cmd: str) -> Optional[str]:
        """Sends the given GPIB command to the device, then return device output as a string.

        Parameters
        ----------
        cmd : str
            the GPIB command.

        Returns
        -------
        output : Optional[str]
            the device output.  None if an error occurred.
        """
        self.log_msg('Sending query %s to device (%d, %d)' % (cmd, self.bid, self.pad))
        result = self._dev.query()
        self.log_msg('Receive output %s from device (%d, %d)' % (result, self.bid, self.pad))
        return result


class GPIBController(LoggingBase):
    """This is the base GPIB controller class.

    This class is a thin wrapper class around GPIBBase that figures out which
    Python library to use for GPIB communication.  Other GPIB device classes should
    subclass this class.

    Parameters
    ----------
    bid : int
        the GPIB board ID.
    pad : int
        the GPIB primiary address.
    timeout_ms : int
        the GPIB timeout, in miliseconds.
    use_visa : bool
        True to prioritize using National Instruments visa package.
    """
    def __init__(self, bid: int, pad: int, timeout_ms: int=10000, use_visa: bool=True) -> None:
        LoggingBase.__init__(self)

        self._dev = None
        if use_visa:
            if visa is None:
                self.log_msg('Failed to import visa, revert to Gpib.')
            else:
                self._dev = GPIBVisa(bid, pad, timeout_ms=timeout_ms)

        if self._dev is None:
            if Gpib is None:
                raise ImportError('Failed import either the visa package or the Gpib package.')
            self._dev = GPIBBasic(bid, pad, timeout_ms=timeout_ms)

    def write(self, cmd: str) -> None:
        """Sends the given GPIB command to the device.

        Parameters
        ----------
        cmd : str
            the GPIB command.
        """
        self._dev.write(cmd)

    def query(self, cmd: str) -> Optional[str]:
        """Sends the given GPIB command to the device, then return device output as a string.

        Parameters
        ----------
        cmd : str
            the GPIB command.

        Returns
        -------
        output : Optional[str]
            the device output.  None if an error occurred.
        """
        return self._dev.query(cmd)
