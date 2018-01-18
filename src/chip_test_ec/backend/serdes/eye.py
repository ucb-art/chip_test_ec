# -*- coding: utf-8 -*-

import abc

from ...gui.base.threads import WorkerThread
from ..core import Controller


class EyePlotBase(object, metaclass=abc.ABCMeta):
    """A class used to plot eye diagram."""
    def __init__(self, thread: WorkerThread, ctrl: Controller):
        self.thread = thread
        self.ctrl = ctrl

    @abc.abstractmethod
    def set_delay(self, val: int):
        pass

    @abc.abstractmethod
    def read_error(self, tmeas_ms: int) -> int:
        return 0

    def plot_eye(self):
        pass