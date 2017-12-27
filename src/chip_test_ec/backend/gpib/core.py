# -*- coding: utf-8 -*-

"""This module defines Python classes that implement the GPIB interface.
"""

from typing import Optional

import abc
import logging
import traceback
import socket

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
    def close(self):
        """Close resources associated with this GPIB device."""
        pass

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

    def close(self):
        """Close resources associated with this GPIB device."""
        self.log_msg('Closing GPIB device (%d, %d)' % (self.bid, self.pad))
        pass

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

    def close(self):
        """Close resources associated with this GPIB device."""
        self.log_msg('Closing GPIB device (%d, %d)' % (self.bid, self.pad))
        pass

    def write(self, cmd: str) -> None:
        """Sends the given GPIB command to the device.

        Parameters
        ----------
        cmd : str
            the GPIB command.
        """
        self.log_msg('Sending command %s to device (%d, %d)' % (cmd, self.bid, self.pad))
        # noinspection PyUnresolvedReferences
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
        # noinspection PyUnresolvedReferences
        result = self._dev.query(cmd)
        self.log_msg('Receive output %s from device (%d, %d)' % (result, self.bid, self.pad))
        return result


class GPIBTCP(GPIBBase):
    """This class uses a TCP socket to directly send/receive commands to a GPIB instrument.

    Parameters
    ----------
    bid : int
        the GPIB board ID.
    pad : int
        the GPIB primiary address.
    ip_addr : str
        the IP address of the instrument.
    port : int
        the TCP port number for communication.
    timeout_ms : int
        the GPIB timeout, in miliseconds.
    buffer_size : int
        the receive buffer size.
    """
    def __init__(self, bid: int, pad: int, ip_addr: str, port: int,
                 timeout_ms: int=10000, buffer_size: int=2048) -> None:
        GPIBBase.__init__(self, bid, pad, timeout_ms=timeout_ms)

        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._buf_size = buffer_size
        self.log_msg('Connecting to IP address %s:%d' % (ip_addr, port))
        self._s.connect((ip_addr, port))
        self._ip_addr = ip_addr
        self._port = port

    def close(self):
        """Close resources associated with this GPIB device."""
        self.log_msg('Closing GPIB device at %s:%d' % (self._ip_addr, self._port))
        self._s.close()

    def write(self, cmd: str) -> None:
        """Sends the given GPIB command to the device.

        Parameters
        ----------
        cmd : str
            the GPIB command.
        """
        self.log_msg('Sending command %s to device at %s:%d' % (cmd, self._ip_addr, self._port))
        # noinspection PyUnresolvedReferences
        self._s.send((cmd + '\n').encode())

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
        self.log_msg('Sending query %s to device at %s:%d' % (cmd, self._ip_addr, self._port))
        self.write(cmd)
        # noinspection PyUnresolvedReferences
        result = self._s.recv(self._buf_size).decode()
        self.log_msg('Received output %s from device at %s:%d' % (result, self._ip_addr, self._port))
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
    **kwargs
        Additional optional arguments.
        True to prioritize using National Instruments visa package.
    """
    def __init__(self, bid: int, pad: int, timeout_ms: int=10000, **kwargs) -> None:
        LoggingBase.__init__(self)

        self._dev = None
        if 'ip_addr' in kwargs:
            new_kwargs = kwargs.copy()
            ip_addr = new_kwargs.pop('ip_addr')
            port = new_kwargs.pop('port')
            self._dev = GPIBTCP(bid, pad, ip_addr, port, timeout_ms=timeout_ms, **new_kwargs)
        elif kwargs.get('use_visa', True):
            if visa is None:
                self.log_msg('Failed to import visa, revert to Gpib.')
            else:
                self._dev = GPIBVisa(bid, pad, timeout_ms=timeout_ms)

        if self._dev is None:
            if Gpib is None:
                raise ImportError('Failed import either the visa package or the Gpib package.')
            self._dev = GPIBBasic(bid, pad, timeout_ms=timeout_ms)

    def close(self):
        """Close resources associated with this GPIB device."""
        self._dev.close()

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
