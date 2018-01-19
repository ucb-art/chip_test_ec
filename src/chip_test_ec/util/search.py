# -*- coding: utf-8 -*-

"""This module provides search related utilities.
"""

from typing import Optional, Any

from collections import namedtuple

MinCostResult = namedtuple('MinCostResult', ['x', 'xmax', 'vmax', 'nfev'])


class BinaryIterator(object):
    """A class that performs binary search over integers.
    This class supports both bounded or unbounded binary search, and
    you can also specify a step size.
    Parameters
    ----------
    low : int
        the lower bound (inclusive).
    high : Optional[int]
        the upper bound (exclusive).  None for unbounded binary search.
    step : int
        the step size.  All return values will be low + N * step
    """

    def __init__(self, low, high, step=1):
        # type: (int, Optional[int], int) -> None

        if not isinstance(low, int) or not isinstance(step, int):
            raise ValueError('low and step must be integers.')

        self._offset = low
        self._step = step
        self._low = 0

        if high is not None:
            if not isinstance(high, int):
                raise ValueError('high must be None or integer.')

            nmax = (high - low) // step
            if low + step * nmax < high:
                nmax += 1
            self._high = nmax
            self._current = (self._low + self._high) // 2
        else:
            self._high = None
            self._current = self._low

        self._save_marker = None
        self._save_info = None

    def set_current(self, val):
        # type: (int) -> None
        """Set the value of the current marker."""
        if (val - self._offset) % self._step != 0:
            raise ValueError('value %d is not multiple of step size.' % val)
        self._current = (val - self._offset) // self._step

    def has_next(self):
        # type: () -> bool
        """returns True if this iterator is not finished yet."""
        return self._high is None or self._low < self._high

    def get_next(self):
        # type: () -> int
        """Returns the next value to look at."""
        return self._current * self._step + self._offset

    def up(self):
        # type: () -> None
        """Increment this iterator."""
        self._low = self._current + 1

        if self._high is not None:
            self._current = (self._low + self._high) // 2
        else:
            if self._current > 0:
                self._current *= 2
            else:
                self._current = 1

    def down(self):
        # type: () -> None
        """Decrement this iterator."""
        self._high = self._current
        self._current = (self._low + self._high) // 2

    def save(self):
        # type: () -> None
        """Save the current index"""
        self._save_marker = self._current

    def save_info(self, info):
        # type: (Any) -> None
        """Save current information."""
        self.save()
        self._save_info = info

    def get_last_save(self):
        # type: () -> Optional[int]
        """Returns the last saved index."""
        if self._save_marker is None:
            return None
        return self._save_marker * self._step + self._offset

    def get_last_save_info(self):
        # type: () -> Any
        """Return last save information."""
        return self._save_info
