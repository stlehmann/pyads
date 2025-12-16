"""Utility functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53

"""
import functools
import sys
import warnings
import os
from .structs import SAdsSymbolEntry
from .constants import PLC_STRING_TYPE_NAME, PLC_DEFAULT_STRING_SIZE

from typing import Callable, Any, Optional


def platform_is_beckhoff_rt_linux() -> bool:
    """Workaround to identify Beckhoff RT-Linux as a FreeBSD-based solution instead of Linux."""
    return os.path.exists("/usr/bin/TcSystemServiceUm")


def platform_is_linux() -> bool:
    """Return True if current platform is Linux or Mac OS."""
    return (sys.platform.startswith("linux") or sys.platform.startswith("darwin")) and not platform_is_beckhoff_rt_linux()


def platform_is_windows() -> bool:
    """Return True if current platform is Windows."""
    # cli being .NET (IronPython)
    return sys.platform == "win32" or sys.platform == "cli"


def platform_is_freebsd() -> bool:
    """Return True if current platform is FreeBSD."""
    return sys.platform.startswith("freebsd") or platform_is_beckhoff_rt_linux()


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

def get_num_of_chars(symbol_type_str: SAdsSymbolEntry.symbol_type) -> int:
    """Gets the number of characters in a Beckhoff string using the symbol type str.

    TODO: Find this information some other way without string manipulation of the symbol type?

    Args:
        symbol_type_str (SAdsSymbolEntry.symbol_type): Symbol type of a string, wstring, or a string array

    Returns:
        num_characters (int): The number of characters im the string
    """

    # Find "STRING" in type 
    pos_of_string_in_name = symbol_type_str.upper().find(PLC_STRING_TYPE_NAME)

    # If not string return -1
    if pos_of_string_in_name == -1:
        return(-1)

    # Generate start index based on the position of PLC_STRING_TYPE_NAME in the array
    start_index = pos_of_string_in_name + len(PLC_STRING_TYPE_NAME) + 1

    # Return the value cast as int
    try:
        return(int(symbol_type_str[start_index:-1]))
    except ValueError:
        return(PLC_DEFAULT_STRING_SIZE)
