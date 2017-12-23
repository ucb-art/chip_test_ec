# -*- coding: utf-8 -*-

"""This module defines various basic classes/methods used by everything."""

import logging


class LoggingBase(object):
    """This is a base class that provides a log_msg() methodd for easy logging.
    """
    def __init__(self) -> None:
        self._logger = logging.getLogger(self.get_full_qualified_name())

    @classmethod
    def get_full_qualified_name(cls) -> str:
        """Returns the fully qualified class name of this class."""
        return cls.__module__ + '.' + cls.__name__

    def log_msg(self, msg: str, level: int = logging.DEBUG, disp: bool = False) -> None:
        """Logs the given message.

        Parameters
        ----------
        msg : str
            the message to log.
        level : int
            the logging level.
        disp : bool
            True to display the message on stdout.
        """
        self._logger.log(level=level, msg=msg)
        if disp:
            print(msg)
