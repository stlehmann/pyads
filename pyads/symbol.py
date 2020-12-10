"""
Define the Symbol class

Separate file because it depends on many other files, so we try to simplify
the circular dependencies.
"""

from typing import TYPE_CHECKING, Any, Union, Optional, Type, List, Tuple, \
    Callable
# ads.Connection relies on structs.AdsSymbol (but type hints only), so use
# this if to only include it when type hinting (False during execution)
if TYPE_CHECKING:
    from .ads import Connection
import re
from ctypes import sizeof

from .pyads_ex import adsGetSymbolInfo
from .structs import NotificationAttrib
from . import constants  # To access all constants, use package notation


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
                 plc: "Connection",
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
        self._handles_list: List[Tuple[int, int]] = []  # Notification handles

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

            print('---AdsSymbol---:')
            for field_info in info._fields_:
                field = field_info[0]
                print('info.{}:'.format(field), getattr(info, field))

            self.index_group = info.iGroup
            self.index_offset = info.iOffs
            self.comment = info.comment if info.comment is not None \
                else comment
            if info.type_name is not None and info.type_name:
                symtype = info.type_name  # Type name, e.g. 'LREAL'

        if isinstance(symtype, str):
            self.type_name = symtype  # Store human-readable type name
            self.symtype = self.get_type_from_str(symtype)
        elif isinstance(symtype, int):
            self.type_name = symtype  # This will be a number, but no way to
            # get it back to a sensible string
            self.symtype = constants.ads_type_to_ctype[symtype]
        else:
            self.type_name = symtype.__class__.__name__  # Try to find
            # human-readable version
            self.symtype = symtype

    def read(self) -> Any:
        """Read the current value of this symbol"""
        return self._plc.read(self.index_group, self.index_offset,
                              self.symtype)

    def write(self, new_value: Any):
        """Write a new value to the symbol"""
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

    def __del__(self):
        """Destructor"""
        self.clear_device_notifications()

    def add_device_notification(
            self,
            callback: Callable,
            attr: Optional[NotificationAttrib] = None,
            user_handle:  Optional[int] = None
    ) -> Optional[Tuple[int, int]]:
        """Add on-change callback to symbol

        See Connection.add_device_notification(...).

        When `attr` is omitted, the default will be used.

        The notification handles are returned but also stored locally. When
        this symbol is destructed any notifications will be freed up
        automatically.
        """

        if attr is None:
            attr = NotificationAttrib(length=sizeof(self.symtype))

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
