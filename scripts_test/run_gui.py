#!./venv/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml

CWD = os.path.abspath('.')
sys.path.append(CWD)
sys.path.append(os.path.join(CWD, 'src_python'))
sys.path.append(os.path.join(CWD, 'chip_test_ec', 'src'))


from chip_test_ec.core import run_main


def start_gui():
    title = 'Chip Test Debug'
    spec_test_dir = os.path.join(CWD, 'chip_test_ec', 'specs_test')
    ctrl_specs_fname = os.path.join(spec_test_dir, 'controller.yaml')
    gui_specs_fname = os.path.join(spec_test_dir, 'main_gui.yaml')

    with open(ctrl_specs_fname, 'r') as f:
        ctrl_specs = yaml.load(f)

    with open(gui_specs_fname, 'r') as f:
        gui_specs = yaml.load(f)

    run_main(title, spec_test_dir, ctrl_specs, gui_specs)


if __name__ == '__main__':
    start_gui()
