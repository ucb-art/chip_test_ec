# -*- coding: utf-8 -*-


"""This module defines core classes for controlling chip, FPGA, and equipments.."""

from typing import Optional, Dict, Any

from ..util.core import import_class

# type check imports
from .fpga.base import FPGABase
from .gpib.core import GPIBController


class Controller(object):
    """A class that controls various equipments..

    Parameters
    ----------
    specs : Dict[str, Any]
        the controller specification dictionary.
    """
    def __init__(self, specs: Dict[str, Any]) -> None:
        # create FPGA
        fpga_info = specs['fpga']
        mod_name = fpga_info['module']
        cls_name = fpga_info['class']
        params = fpga_info['params']
        fpga_cls = import_class(mod_name, cls_name)
        self._fpga = fpga_cls(**params)  # type: FPGABase

        # create GPIB devices
        gpib_info = specs['gpib']
        self._gpib_devices = {}
        for name, info in gpib_info.items():
            if self._fpga.is_fake_scan:
                self._gpib_devices[name] = None
            else:
                mod_name = info['module']
                cls_name = info['class']
                params = info['params']
                gpib_cls = import_class(mod_name, cls_name)
                self._gpib_devices[name] = gpib_cls(**params)

    @property
    def fpga(self) -> Optional[FPGABase]:
        return self._fpga

    @property
    def gpib_table(self) -> Dict[str, Optional[GPIBController]]:
        return self._gpib_devices

    def get_device(self, name: str) -> Optional[GPIBController]:
        """Returns the GPIB device corresponding to the given name.

        Parameters
        ----------
        name : str
            the GPIB device name.

        Returns
        -------
        device : Optional[GPIBController]
            the GPIB device, None if this is a fake Controller.
        """
        return self._gpib_devices[name]
