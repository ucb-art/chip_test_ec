# -*- coding: utf-8 -*-

"""This module defines a class that talks to Xilinx GTX.  This is used for SCPA testing."""

import serial
import struct


class GTX(object):
    """A class that communicates with Xilinx GTX using a serial port (usually USB.)
    """

    def __init__(self, port='COM3', baudrate=500000, timeout=10.0, flow_ctrl='hardware',
                 debug=False):
        # matlab switch between XON/XOFF and RTS/CTS flow control
        if flow_ctrl == 'hardware':
            rtscts = True
            xonxoff = False
        else:
            rtscts = False
            xonxoff = True

        self.debug = debug

        # create serial port
        self.port = serial.Serial(port=port,
                                  baudrate=baudrate,
                                  timeout=timeout,
                                  xonxoff=xonxoff,
                                  rtscts=rtscts,
                                  write_timeout=timeout,
                                  dsrdtr=False)

    def write_int(self, num):
        """Transmit the given integer value as a byte to the FPGA.

        Parameters
        ----------
        num : int
            the byte value to transmit.
        """
        msg = struct.pack('@B', num)
        if self.debug:
            print('Writing single int: {0}'.format(msg))
        self.port.write(msg)

    def write_ints(self, num_list):
        """Transmit the given list of integers as bytes to the FPGA.

        Parameters
        ----------
        num_list : list[int]
            the list of values to transmit
        """
        msg = bytearray(num_list)
        if self.debug:
            print('Writing bytearray: {0}'.format([val for val in msg]))
        self.port.write(msg)

    def read_ints(self, size):
        """Read given number of bytes from the FPGA and return as a list
        of integers.

        Parameters
        ----------
        size : int
            number of bytes to read.

        Returns
        -------
        blist : list[int]
            a list of byte values as integers.
        """
        barr = bytearray(self.port.read(size=size))
        blist = [val for val in barr]
        if self.debug:
            print('Read bytearray: {0}'.format(blist))
        return blist

    def close(self):
        """Close the port."""
        self.port.close()
