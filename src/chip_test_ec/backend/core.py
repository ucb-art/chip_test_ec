# -*- coding: utf-8 -*-


"""This module defines core classes for controlling chip, FPGA, and equipments.."""

from typing import Optional, Dict, Any

from ..util.core import import_class
from .scan.core import Scan

# type check imports
from .fpga.base import FPGABase
from .gpib.core import GPIBController


class Controller(object):
    """A class that controls various equipments..

    Parameters
    ----------
    specs : Dict[str, Any]
        the controller specification dictionary.
    fake : bool
        If True,
    """

    def __init__(self, specs: Dict[str, Any], fake: bool=False) -> None:
        # create FPGA
        fpga_info = specs.get('fpga', None)
        if fpga_info is None or fake:
            self._fpga = None
        else:
            mod_name = fpga_info['module']
            cls_name = fpga_info['class']
            params = fpga_info['params']
            fpga_cls = import_class(mod_name, cls_name)
            self._fpga = fpga_cls(**params)

        # create scan
        scan_info = specs['scan']
        if self._fpga is None and not fake:
            raise Exception('Not in fake scan mode and FPGA is not initialized.')
        fname = scan_info['fname']
        pre_bytes = scan_info.get('pre_bytes', 0)
        post_bytes = scan_info.get('post_bytes', 0)
        self._scan = Scan(fname, self._fpga, pre_bytes=pre_bytes, post_bytes=post_bytes)

        # create GPIB devices
        gpib_info = specs['gpib']
        self._gpib_devices = {}
        for name, info in gpib_info.items():
            mod_name = info['module']
            cls_name = info['class']
            params = info['params']
            gpib_cls = import_class(mod_name, cls_name)
            self._gpib_devices[name] = gpib_cls(**params)

    @property
    def fpga(self) -> Optional[FPGABase]:
        return self._fpga

    @property
    def scan(self) -> Scan:
        return self._scan

    @property
    def gpib_table(self) -> Dict[str, GPIBController]:
        return self._gpib_devices

    def get_device(self, name: str) -> GPIBController:
        """Returns the GPIB device corresponding to the given name.

        Parameters
        ----------
        name : str
            the GPIB device name.

        Returns
        -------
        device : GPIBController
            the GPIB device.
        """
        return self._gpib_devices[name]
