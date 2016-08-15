#!-*- coding: utf-8 -*-
# from .pyads import *
from .ads import AmsAddr, open_port, close_port, get_local_address

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
