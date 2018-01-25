# -*- coding: utf-8 -*-

from typing import Dict, Any, Tuple

import abc
import time
import math
import bisect

from ...gui.base.threads import WorkerThread
from ...util.search import BinaryIterator
from ...math.serdes import get_ber_list
from ..core import Controller


class StopException(Exception):
    def __init__(self):
        Exception.__init__(self, 'Stop signal received.')


class EyePlotBase(object, metaclass=abc.ABCMeta):
    """A class used to plot eye diagram."""
    def __init__(self, thread: WorkerThread, ctrl: Controller, config: Dict[str, Any]):
        self.thread = thread
        self.ctrl = ctrl

        self.max_ber = config['max_ber']
        self.y_name = config['y_name']
        self.y_guess = config['y_guess']
        self.is_pattern = config['is_pattern']
        self.pat_data = config['pat_data']
        self.pat_len = len(self.pat_data)
        self.tvec = list(range(config['t_start'], config['t_stop'], config['t_step']))
        self.yvec = list(range(config['y_start'], config['y_stop'], config['y_step']))
        self.targ_ber = config['ber']
        self.data_rate = config['data_rate']
        confidence = config['confidence']
        self.nerr_max = config.get('nerr_max', 10)

        self.nbits_meas = int(math.ceil(-math.log(1.0 - confidence) / self.targ_ber))
        self.time_meas = self.nbits_meas / self.data_rate
        self.max_err_val = (self.max_ber, self.nbits_meas, self.nbits_meas)
        self.ideal_val = (self.targ_ber, 0, self.nbits_meas)
        self.ber_table = get_ber_list(confidence, self.nbits_meas, self.nerr_max, self.targ_ber * 1e-3)

    @abc.abstractmethod
    def get_delay(self):
        return 0

    @abc.abstractmethod
    def set_delay(self, val: int):
        pass

    @abc.abstractmethod
    def get_offset(self):
        return 0

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

    def read_error(self) -> Tuple[float, int, int]:
        if self.thread.stop:
            raise StopException()
        self.init_error_meas(self.is_pattern)
        if self.thread.stop:
            raise StopException()

        if self.is_pattern:
            bits_read = 0
            cnt = 0
            while bits_read < self.nbits_meas and (cnt <= self.nerr_max or cnt / bits_read < self.max_ber):
                if self.thread.stop:
                    raise StopException()
                output = self.read_output()
                for char1, char2 in zip(output, self.pat_data):
                    if char1 != char2:
                        cnt += 1
                cnt += abs(len(output) - self.pat_len)
                bits_read += self.pat_len
        else:
            cnt = 0
            if self.thread.stop:
                raise StopException()
            t_start = time.time()
            cnt += self.read_error_count()
            t_dur = time.time() - t_start
            bits_read = t_dur * self.data_rate
            while t_dur < self.time_meas and (cnt <= self.nerr_max or cnt / bits_read < self.max_ber):
                if self.thread.stop:
                    raise StopException()
                cnt += self.read_error_count()
                t_dur = time.time() - t_start
                bits_read = t_dur * self.data_rate
            bits_read = int(bits_read)

        if cnt <= self.nerr_max:
            ber = self.ber_table[cnt]
        else:
            ber = cnt / bits_read

        return ber, cnt, bits_read

    def run(self):
        init_delay = self.get_delay()
        init_offset = self.get_offset()
        num_y = len(self.yvec)
        guess_idx = num_y // 2 if self.y_guess is None else bisect.bisect_left(self.yvec, self.y_guess)
        guess_idx = max(0, min(guess_idx, len(self.yvec) - 1))
        try:
            for t_idx, tval in enumerate(self.tvec):
                if self.thread.stop:
                    raise StopException()
                # first, measure BER at guessed offset
                self.thread.send(dict(t_idx=t_idx, y_idx=guess_idx, val=(0, -1, 0)))
                self.set_delay(tval)
                self.set_offset(self.yvec[guess_idx])
                val = self.read_error()
                mark_set = {guess_idx}
                self.thread.send(dict(t_idx=t_idx, y_idx=guess_idx, val=val))

                if val[1] == 0:
                    # the guessed offset is in the eye
                    # use binary search to find bottom eye edge
                    bot_edge_idx = self._bin_search_eye_edge(mark_set, t_idx, 0, guess_idx, True)
                    # mark all region below eye as max errors.
                    for idx in range(0, bot_edge_idx):
                        if idx not in mark_set:
                            self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.max_err_val))
                    # use binary search to find top eye edge
                    top_edge_idx = self._bin_search_eye_edge(mark_set, t_idx, guess_idx + 1, num_y, False)
                    # mark all region above eye as max errors.
                    for idx in range(top_edge_idx + 1, num_y):
                        if idx not in mark_set:
                            self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.max_err_val))
                else:
                    # the guessed offset is not in the eye.
                    # assume we are below the eye, linear search bottom edge
                    edge_idx, is_bot_edge = self._flood_search_eye_edge(mark_set, t_idx, 0, num_y, guess_idx, guess_idx)
                    if edge_idx < 0:
                        # we did not find any edge, and we swept all possibilities.  So just continue
                        continue
                    elif is_bot_edge:
                        # we found bottom edge
                        bot_edge_idx = edge_idx
                        # mark all region below eye as max errors.
                        for idx in range(0, bot_edge_idx):
                            if idx not in mark_set:
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.max_err_val))
                        # use binary search to find top eye edge
                        top_edge_idx = self._bin_search_eye_edge(mark_set, t_idx, bot_edge_idx + 1, num_y, False)
                        # mark all region above eye as max errors.
                        for idx in range(top_edge_idx + 1, num_y):
                            if idx not in mark_set:
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.max_err_val))
                    else:
                        # we found top edge
                        top_edge_idx = edge_idx
                        # we found top edge
                        # mark all region above eye as max errors.
                        for idx in range(top_edge_idx + 1, num_y):
                            if idx not in mark_set:
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.max_err_val))
                        # use binary search to find bottom eye edge
                        bot_edge_idx = self._bin_search_eye_edge(mark_set, t_idx, 0, top_edge_idx, True)
                        # mark all region below eye as max errors.
                        for idx in range(0, bot_edge_idx):
                            if idx not in mark_set:
                                self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.max_err_val))

                # mark all region in the eye as no errors.
                for idx in range(bot_edge_idx + 1, top_edge_idx):
                    self.thread.send(dict(t_idx=t_idx, y_idx=idx, val=self.ideal_val))

                # update guessed offset
                guess_idx = (bot_edge_idx + top_edge_idx) // 2

        except StopException:
            pass
        finally:
            self.set_delay(init_delay)
            self.set_offset(init_offset)

    def _bin_search_eye_edge(self, mark_set, t_idx, bot_idx, top_idx, eye_on_top):
        bin_iter = BinaryIterator(bot_idx, top_idx)
        edge_idx = top_idx if eye_on_top else bot_idx - 1
        while bin_iter.has_next():
            if self.thread.stop:
                raise StopException()

            cur_idx = bin_iter.get_next()
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, val=(0, -1, 0)))
            self.set_offset(self.yvec[cur_idx])
            if self.thread.stop:
                raise StopException()
            val = self.read_error()
            mark_set.add(cur_idx)
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, val=val))

            if val[1] == 0:
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

    def _flood_search_eye_edge(self, mark_set, t_idx, start_idx, stop_idx, bot_idx, top_idx):
        cur_dir = -1
        while bot_idx > start_idx or top_idx < stop_idx - 1:
            if cur_dir < 0 and bot_idx > start_idx or top_idx == stop_idx - 1:
                cur_idx = bot_idx - 1
            else:
                cur_idx = top_idx + 1

            if self.thread.stop:
                raise StopException()

            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, val=(0, -1, 0)))
            self.set_offset(self.yvec[cur_idx])
            if self.thread.stop:
                raise StopException()
            val = self.read_error()
            mark_set.add(cur_idx)
            self.thread.send(dict(t_idx=t_idx, y_idx=cur_idx, val=val))

            if val[1] == 0:
                # found edge
                return cur_idx, cur_idx > top_idx

            bot_idx = min(bot_idx, cur_idx)
            top_idx = max(top_idx, cur_idx)
            cur_dir = -cur_dir

        return -1, False


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
        return self.nbits_meas

    def read_output(self):
        time.sleep(0.05)
        if self._in_eye():
            return self.pat_data
        return ''.join(('0' if char == '1' else '1' for char in self.pat_data))
