"""
Define the Symbol class

Separate file because it depends on many other files, so we try to simplify
the circular dependencies.
"""

from __future__ import annotations  # Allows forward declarations
from typing import TYPE_CHECKING, Any, Union, Optional, Type
# ads.Connection relies on structs.AdsSymbol (but type hints only), so use
# this if to only include it when type hinting (False during execution)
if TYPE_CHECKING:
    from .ads import Connection
import re

from .pyads_ex import adsGetSymbolInfo
from . import constants
# We want to access all constants, so use package notation


class AdsSymbol:
    """Object that points to an ADS variable

    Contains index group, index offset, name, symbol type, comment of ADS
    symbol. Also remembers a reference to a Connection to be able to
    read/write directly.

    :param index_group: Index group of symbol
    :param index_offset: Index offset of symbol
    :param name: Name of symbol
    :param symtype: String representation of symbol type
    :param comment: Comment of symbol

    """

    def __init__(self,
                 plc: Connection,
                 name: Optional[str] = None,
                 index_group: Optional[int] = None,
                 index_offset: Optional[int] = None,
                 symtype: Optional[Union[Type, str]] = None,
                 comment=None):
        """Create AdsSymbol instance

        Specify either the variable name or the index_group _and_
        index_offset so the symbol can be located.
        If the name was specified but not all other attributes were,
        the other attributes will be looked up from the connection.
        `symtype` can be a PLCTYPE_* constant or a string representing a PLC
        type (e.g. 'LREAL').

        The virtual property `value` can be used to read from and write to
        the symbol.

        :param plc: Connection instance
        :param name:
        :param index_group:
        :param index_offset:
        :param symtype:
        :param comment:

        """
        self._plc = plc

        do_lookup = True

        if index_group is None or index_offset is None or symtype is None:
            if name is None:
                raise ValueError('Please specify either `name`, or '
                                 '`index_group`, `index_offset` and '
                                 'symtype')
            else:
                self.name = name
        else:
            self.index_offset = index_offset
            self.index_group = index_group
            self.name = name
            self.comment = comment
            do_lookup = False  # Have what we need already

        if do_lookup:
            info = adsGetSymbolInfo(self._plc.port, self._plc.ams_addr,
                                    name)

            self.index_group = info.iGroup
            self.index_offset = info.iOffs
            self.comment = comment
            symtype = info.type_name  # Type name, e.g. 'LREAL'

        if isinstance(symtype, str):
            self.type_name = symtype  # Store human-readable type name
            self.symtype = self.get_type_from_str(symtype)
        else:
            self.type_name = symtype.__class__  # Try to find human-readable
            self.symtype = symtype

    def read(self) -> Any:
        """Read the current value of this symbol"""
        return self._plc.read(self.index_group, self.index_offset,
                              self.symtype)

    def write(self, new_value: Any):
        """Write a new value to the symbol"""
        if self._handle:
            return self._plc.write_by_name(self.name, new_value, self.symtype,
                                           handle=self._handle)
        return self._plc.write(self.index_group, self.index_offset,
                               new_value, self.symtype)

    @property
    def value(self):
        return self.read()

    @value.setter
    def value(self, new_value):
        self.write(new_value)

    def __repr__(self):
        """Debug string"""
        t = type(self)
        return '<{}.{} object at {}, name: {}, type: {}>'.format(
            t.__module__, t.__qualname__, hex(id(self)),
            self.name, self.type_name)

    @staticmethod
    def get_type_from_str(type_str: str) -> Optional[Type]:
        """Get PLCTYPE_* from PLC name string

        If PLC name could not be mapped, return None. This is done on
        purpose to prevent a program from crashing when an unusable symbol
        is found. Instead, exceptions will be thrown when this unmapped
        symbol is read/written.
        """

        # If simple scalar
        plc_name = 'PLCTYPE_' + type_str
        if hasattr(constants, plc_name):
            # Map e.g. 'LREAL' to 'PLCTYPE_LREAL' directly based on the name
            return getattr(constants, plc_name)

        # If array/matrix (an 1D array is also called a matrix)
        reg_match = re.match(r'matrix_(\d+)_(.*)_T', type_str)
        if reg_match is not None:

            groups = reg_match.groups()
            size = int(groups[0])
            scalar_type_str = groups[1]

            if scalar_type_str in constants.PLC_ARRAY_MAP:
                return constants.PLC_ARRAY_MAP[scalar_type_str](size)

        # We allow unmapped types at this point - Instead we will throw  an
        # error when they are being addressed

        return None