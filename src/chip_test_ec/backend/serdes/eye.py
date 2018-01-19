# -*- coding: utf-8 -*-

from typing import Dict, Any

import abc
import bisect

from ...gui.base.threads import WorkerThread
from ...util.search import BinaryIterator
from ..core import Controller


class StopException(Exception):
    def __init__(self):
        Exception.__init__(self, 'Stop signal received.')


class EyePlotBase(object, metaclass=abc.ABCMeta):
    """A class used to plot eye diagram."""
    def __init__(self, thread: WorkerThread, ctrl: Controller, config: Dict[str, Any]):
        self.thread = thread
        self.ctrl = ctrl

        self.ber = config['ber']
        self.max_err = config['max_err']
        self.y_guess = config.get('y_guess', None)
        self.tvec = list(range(*config['t_range']))
        self.yvec = list(range(*config['y_range']))

    @abc.abstractmethod
    def set_delay(self, val: int):
        pass

    @abc.abstractmethod
    def set_offset(self, val: int):
        pass

    @abc.abstractmethod
    def read_error(self) -> int:
        return 0

    def run(self):
        num_y = len(self.yvec)
        guess_idx = num_y // 2 if self.y_guess is None else bisect.bisect_left(self.yvec, self.y_guess)

        try:
            for t_idx, tval in enumerate(self.tvec):
                if self.thread.stop:
                    raise StopException()
                # first, measure BER at guessed offset
                self.set_delay(tval)
                self.set_offset(self.yvec[guess_idx])
                err_cnt = self.read_error()
                self.thread.send(dict(t_idx=t_idx, y_idx=guess_idx, err_cnt=err_cnt))

                if err_cnt == 0:
                    # the guessed offset is in the eye
                    # use binary search to find bottom eye edge
                    bot_edge_idx = self._bin_search_eye_edge(t_idx, 0, guess_idx, True)
                    # mark all region below eye as max errors.
                    for idx in range(0, bot_edge_idx - 1):
                        self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=self.max_err))
                    # use binary search to find top eye edge
                    top_edge_idx = self._bin_search_eye_edge(t_idx, guess_idx + 1, num_y, False)
                    # mark all region above eye as max errors.
                    for idx in range(top_edge_idx + 2, num_y):
                        self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=self.max_err))
                else:
                    # the guessed offset is not in the eye.
                    # assume we are below the eye, linear search bottom edge
                    bot_edge_idx = self._lin_search_eye_edge(t_idx, guess_idx + 1, num_y)
                    if bot_edge_idx < 0:
                        # we did not find bottom edge.  Try finding top edge
                        top_edge_idx = self._lin_search_eye_edge(t_idx, guess_idx - 1, -1)
                        if top_edge_idx < 0:
                            # we did not find top edge either.  This means we swept all possibilities,
                            # so just continue.
                            continue
                        else:
                            # we found top edge
                            # mark all region above eye as max errors.
                            for idx in range(top_edge_idx + 2, num_y):
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=self.max_err))
                            # use binary search to find bottom eye edge
                            bot_edge_idx = self._bin_search_eye_edge(t_idx, 0, top_edge_idx, True)
                            # mark all region below eye as max errors.
                            for idx in range(0, bot_edge_idx - 1):
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=self.max_err))
                    else:
                        # we found bottom edge
                        # mark all region below eye as max errors.
                        for idx in range(0, bot_edge_idx - 1):
                            self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=self.max_err))
                        # use binary search to find top eye edge
                        top_edge_idx = self._bin_search_eye_edge(t_idx, bot_edge_idx + 1, num_y, False)
                        # mark all region above eye as max errors.
                        for idx in range(top_edge_idx + 2, num_y):
                            self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=self.max_err))

                # mark all region in the eye as no errors.
                for idx in range(bot_edge_idx + 1, top_edge_idx):
                    self.thread.send(dict(t_idx=t_idx, y_idx=idx, err_cnt=0))

                # update guessed offset
                guess_idx = (bot_edge_idx + top_edge_idx) // 2

        except StopException:
            pass

    def _bin_search_eye_edge(self, t_idx, bot_idx, top_idx, eye_on_top):
        bin_iter = BinaryIterator(bot_idx, top_idx)
        edge_idx = top_idx if eye_on_top else bot_idx - 1
        while bin_iter.has_next():
            if self.thread.stop:
                raise StopException()

            cur_idx = bin_iter.get_next()
            self.set_offset(self.yvec[cur_idx])

            err_cnt = self.read_error()
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, err_cnt=err_cnt))

            if err_cnt == 0:
                edge_idx = cur_idx
                if eye_on_top:
                    bin_iter.down()
                else:
                    bin_iter.up()
            elif eye_on_top:
                bin_iter.up()
            else:
                bin_iter.down()

        return edge_idx

    def _lin_search_eye_edge(self, t_idx, start_idx, stop_idx):
        step = 1 if stop_idx >= start_idx else -1
        for cur_idx in range(start_idx, stop_idx, step):
            if self.thread.stop:
                raise StopException()

            self.set_offset(self.yvec[cur_idx])

            err_cnt = self.read_error()
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, err_cnt=err_cnt))

            if err_cnt == 0:
                return cur_idx
        return -1
