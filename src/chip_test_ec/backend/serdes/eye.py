# -*- coding: utf-8 -*-

from typing import Dict, Any

import abc
import bisect

from ...gui.base.threads import WorkerThread
from ..core import Controller


class StopException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)


class EyePlotBase(object, metaclass=abc.ABCMeta):
    """A class used to plot eye diagram."""
    def __init__(self, thread: WorkerThread, ctrl: Controller, config: Dict[str, Any]):
        self.thread = thread
        self.ctrl = ctrl
        self.config = config

    @abc.abstractmethod
    def set_delay(self, val: int):
        pass

    @abc.abstractmethod
    def set_offset(self, val: int):
        pass

    @abc.abstractmethod
    def read_error(self, ber: float, max_err: int) -> int:
        return 0

    def run(self):
        ber = self.config['ber']
        max_err = self.config['max_err']

        tvec = list(range(*self.config['t_range']))
        yvec = list(range(*self.config['y_range']))

        num_y = len(yvec)
        if 'y_guess' in self.config:
            guess_idx = bisect.bisect_left(yvec, self.config['y_guess'])
        else:
            guess_idx = num_y // 2

        try:
            for t_idx, tval in enumerate(tvec):
                if self.thread.stop:
                    raise StopException('Stop signal received.')
                # first, measure BER at guessed offset
                self.set_delay(tval)
                self.set_offset(yvec[guess_idx])
                err_cnt = self.read_error(ber, max_err)
                self.thread.send(dict(t_idx=t_idx, y_idx=guess_idx, err_cnt=err_cnt))

                if err_cnt == 0:
                    # the guessed offset is in the eye
                    # use binary search to find bottom eye edge
                    bot_edge_idx = self._bin_search_eye_edge(yvec, 0, guess_idx)
                    # mark all region below eye as max errors.
                    for idx in range(0, bot_edge_idx):
                        self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=max_err))
                    # use binary search to find top eye edge
                    top_edge_idx = self._bin_search_eye_edge(yvec, guess_idx + 1, num_y)
                    # mark all region above eye as max errors.
                    for idx in range(top_edge_idx + 1, num_y):
                        self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=max_err))
                else:
                    # the guessed offset is not in the eye.
                    # assume we are below the eye, linear search bottom edge
                    bot_edge_idx = self._lin_search_eye_edge(yvec, guess_idx + 1, num_y)
                    if bot_edge_idx < 0:
                        # we did not find bottom edge.  Try finding top edge
                        top_edge_idx = self._lin_search_eye_edge(yvec, guess_idx - 1, 0)
                        if top_edge_idx < 0:
                            # we did not find top edge either.  This means we swept all possibilities,
                            # so just continue.
                            continue
                        else:
                            # we found top edge
                            # mark all region above eye as max errors.
                            for idx in range(top_edge_idx + 1, num_y):
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=max_err))
                            # use binary search to find bottom eye edge
                            bot_edge_idx = self._bin_search_eye_edge(yvec, 0, top_edge_idx)
                            # mark all region below eye as max errors.
                            for idx in range(0, bot_edge_idx):
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=max_err))
                    else:
                        # we found bottom edge
                        # mark all region below eye as max errors.
                        for idx in range(0, bot_edge_idx):
                            self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=max_err))
                        # use binary search to find top eye edge
                        top_edge_idx = self._bin_search_eye_edge(yvec, bot_edge_idx + 1, num_y)
                        # mark all region above eye as max errors.
                        for idx in range(top_edge_idx + 1, num_y):
                            self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=max_err))

                # mark all region in the eye as no errors.
                for idx in range(bot_edge_idx + 1, top_edge_idx):
                    self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=0))

                # update guessed offset
                guess_idx = (bot_edge_idx + top_edge_idx) // 2

        except StopException:
            pass

    def _bin_search_eye_edge(self, yvec, bot_idx, top_idx):
        return 0

    def _lin_search_eye_edge(self, yvec, start_idx, stop_idx):
        return 0
