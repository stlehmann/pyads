# -*- coding: utf-8 -*-
"""Utility functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:53
:last modified by: Stefan Lehmann
:last modified time: 2018-07-12 14:11:12

"""
import sys
from ctypes import c_ubyte


def platform_is_linux():
    # type: () -> bool
    """Return True if current platform is Linux or Mac OS."""
    return sys.platform.startswith('linux') or \
        sys.platform.startswith('darwin')


def platform_is_windows():
    # type: () -> bool
    """Return True if current platform is Windows."""
    return sys.platform == 'win32'
