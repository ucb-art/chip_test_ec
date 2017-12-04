# -*- coding: utf-8 -*-

"""This module contains code to control Agilent 54855A oscilloscope over GPIB.
"""

from .GPIBBase import GPIBBase


class AG54855A(GPIBBase):
    """A class that provides methods to control an Agilent 54855A oscilloscope.
    """
    def __init__(self, bid, pad, timeout_ms=10000):
        super(AG54855A, self).__init__(bid, pad, timeout_ms=timeout_ms)
        # turn off system headers so received results don't have them
        # self.write(':system:header off')

    def setup_tdelta(self, dir1, num1, pos1, dir2, num2, pos2):
        """Setup time difference measurement options.

        Parameters
        ----------
        dir1 : str
            Starting edge direction.  One of 'rising', 'falling', or 'either'.
        num1 : int
            Starting edge number.  Should be between 1 and 65534.
        pos1 : str
            Starting edge trigger point.  One of 'upper', 'middle', or 'lower'.
        dir2 : str
            Stopping edge direction.  One of 'rising', 'falling', or 'either'.
        num2 : int
            Stopping edge number.  Should be between 1 and 65534.
        pos2 : str
            Stopping edge trigger point.  One of 'upper', 'middle', or 'lower'.
        """
        cmd = ':measure:define deltatime,{0},{1},{2},{3},{4},{5}'.format(dir1, num1, pos1, dir2, num2, pos2)
        self.write(cmd)

    def get_display_trange(self):
        return float(self.query(':timebase:range?'))

    def set_display_trange(self, trang):
        self.write(':timebase:range {:.4g}'.format(trang))

    def get_tdelta(self, ch1, ch2):
        """Get the time difference between the waveforms on the two given channels.

        Parameters
        ----------
        ch1 : int
            channel 1 ID.
        ch2 : int
            channel 2 ID.

        Returns
        -------
        tdelta : float
            the time difference, in seconds.
        """
        cmd = ':measure:deltatime? channel{0},channel{1}'.format(ch1, ch2)
        return float(self.query(cmd))

    def get_vrms(self, ch):
        """Get the RMS voltage of the given channel.

        Parameters
        ----------
        ch : int
            channel id

        Returns
        -------
        vrms : float
            the RMS voltage, in volts.
        """
        cmd = ":measure:vrms? cycle,ac,channel{0}".format(ch)
        return float(self.query(cmd))

    def get_vrms_display(self, ch):
        cmd = ":measure:vrms? display,ac,channel{0}".format(ch)
        return float(self.query(cmd))

    def set_fft_threshold(self, thres_db):
        """Set FFT Threshold.

        Parameters
        ----------
        thres_db
        """
        self.write(':measure:fft:threshold {:.4g}'.format(thres_db))

    def get_fft_threshold(self):
        return float(self.query(':measure:fft:threshold?'))

    def set_fft_peak1(self, n):
        self.write(':measure:fft:peak1 {}'.format(n))

    def set_fft_peak2(self, n):
        self.write(':measure:fft:peak2 {}'.format(n))

    def get_fft_mag(self, func_id):
        return float(self.query(':measure:fft:magnitude? function{}'.format(func_id)))

    def get_value(self, xval, wvtype, wv_id, precision=6):
        fmt = ':measure:vtime? {0:.%dg},{1}{2}' % precision
        return float(self.query(fmt.format(xval, wvtype, wv_id)))

    def calc_fft_mag(self, ch_id, func_id):
        self.write(':function{0}:fftmagnitude channel{1}'.format(func_id, ch_id))

    def set_fullscale(self, ch_id, vfull):
        self.write(':channel{0}:range {1:.4g}'.format(ch_id, vfull))

    def get_vmax(self, ch_id):
        return float(self.query(':measure:vmax? channel{}'.format(ch_id)))

    def get_vmin(self, ch_id):
        return float(self.query(':measure:vmin? channel{}'.format(ch_id)))

    def get_fullscale(self, ch_id):
        return float(self.query(':channel{0}:range?'.format(ch_id)))
