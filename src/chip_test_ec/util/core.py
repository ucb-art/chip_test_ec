# -*- coding: utf-8 -*-

"""This module contains various utility classes and methods."""

from typing import Any

import importlib


def import_class(module_name: str, cls_name: str) -> Any:
    cls_module = importlib.import_module(module_name)
    return getattr(cls_module, cls_name)
