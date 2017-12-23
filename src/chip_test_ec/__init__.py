# -*- coding: utf-8 -*-

"""This package contains various subpackages creating a chip testing GUI in Python."""

# Setup logging
import os
import logging.config

log_conf_fname = 'logging_config.ini'
if os.path.isfile(log_conf_fname):
    logging.config.fileConfig(log_conf_fname)
