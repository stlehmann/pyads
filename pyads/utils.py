"""Utility functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53

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


def platform_is_freebsd() -> bool:
    """Return True if current platform is FreeBSD."""
    return sys.platform.startswith("freebsd")


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


def decode_ads(message: bytes) -> str:
    """
    Decode a string that in encoded in the format used by ADS.

    From Beckhoff documentation: 'A STRING constant is a string enclosed by
    single quotation marks. The characters are encoded according to the Windows
    1252 character set. As a subset of Windows-1252, the character set of
    ISO/IEC 8859-1 is supported.'
    """
    return message.decode("windows-1252").strip(" \t\n\r\0")


def find_wstring_null_terminator(data: bytearray) -> Optional[int]:
    """Find null-terminator in WSTRING (UTF-16) data.

    :return: None if no null-terminator was found, else the index of the null-terminator

    """
    for ix in range(1, len(data), 2):
        if (data[ix - 1], data[ix]) == (0, 0):
            return ix - 1
    else:
        return None
