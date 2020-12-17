"""
Define the Symbol class

Separate file because it depends on many other files, so we try to simplify
the circular dependencies.
"""

import re
from ctypes import sizeof
from typing import TYPE_CHECKING, Any, Optional, List, Tuple, Callable
from .pyads_ex import adsGetSymbolInfo
from .structs import NotificationAttrib
from . import constants  # To access all constants, use package notation
# ads.Connection relies on structs.AdsSymbol (but in type hints only), so use
# this 'if' to only include it when type hinting (False during execution)
if TYPE_CHECKING:
    from .ads import Connection  # pragma: no cover


class AdsSymbol:
    """Object that points to an ADS variable

    Contains index group, index offset, name, symbol type, comment of ADS
    symbol. Also remembers a reference to a Connection to be able to
    read/write directly.

    The virtual property `value` can be used to read from and write to
    the symbol.

    :ivar index_group: Index group of symbol
    :ivar index_offset: Index offset of symbol
    :ivar name: Name of symbol
    :ivar symbol_type: String representation of symbol type (PLC-style,
                     e.g. "LREAL")
    :ivar plc_type: ctypes type of variable (from constants.PLCTYPE_*)
    :ivar comment: Comment of symbol
    """

    def __init__(self,
                 plc: "Connection",
                 name: Optional[str] = None,
                 index_group: Optional[int] = None,
                 index_offset: Optional[int] = None,
                 symbol_type: Optional[str] = None,
                 comment=None):
        """Create AdsSymbol instance

        Specify either the variable name or the index_group **and**
        index_offset so the symbol can be located.
        If the name was specified but not all other attributes were,
        the other attributes will be looked up from the connection.
        `symbol_type` should be a string representing a PLC type (e.g.
        'LREAL').

        :param plc: Connection instance
        :param name:
        :param index_group:
        :param index_offset:
        :param symbol_type: PLC variable type (e.g. 'LREAL')
        :param comment:
        """
        self._plc = plc

        self._handles_list: List[Tuple[int, int]] = []  # Notification handles

        do_lookup = True

        if index_group is None or index_offset is None or symbol_type is None:
            if name is None:
                raise ValueError('Please specify either `name`, or '
                                 '`index_group`, `index_offset` and '
                                 'plc_type')
        else:
            # We have an address and the type, so we don't need to do a lookup
            do_lookup = False

        self.name = name
        self.index_offset = index_offset
        self.index_group = index_group
        self.symbol_type = symbol_type
        self.comment = comment

        if do_lookup:
            self.make_symbol_from_info()  # Perform remote lookup

        # Now `self._type_hint` must have a value, find the actual PLCTYPE
        # from it.
        # This is relevant for both lookup and full user definition.

        if self.symbol_type is not None:
            self.plc_type = self.get_type_from_str(self.symbol_type)
        else:
            # Set directly from user input
            self.plc_type = self.symbol_type  # type: Any

    def make_symbol_from_info(self):
        """Look up remaining info from the remote

        The name must already be present.
        Other values will already have a default value (mostly None).
        """
        info = adsGetSymbolInfo(self._plc._port, self._plc._adr, self.name)

        self.index_group = info.iGroup
        self.index_offset = info.iOffs
        if info.comment:
            self.comment = info.comment

        # info.dataType is an integer mapping to a type in
        # constants.ads_type_to_ctype.
        # However, this type ignores whether the variable is really an array!
        # So are not going to be using this and instead rely on the textual
        # type
        self.symbol_type = info.type_name  # Save the type as string

    def read_write_check(self):
        """Assert the current object is ready to read from/write to"""
        if self.plc_type is None:
            raise ValueError('Cannot read or write with invalid value for '
                             'plc_type: `{}`'.format(self.plc_type))

        if not self._plc or not self._plc.is_open:
            raise ValueError('Cannot read or write data with missing or '
                             'unopened Connection')

        if not isinstance(self.index_group, int) or \
                not isinstance(self.index_offset, int):
            raise ValueError(
                'Cannot read or write data with invalid values for group- and '
                'offset index: ({}, {})'.format(self.index_group,
                                                self.index_offset))

    def read(self) -> Any:
        """Read the current value of this symbol"""
        self.read_write_check()
        return self._plc.read(self.index_group, self.index_offset,
                              self.plc_type)

    def write(self, new_value: Any):
        """Write a new value to the symbol"""
        self.read_write_check()
        return self._plc.write(self.index_group, self.index_offset,
                               new_value, self.plc_type)

    @property
    def value(self):
        """Equivalent to AdsSymbol.read()"""
        return self.read()

    @value.setter
    def value(self, new_value):
        """Equivalent to AdsSymbol.write()"""
        self.write(new_value)

    def __repr__(self):
        """Debug string"""
        t = type(self)
        return '<{}.{} object at {}, name: {}, type: {}>'.format(
            t.__module__, t.__qualname__, hex(id(self)),
            self.name, self.symbol_type)

    def __del__(self):
        """Destructor"""
        self.clear_device_notifications()

    def add_device_notification(
            self,
            callback: Callable,
            attr: Optional[NotificationAttrib] = None,
            user_handle: Optional[int] = None
    ) -> Optional[Tuple[int, int]]:
        """Add on-change callback to symbol

        See Connection.add_device_notification(...).

        When `attr` is omitted, the default will be used.

        The notification handles are returned but also stored locally. When
        this symbol is destructed any notifications will be freed up
        automatically.
        """

        if attr is None:
            attr = NotificationAttrib(length=sizeof(self.plc_type))

        handles = self._plc.add_device_notification(
            (self.index_group, self.index_offset),
            attr,
            callback,
            user_handle
        )

        self._handles_list.append(handles)

        return handles

    def clear_device_notifications(self):
        """Remove all registered notifications"""
        if self._handles_list:
            for handles in self._handles_list:
                self._plc.del_device_notification(*handles)
            self._handles_list = []  # Clear the list

    def del_device_notification(self, handles: Tuple[int, int]):
        """Remove a single device notification by handles"""
        if handles in self._handles_list:
            self._plc.del_device_notification(*handles)
            self._handles_list.remove(handles)

    @staticmethod
    def get_type_from_str(type_str: str) -> Any:
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

        # If ARRAY
        reg_match = re.match(r'ARRAY \[(\d+)..(\d+)\] OF (.*)', type_str)
        if reg_match is not None:

            groups = reg_match.groups()
            size = int(groups[1]) + 1 - int(groups[0])  # Estimate the size
            scalar_type_str = groups[2]

            # Find scalar type
            scalar_type = AdsSymbol.get_type_from_str(scalar_type_str)

            if scalar_type:
                return scalar_type * size

            # Fall to method default instead

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

    @staticmethod
    def get_type_from_int(type_int: int) -> Any:
        """Get PLCTYPE_* from a number

        Also see `get_type_from_string()`
        """
        if type_int in constants.ads_type_to_ctype:
            return constants.ads_type_to_ctype[type_int]

        return None
