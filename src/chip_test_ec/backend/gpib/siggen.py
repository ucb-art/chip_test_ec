# -*- coding: utf-8 -*-

"""This module contains various classes to control different signal generators over GPIB.
"""

from .core import GPIBController


class AG81142A(GPIBController):
    """A class that provides methods to control an Agilent 81142A signal generator.

    Parameters
    ----------
    bid : int
        the GPIB board ID.
    pad : int
        the GPIB primiary address.
    timeout_ms : int
        the GPIB timeout, in miliseconds.
    **kwargs :
        additional keyword arguments.
    """
    def __init__(self, bid: int, pad: int, timeout_ms: int=10000, **kwargs) -> None:
        GPIBController.__init__(self, bid, pad, timeout_ms=timeout_ms, **kwargs)

    def get_output_delay(self) -> float:
        """Returns the output delay in picoseconds."""
        val = self.query('OUTP:DEL?').strip()
        return float(val)

    def set_output_delay(self, td: float) -> None:
        """Sets the output delay.

        Parameters
        ----------
        td : float
            the output delay, in seconds.
        """
        self.write('OUTP:DEL %.6e' % td)
