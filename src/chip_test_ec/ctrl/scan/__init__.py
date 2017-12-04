# -*- coding: utf-8 -*-

"""This package contains the scan chain data structure."""

import os
import numpy as np


class Scan(object):
    """A object that keeps track of scan chain information and provides
    scan chain modification methods.
    """

    def __init__(self, fname, fpga, pre_bytes=0, post_bytes=0, debug=False):
        """Create a new Scan instance.

        Parameters
        ----------
        fname : str
            name of the scan chain file.
        fpga : fpga.gtx.GTX
            the fpga used to read and write the scan chain.  If None, this scan
            chain will run in fake scan mode.
        pre_bytes : int
            number of extra prefix bytes read from FPGA.
        post_bytes : int
            number of extra suffix bytes read from FPGA
        debug : bool
            True to enable debug messages.
        """
        self.fpga = fpga
        self.debug = debug

        self.value = {}
        self.numbits = {}
        self.index = {}
        self.order = []
        self.listeners = []
        self.read_pre_bytes = pre_bytes
        self.read_post_bytes = post_bytes
        self.pre_data = []
        self.post_data = []

        cur_idx = 0
        with open(fname, 'r') as f:
            for line in f:
                parts = line.split()
                name = parts[0]
                defval = int(parts[1])
                numbits = int(parts[2])

                self.numbits[name] = numbits
                self.value[name] = defval
                self.order.append(name)
                self.index[name] = cur_idx
                cur_idx += numbits

        self.nbits = cur_idx
        self.nbytes = int(np.ceil(self.nbits / 8.0))

        self.write_twice()

    def set_from_file(self, fname):
        if not os.path.exists(fname):
            print('Non-existent file: {}'.format(fname))
            return

        with open(fname, 'r') as f:
            for line in f:
                parts = line.split()
                name = parts[0]
                defval = int(parts[1])
                numbits = int(parts[2])
                self.value[name] = defval

        self.write_twice()

    def save_to_file(self, fname):
        with open(fname, 'w') as f:
            for name in self.order:
                f.write('{0}\t{1}\t{2}\n'.format(name, self.value[name], self.numbits[name]))

    def add_listener(self, obj):
        """Adds a listener which will be notified if the scan chain changes.

        Parameters
        ----------
        obj :
            the listener to add.
        """
        self.listeners.append(obj)

    def get_scan_names(self):
        """Returns a list of scan names in the order you scan in.

        Returns
        -------
        scan_list : list[str]
            a list of scan names.
        """
        return self.order[:]

    def set(self, name, value):
        """Sets the given scan bus value.

        Parameters
        ----------
        name : str
            the scan bus to set.
        value : int
            the new value
        """
        if self.debug:
            print('Scan: setting {} to {}'.format(name, value))
        self.value[name] = value

    def get_numbits(self, name):
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
        return self.numbits[name]

    def get_value(self, name):
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
        return self.value[name]

    def get_pre_bytes_data(self):
        """Returns the last read pre-scan chain data.

        Returns
        -------
        val_list : list[int]
            list of pre-scan byte data.
        """
        return self.pre_data

    def get_post_bytes_data(self):
        """Returns the last read post-scan chain data.

        Returns
        -------
        val_list : list[int]
            list of post-scan byte data.
        """
        return self.post_data

    def to_byte_array(self):
        """Convert the content of this Scan object into an array of 8 bit integers.

        Returns
        -------
        arr : list[int]
            a list of byte values.
        """
        bstr = ''
        for name in self.order:
            bstr += np.binary_repr(self.value[name], self.numbits[name])

        return [int(bstr[i:i + 8], 2) for i in xrange(0, len(bstr), 8)]

    def _from_byte_array(self, barr):
        """Update the content of this Scan object from the given byte array.

        Parameters
        ----------
        barr : list[int]
            a list of byte values to update.
        """
        if len(barr) != self.nbytes:
            raise Exception('bytearray length {0} != {1}.'.format(len(barr), self.nbytes))
        bstr = ''
        for val in barr:
            bstr += np.binary_repr(val, 8)
        for name in self.order:
            idx = self.index[name]
            n = self.numbits[name]
            old_val = self.value[name]
            new_val = int(bstr[idx:idx+n], 2)
            if old_val != new_val:
                if self.debug:
                    print('scan bus {} changed from {} to {}'.format(name, old_val, new_val))
                self.value[name] = new_val

    def write_twice(self):
        """Write the content of this instance to the scan chain twice,
        then update the content with what you read out.
        """

        if self.fpga is not None:
            # make integer array to write to fpga
            arr = [0x10]
            barr = self.to_byte_array()
            nbytes = len(barr)
            arr.extend(barr)

            # write twice
            self.fpga.write_ints(arr)
            self.fpga.read_ints(nbytes + self.read_pre_bytes + self.read_post_bytes)
            self.fpga.write_ints(arr)
            scan_out = self.fpga.read_ints(nbytes + self.read_pre_bytes + self.read_post_bytes)

            new_scan = scan_out[self.read_pre_bytes:len(scan_out) - self.read_post_bytes]
            self.pre_data = scan_out[:self.read_pre_bytes]
            self.post_data = scan_out[len(scan_out) - self.read_post_bytes:]

            # update values
            self._from_byte_array(new_scan)
        else:
            self.pre_data = [0] * self.read_pre_bytes
            self.post_data = [0] * self.read_post_bytes

        for obj in self.listeners:
            obj.scanChanged()
