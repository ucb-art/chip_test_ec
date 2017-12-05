# -*- coding: utf-8 -*-

"""This module contains various classes to control different oscilloscopes over GPIB.
"""

from .core import GPIBController


class AG54855A(GPIBController):
    """A class that provides methods to control an Agilent 54855A oscilloscope.

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
        GPIBController.__init__(self, bid, pad, timeout_ms=timeout_ms, use_visa=use_visa)
        # turn off system headers so received results don't have them
        # self.write(':system:header off')

    def setup_tdelta(self, dir1: str, num1: int, pos1: str, dir2: str, num2: int, pos2: str) -> None:
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

    def get_display_trange(self) -> float:
        """Returns the display time range."""
        return float(self.query(':timebase:range?'))

    def set_display_trange(self, trang: float) -> None:
        """Sets the display time range.

        Parameters
        ----------
        trang : float
            the time range, in seconds.
        """
        self.write(':timebase:range {:.4g}'.format(trang))

    def get_tdelta(self, ch1: int, ch2: int) -> float:
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

    def get_vrms(self, ch: int) -> float:
        """Get the RMS voltage of the given channel.

        Parameters
        ----------
        ch : int
            channel ID.

        Returns
        -------
        vrms : float
            the RMS voltage, in volts.
        """
        cmd = ":measure:vrms? cycle,ac,channel{0}".format(ch)
        return float(self.query(cmd))

    def get_vrms_display(self, ch: int) -> float:
        """Returns the display RMS voltage of the given channel.

        Parameters
        ----------
        ch : int
            channel ID.

        Returns
        -------
        vrms : float
            the RMS voltage, in volts.
        """
        cmd = ":measure:vrms? display,ac,channel{0}".format(ch)
        return float(self.query(cmd))

    def set_fft_threshold(self, thres_db: float) -> None:
        """Sets FFT Threshold.

        Parameters
        ----------
        thres_db: float
            the FFT threshold, in dB.
        """
        self.write(':measure:fft:threshold {:.4g}'.format(thres_db))

    def get_fft_threshold(self) -> float:
        """Returns the current FFT threshold."""
        return float(self.query(':measure:fft:threshold?'))

    def set_fft_peak1(self, n: str) -> None:
        """Sets FFT peak1."""
        self.write(':measure:fft:peak1 {}'.format(n))

    def set_fft_peak2(self, n: str) -> None:
        """Sets FFT peak2."""
        self.write(':measure:fft:peak2 {}'.format(n))

    def get_fft_mag(self, func_id: int) -> float:
        """Returns the FFT magnitude of the given function.

        Parameters
        ----------
        func_id : int
            the function ID.

        Returns
        -------
        mag : float
            the FFT magnitude.
        """
        return float(self.query(':measure:fft:magnitude? function{}'.format(func_id)))

    def get_value(self, xval: float, wvtype: str, wv_id: int, precision=6) -> float:
        """Returns the waveform value at the given X coordinate.

        Parameters
        ----------
        xval : float
            the X coordinate.
        wvtype : str
            the waveform type.
        wv_id : int
            the waveform ID.
        precision: int
            the precision of xval.

        Returns
        -------
        val : float
            the waveform value.
        """
        fmt = ':measure:vtime? {0:.%dg},{1}{2}' % precision
        return float(self.query(fmt.format(xval, wvtype, wv_id)))

    def calc_fft_mag(self, ch_id: int, func_id: int) -> None:
        """Make oscilloscope calculate the FFT magnitude.

        Parameters
        ----------
        ch_id : int
            the channel ID.
        func_id : int
            the function ID.
        """
        self.write(':function{0}:fftmagnitude channel{1}'.format(func_id, ch_id))

    def set_fullscale(self, ch_id: int, vfull: float) -> None:
        """Sets the full-scale voltage of the given channel.

        Parameters
        ----------
        ch_id : int
            the channel ID.
        vfull : float
            the full-scale voltage, in volts.
        """
        self.write(':channel{0}:range {1:.4g}'.format(ch_id, vfull))

    def get_vmax(self, ch_id: int) -> float:
        """Returns the maximum voltage of the given channel.

        Parameters
        ----------
        ch_id : int
            the channel ID.

        Returns
        -------
        vmax : float
            the maximum voltage, in volts.
        """
        return float(self.query(':measure:vmax? channel{}'.format(ch_id)))

    def get_vmin(self, ch_id: int) -> float:
        """Returns the minimum voltage of the given channel.

        Parameters
        ----------
        ch_id : int
            the channel ID.

        Returns
        -------
        vmax : float
            the minimum voltage, in volts.
        """
        return float(self.query(':measure:vmin? channel{}'.format(ch_id)))

    def get_fullscale(self, ch_id: int) -> float:
        """Returns the full-scale voltage of the given channel.

        Parameters
        ----------
        ch_id : int
            the channel ID.

        Returns
        -------
        vfull : float
            the full-scale voltage, in volts.
        """
        return float(self.query(':channel{0}:range?'.format(ch_id)))
