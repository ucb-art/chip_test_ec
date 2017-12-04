# -*- coding: utf-8 -*-

"""This package contains all GUI related code.
"""

from . import base
from . import gpib
from . import scan


def make_fpga_form(name, conf_path, font_size=11):
    """Returns an FPGA form.

    Parameters
    ----------
    name : str
        name of the form.
    conf_path : str
        the configuration directory path.
    font_size : int
        the font size.

    Returns
    -------
    form : gui.base.TitledForm.TitledForm
        a user input form for FPGA.
    """
    specs = [
        ('port', str, 'COM3'),
        ('baud_rate', int, 500000, 0, 9999999, 1),
        ('time_out', float, 10.0, 0.0, 9999.0, 0.1, 1),
        ('flow_ctrl', ['hardware', 'software'], 'hardware'),
        ('fake', bool, False),
        ('debug', bool, False),
    ]
    return base.TitledForm(name, conf_path, specs, font_size=font_size)


def make_gpib_form(name, conf_path, font_size=11):
    """Returns an GPIB form.

    Parameters
    ----------
    name : str
        name of the form.
    conf_path : str
        the configuration directory path.
    font_size : int
        the font size.

    Returns
    -------
    form : gui.base.TitledForm.TitledForm
        a user input form for GPIB.
    """
    specs = [
        ('bid', int, 0, 0, 999, 1),
        ('pad', int, 0, 0, 999, 1),
        ('skip', bool, False)
    ]
    return base.TitledForm(name, conf_path, specs, font_size=font_size)


def make_scan_form(name, conf_path, font_size=11):
    """Returns an Scan form.

    Parameters
    ----------
    name : str
        name of the form.
    conf_path : str
        the configuration directory path.
    font_size : int
        the font size.

    Returns
    -------
    form : gui.base.TitledForm.TitledForm
        a user input form for Scan.
    """
    specs = [
        ('fname', str, 'scan.txt', 'file'),
        ('fake', bool, False),
        ('debug', bool, False),
    ]
    return base.TitledForm(name, conf_path, specs, font_size=font_size)
