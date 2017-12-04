# -*- coding: utf-8 -*-

"""This module defines various classes for controlling FPGAs.

The FPGABase class is the base class for all FPGA controllers.

The FPGASerial class is a class that controls an FPGA using a serial port.
It can be used to control Xilinx GTX
"""

from typing import Sequence, List

import abc
import logging
import serial
import struct


class FPGABase(abc.ABC):
    """The base class that represents all FPGAs.

    This class defines methods that all FPGA controller have to implement.

    """
    def __init__(self) -> None:
        self._logger = logging.getLogger(self.get_full_qualified_name())

    @classmethod
    def get_full_qualified_name(cls) -> str:
        """Returns the fully qualified class name of this class."""
        return cls.__module__ + '.' + cls.__name__

    def log_msg(self, msg: str, level: int=logging.DEBUG) -> None:
        """Logs the given message.

        Parameters
        ----------
        msg : str
            the message to log.
        level : int
            the logging level.
        """
        self._logger.log(level=level, msg=msg)

    @abc.abstractmethod
    def write_int(self, num: int) -> None:
        """Transmit the given integer value as a byte to the FPGA.

        Parameters
        ----------
        num : int
            the byte value to transmit.
        """
        pass

    @abc.abstractmethod
    def write_ints(self, num_list: Sequence[int]) -> None:
        """Transmit the given list of integers as bytes to the FPGA.

        Parameters
        ----------
        num_list : Sequence[int]
            the list of values to transmit
        """
        pass

    @abc.abstractmethod
    def read_ints(self, size: int) -> List[int]:
        """Read given number of bytes from the FPGA and return as a list
        of integers.

        Parameters
        ----------
        size : int
            number of bytes to read.

        Returns
        -------
        byte_list : List[int]
            a list of byte values as integers.
        """
        return []

    @abc.abstractmethod
    def close(self) -> None:
        """Close the FPGA controller, free up resources.."""
        pass


class FPGASerial(FPGABase):
    """A default implmentation of FPGABase that controls FPGA using a serial port (usually USB).

    Parameters
    ----------
    port : str
        the serial port name.
    baud_rate : int
        the serial port baud rate.
    timeout : int
        the serial port timeout, in seconds.
    flow_ctrl : str
        the serial port flow control scheme.
    """

    def __init__(self, port: str='COM3', baud_rate: int=500000, timeout: float=10.0,
                 flow_ctrl: str='hardware') -> None:
        FPGABase.__init__(self)

        # matlab switch between XON/XOFF and RTS/CTS flow control
        if flow_ctrl == 'hardware':
            rtscts = True
            xonxoff = False
        else:
            rtscts = False
            xonxoff = True

        # create serial port
        self._port = serial.Serial(port=port,
                                   baudrate=baud_rate,
                                   timeout=timeout,
                                   xonxoff=xonxoff,
                                   rtscts=rtscts,
                                   write_timeout=timeout,
                                   dsrdtr=False)

    def write_int(self, num: int) -> None:
        """Transmit the given integer value as a byte to the FPGA.

        Parameters
        ----------
        num : int
            the byte value to transmit.
        """
        msg = struct.pack('@B', num)
        self.log_msg('Writing single int = {0}, msg = {1}'.format(num, msg))
        self._port.write(msg)

    def write_ints(self, num_list: Sequence[int]) -> None:
        """Transmit the given list of integers as bytes to the FPGA.

        Parameters
        ----------
        num_list : Sequence[int]
            the list of values to transmit
        """
        msg = bytearray(num_list)
        self.log_msg('Writing integer list = {0}, msg = {1}'.format(num_list, [val for val in msg]))
        self._port.write(msg)

    def read_ints(self, size: int) -> List[int]:
        """Read given number of bytes from the FPGA and return as a list
        of integers.

        Parameters
        ----------
        size : int
            number of bytes to read.

        Returns
        -------
        byte_list : List[int]
            a list of byte values as integers.
        """
        barr = bytearray(self._port.read(size=size))
        blist = [val for val in barr]
        self.log_msg('Read bytearray: {0}'.format(blist))
        return blist

    def close(self) -> None:
        """Close the FPGA controller, free up resources.."""
        self._port.close()
