# -*- coding: utf-8 -*-

from typing import Dict, Any, List

import abc
import time
import bisect

import numpy as np

from ...gui.base.threads import WorkerThread
from ..core import Controller


class StopException(Exception):
    def __init__(self):
        Exception.__init__(self, 'Stop signal received.')


class TracePlotBase(object, metaclass=abc.ABCMeta):
    """A class used to plot trace using subsampling."""
    def __init__(self, thread: WorkerThread, ctrl: Controller, config: Dict[str, Any]):
        self.thread = thread
        self.ctrl = ctrl

        self.num_samp = config['num_samp']
        self.y_guess = config['y_guess']
        self.tvec = list(range(config['t_start'], config['t_stop'], config['t_step']))
        self.yvec = list(range(config['y_start'], config['y_stop'], config['y_step']))

        tper = 1e12 / config['data_rate']
        output_len = config['output_len']
        num_des = config['num_des']
        parity = config['parity']
        self.str_idx_list = list(range(output_len - 1 - parity, -1, -num_des))
        self.toff_list = [idx * tper for idx in range(parity, output_len, num_des)]

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
    def init_meas(self) -> None:
        pass

    @abc.abstractmethod
    def read_output(self) -> str:
        return ''

    def read_trace(self) -> List[int]:
        if self.thread.stop:
            raise StopException()
        self.init_meas()

        num_idx = len(self.str_idx_list)
        ans = [0] * num_idx
        zero_map = [0] * num_idx
        one_map = [0] * num_idx
        for _ in range(self.num_samp):
            if self.thread.stop:
                raise StopException()

            out_str = self.read_output()
            for cur_idx in range(num_idx):
                str_idx = self.str_idx_list[cur_idx]
                if out_str[str_idx] == '0':
                    zero_map[cur_idx] += 1
                else:
                    one_map[cur_idx] += 1

        for cur_idx in range(num_idx):
            if zero_map[cur_idx] == 0:
                ans[str_idx] = 1
            elif one_map[cur_idx] == 0:
                ans[str_idx] = -1

        return ans

    def _send_focus(self, t_idx, y_idx):
        t0 = self.tvec[t_idx]
        yval = self.yvec[y_idx]
        for toff in self.toff_list:
            self.thread.send(dict(tval=t0 + toff, yval=yval, val=2))

    def _send_mark(self, t_idx, y_idx, cur_idx, otype):
        t0 = self.tvec[t_idx]
        yval = self.yvec[y_idx]
        toff = self.toff_list[cur_idx]
        self.thread.send(dict(tval=t0 + toff, yval=yval, val=otype))

    def eval_y(self, t_idx, y_idx, bot_edge_intv, top_edge_intv):
        self.set_offset(self.yvec[y_idx])
        self._send_focus(t_idx, y_idx)
        if self.thread.stop:
            raise StopException()

        output_types = self.read_trace()
        for cur_idx, (bintv, tintv, otype) in enumerate(zip(bot_edge_intv, top_edge_intv, output_types)):
            self._send_mark(t_idx, y_idx, cur_idx, otype)
            if otype < 0:
                bintv[0] = max(bintv[0], y_idx)
                tintv[0] = max(tintv[0], y_idx + 1)
            elif otype == 0:
                bintv[1] = min(bintv[1], y_idx)
                tintv[0] = max(tintv[0], y_idx + 1)
            else:
                bintv[1] = min(bintv[1], y_idx)
                tintv[1] = min(tintv[1], y_idx + 1)

    def find_edge(self, is_bot, t_idx, cur_idx, bot_edge_intv, top_edge_intv, guess_idx):
        cur_intv = bot_edge_intv[cur_idx] if is_bot else top_edge_intv[cur_idx]
        if cur_intv[1] == cur_intv[0] + 1:
            return

        # evaluate at guess index
        guess_idx = max(cur_intv[0], min(guess_idx, cur_intv[1] - 1))
        self.eval_y(t_idx, guess_idx, bot_edge_intv, top_edge_intv)
        # binary search to find edge of current index
        while cur_intv[1] > cur_intv[0] + 1:
            y_idx = (cur_intv[1] + cur_intv[0]) // 2
            self.eval_y(t_idx, y_idx, bot_edge_intv, top_edge_intv)

    def run(self):
        init_delay = self.get_delay()
        init_offset = self.get_offset()
        num_y = len(self.yvec)
        guess_idx = num_y // 2 if self.y_guess is None else bisect.bisect_left(self.yvec, self.y_guess)
        guess_idx = max(0, min(guess_idx, len(self.yvec) - 1))

        num_idx = len(self.str_idx_list)
        try:
            for t_idx, tval in enumerate(self.tvec):
                if self.thread.stop:
                    raise StopException()

                # set delay
                self.set_delay(tval)

                bot_edge_intv = [[0, num_y] for _ in range(num_idx)]
                top_edge_intv = [[0, num_y] for _ in range(num_idx)]

                for cur_idx in range(num_idx):
                    # find bottom edge
                    self.find_edge(True, t_idx, cur_idx, bot_edge_intv, top_edge_intv, guess_idx)
                    # find top edge
                    self.find_edge(False, t_idx, cur_idx, bot_edge_intv, top_edge_intv, guess_idx)
                    bot_edge = bot_edge_intv[cur_idx][0]
                    top_edge = top_edge_intv[cur_idx][0]
                    for y_idx in range(0, bot_edge + 1):
                        self._send_mark(t_idx, y_idx, cur_idx, -1)
                    for y_idx in range(bot_edge + 1, top_edge):
                        self._send_mark(t_idx, y_idx, cur_idx, 0)
                    for y_idx in range(top_edge):
                        self._send_mark(t_idx, y_idx, cur_idx, 1)
        except StopException:
            pass
        finally:
            self.set_delay(init_delay)
            self.set_offset(init_offset)


class TracePlotFake(TracePlotBase):
    """A fake eye diagram plotting class used for testing only."""

    def __init__(self, thread: WorkerThread, ctrl: Controller, config: Dict[str, Any]):
        TracePlotBase.__init__(self, thread, ctrl, config)
        t0 = self.tvec[0]
        t1 = self.tvec[-1]
        y0 = self.yvec[0]
        y1 = self.yvec[-1]

        self.ym = (y1 + y0) / 2
        self.yper = t1 - t0
        self.tr_w = (y1 - y0) / 20
        self.amp = (y1 - y0) / 4
        self.t_cur = t0
        self.y_cur = y0
        self.output_len = config['output_len']
        self.read_cnt = 0

    def get_delay(self):
        return self.t_cur

    def set_delay(self, val: int):
        self.t_cur = val

    def get_offset(self):
        return self.y_cur

    def set_offset(self, val: int):
        self.y_cur = val

    def init_meas(self):
        pass

    def read_output(self):
        self.read_cnt += 1
        time.sleep(0.05)
        output_list = ['0'] * self.output_len
        for toff, str_idx in zip(self.toff_list, self.str_idx_list):
            tcur = self.t_cur + toff
            ymin = self.ym + self.amp * np.sin(2 * np.pi * (tcur - self.tvec[0]) / self.yper) - self.tr_w / 2
            ymax = ymin + self.tr_w
            if self.y_cur <= ymin:
                output_list[str_idx] = '0'
            elif self.y_cur < ymax:
                output_list[str_idx] = str(self.read_cnt % 2)
            else:
                output_list[str_idx] = '1'

        return ''.join(output_list)
