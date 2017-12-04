# -*- coding: utf-8 -*-

import Gpib


class GPIBDev(object):
    def __init__(self, bid, pad):
        self.dev = Gpib.Gpib(bid, pad)
        self.dev.clear()

    def query(self, cmd):
        self.dev.write(cmd)
        self._process_status(self.dev.ibsta())
        try:
            val = self.dev.read(len=2048)
        except Exception as e:
            print str(e)
            val = None
        return val

    def write(self, cmd):
        self.dev.write(cmd)
        self._process_status(self.dev.ibsta())

    def _process_status(self, sta):
        pass
