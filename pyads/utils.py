#!-*- coding: utf-8 -*-
"""
:author: Stefan Lehmann <stefan.st.lehmann@gmail.com>

"""
import sys
from ctypes import c_ubyte
from pyads.structs import SAmsNetId


def platform_is_linux():
    """Return True if current platform is Linux or Mac OS."""
    return sys.platform.startswith('linux') or \
        sys.platform.startswith('darwin')


def platform_is_windows():
    """Return True if current platform is Windows."""
    return sys.platform == 'win32'


def parse_ams_netid(ams_netid):
    """Parse an AmsNetId from *str* to *SAmsNetId*."""
    id_numbers = list(map(int, ams_netid.split('.')))

    if len(id_numbers) != 6:
        raise ValueError('no valid netid')

    # Fill the netId struct with data
    ams_netid_st = SAmsNetId()
    ams_netid_st.b = (c_ubyte * 6)(*id_numbers)
    return ams_netid_st

