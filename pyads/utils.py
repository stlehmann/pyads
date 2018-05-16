#!-*- coding: utf-8 -*-
"""
:author: Stefan Lehmann <stefan.st.lehmann@gmail.com>

"""
import sys
from ctypes import c_ubyte


def platform_is_linux():
    """Return True if current platform is Linux or Mac OS."""
    return sys.platform.startswith('linux') or \
        sys.platform.startswith('darwin')


def platform_is_windows():
    """Return True if current platform is Windows."""
    return sys.platform == 'win32'
