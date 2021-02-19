import pyads
from pyads.ads import PLCDataType, PLCSimpleDataType
from ctypes import Array, c_uint8
from typing import Union, Type


def test(datatype: Type[Union[Array, "PLCSimpleDataType"]]) -> None:
    return None

test(str)