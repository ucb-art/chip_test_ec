# -*- coding: utf-8 -*-

import yaml

from chip_test_ec.core import run_main


def start_gui():
    conf_path = 'conf_sample'
    ctrl_specs_fname = 'specs_sample/controller.yaml'
    gui_specs_fname = 'specs_sample/main_gui.yaml'

    with open(ctrl_specs_fname, 'r') as f:
        ctrl_specs = yaml.load(f)

    with open(gui_specs_fname, 'r') as f:
        gui_specs = yaml.load(f)

    run_main(conf_path, ctrl_specs, gui_specs)


if __name__ == '__main__':
    start_gui()
