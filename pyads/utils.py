# -*- coding: utf-8 -*-
"""Utility functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:53
:last modified by: Stefan Lehmann
:last modified time: 2018-07-12 14:11:12

"""
import functools
import sys
import warnings

from typing import Callable, Any, Optional


def platform_is_linux() -> bool:
    """Return True if current platform is Linux or Mac OS."""
    return sys.platform.startswith("linux") or sys.platform.startswith("darwin")


def platform_is_windows() -> bool:
    """Return True if current platform is Windows."""
    # cli being .NET (IronPython)
    return sys.platform == "win32" or sys.platform == "cli"


def deprecated(message: Optional[str] = None) -> Callable:
    """Decorator for deprecated functions.

    Shows a deprecation warning with the given message if the
    decorated function is called.

    """
    if message is None:
        message = "Deprecated. This function will not be available in future versions."

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Callable:
            warnings.warn(message, DeprecationWarning)  # type: ignore
            return func(*args, **kwargs)

        return wrapper

    return decorator
