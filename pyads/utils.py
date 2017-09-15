#!-*- coding: utf-8 -*-
"""
:author: Stefan Lehmann <stefan.st.lehmann@gmail.com>

"""
import sys


def platform_is_linux():
    return sys.platform.startswith('linux') or \
           sys.platform.startswith('darwin')


def platform_is_windows():
    return sys.platform == 'win32'
