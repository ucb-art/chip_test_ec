# -*- coding: utf-8 -*-

"""This module defines GPIBBase, the base class of all GPIB controllers.
"""


class GPIBBase(object):
    def __init__(self, bid, pad, timeout_ms=10000, use_visa=True):
        # check if visa works
        if use_visa:
            try:
                import visa
            except ImportError:
                visa = None
                print 'Failed to import visa, revert to GPIB'
                use_visa = False
        else:
            visa = None

        if visa is not None:
            self.rm = visa.ResourceManager()
            resources = self.rm.list_resources()
            sid = 'GPIB{0}::{1}::INSTR'.format(bid, pad)
            if sid not in resources:
                raise Exception('GPIB resource {0} not found.  Available resources are:\n{1}'.format(sid, resources))
            self.dev = self.rm.open_resource(sid)
            self.dev.timeout = timeout_ms
        else:
            from .GPIBDev import GPIBDev
            self.dev = GPIBDev(bid, pad)

    def query(self, cmd):
        return self.dev.query(cmd)

    def write(self, cmd):
        self.dev.write(cmd)
