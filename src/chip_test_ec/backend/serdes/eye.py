# -*- coding: utf-8 -*-

from typing import Dict, Any

import abc
import time
import math
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

        self.max_err = config['max_err']
        self.y_name = config['y_name']
        self.y_guess = config['y_guess']
        self.is_pattern = config['is_pattern']
        self.pat_data = config['pat_data']
        self.tvec = list(range(config['t_start'], config['t_stop'], config['t_step']))
        self.yvec = list(range(config['y_start'], config['y_stop'], config['y_step']))
        ber = config['ber']
        data_rate = config['data_rate']
        confidence = config['confidence']

        self.nbits_meas = int(math.ceil(-math.log(1.0 - confidence) / ber))
        self.time_meas = self.nbits_meas / data_rate

    @abc.abstractmethod
    def set_delay(self, val: int):
        pass

    @abc.abstractmethod
    def set_offset(self, val: int):
        pass

    @abc.abstractmethod
    def init_error_meas(self, is_pattern: bool) -> None:
        pass

    @abc.abstractmethod
    def read_error_count(self) -> int:
        return 0

    @abc.abstractmethod
    def read_output(self) -> str:
        return ''

    def read_error(self) -> int:
        self.init_error_meas(self.is_pattern)

        if self.is_pattern:
            bits_read = 0
            cnt = 0
            while bits_read < self.nbits_meas and cnt <= self.max_err:
                output = self.read_output()
                for char1, char2 in zip(output, self.pat_data):
                    if char1 != char2:
                        cnt += 1
                cnt += abs(len(output) - len(self.pat_data))
        else:
            cnt = 0
            t_start = time.time()
            while time.time() - t_start < self.time_meas and cnt <= self.max_err:
                cnt += self.read_error_count()

        return min(cnt, self.max_err)

    def run(self):
        num_y = len(self.yvec)
        guess_idx = num_y // 2 if self.y_guess is None else bisect.bisect_left(self.yvec, self.y_guess)
        guess_idx = max(0, min(guess_idx, len(self.yvec) - 1))

        try:
            for t_idx, tval in enumerate(self.tvec):
                if self.thread.stop:
                    raise StopException()
                # first, measure BER at guessed offset
                self.thread.send(dict(t_idx=t_idx, y_idx=guess_idx, err_cnt=-1))
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
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, err_cnt=-1))
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

            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, err_cnt=-1))
            self.set_offset(self.yvec[cur_idx])

            err_cnt = self.read_error()
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, err_cnt=err_cnt))

            if err_cnt == 0:
                return cur_idx
        return -1


class EyePlotFake(EyePlotBase):
    """A fake eye diagram plotting class used for testing only."""

    def __init__(self, thread: WorkerThread, ctrl: Controller, config: Dict[str, Any]):
        EyePlotBase.__init__(self, thread, ctrl, config)
        t0 = self.tvec[0]
        t1 = self.tvec[-1]
        y0 = self.yvec[0]
        y1 = self.yvec[-1]

        ta = 0.9 * t0 + 0.1 * t1
        tb = (t0 + t1) / 2
        tc = 0.1 * t0 + 0.9 * t1
        ya = 0.9 * y0 + 0.1 * y1
        yb = (y0 + y1) / 2
        yc = 0.1 * y0 + 0.9 * y1

        self.t_cur = t0
        self.y_cur = y0
        self.lower_bnd = [[(ya - yb) / (tb - ta), yb - ta * (ya - yb) / (tb - ta)],
                          [(yb - ya) / (tc - tb), ya - tb * (yb - ya) / (tc - tb)],
                          ]
        self.upper_bnd = [[(yc - yb) / (tb - ta), yb - ta * (yc - yb) / (tb - ta)],
                          [(yb - yc) / (tc - tb), yc - tb * (yb - yc) / (tc - tb)],
                          ]

    def set_delay(self, val: int):
        self.t_cur = val

    def set_offset(self, val: int):
        self.y_cur = val

    def init_error_meas(self, is_pattern: bool):
        pass

    def _in_eye(self):
        for m, b in self.lower_bnd:
            if self.t_cur * m + b > self.y_cur:
                return False
        for m, b in self.upper_bnd:
            if self.t_cur * m + b < self.y_cur:
                return False
        return True

    def read_error_count(self):
        time.sleep(0.05)
        if self._in_eye():
            return 0
        return self.max_err

    def read_output(self):
        time.sleep(0.05)
        if self._in_eye():
            return self.pat_data
        return ''.join(('0' if char == '1' else '1' for char in self.pat_data))
