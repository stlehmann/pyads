"""
Define the Symbol class

Separate file because it depends on many other files, so we try to simplify
the circular dependencies.

:author: Roberto Roos
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2020-11-16

"""
from __future__ import annotations

import re
from ctypes import sizeof
from typing import TYPE_CHECKING, Any, Optional, List, Tuple, Callable, Union, Type

from . import constants  # To access all constants, use package notation
from .constants import PLCDataType
from .pyads_ex import adsGetSymbolInfo
from .structs import NotificationAttrib

# ads.Connection relies on structs.AdsSymbol (but in type hints only), so use
# this 'if' to only include it when type hinting (False during execution)
if TYPE_CHECKING:
    from .ads import Connection, StructureDef  # pragma: no cover


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
    :ivar value: Buffered value, i.e. the most recently read or written
        value for this symbol
    """

    # Regex for array - e.g. "ARRAY [1..10] OF DINT"
    _regex_array = re.compile(r"ARRAY \[(\d+)..(\d+)\] OF (.*)")
    # Regex for matrix - e.g. "matrix_10_int32"
    _regex_matrix = re.compile(r"matrix_(\d+)_(.*)_T")
    # Regex for list - e.g. "DINT(10)"
    _regex_list = re.compile(r"(.*)\((\d+)\)")

    def __init__(
            self,
            plc: "Connection",
            name: Optional[str] = None,
            index_group: Optional[int] = None,
            index_offset: Optional[int] = None,
            symbol_type: Optional[Union[str, Type["PLCDataType"]]] = None,
            comment: Optional[str] = None,
            auto_update: bool = False,
            structure_def: Optional["StructureDef"] = None,
            array_size: Optional[int] = 1,
    ) -> None:
        """Create AdsSymbol instance.

        Specify either the variable name or the index_group **and**
        index_offset so the symbol can be located.
        If the name was specified but not all other attributes were,
        the other attributes will be looked up from the connection.

        `symbol_type` should be a type constant like `pyads.PLCTYPE_*`.
        Alternatively, it can be a string representation a PLC type (e.g.
        'LREAL').

        :param plc: Connection instance
        :param name:
        :param index_group:
        :param index_offset:
        :param symbol_type: PLC variable type (e.g. `pyads.PLCTYPE_DINT`)
        :param comment:
        :param auto_update: Create notification to update buffer (same as
            `set_auto_update(True)`)
        :param Optional["StructureDef"] structure_def: special tuple defining the structure and
            types contained within it according to PLCTYPE constants, must match
            the structure defined in the PLC, PLC structure must be defined with
            {attribute 'pack_mode' :=  '1'}
        :param Optional[int] array_size: size of array if reading array of structure, defaults to 1

        Expected input example for structure_def:

        .. code:: python

            structure_def = (
                ('rVar', pyads.PLCTYPE_LREAL, 1),
                ('sVar', pyads.PLCTYPE_STRING, 2, 35),
                ('SVar1', pyads.PLCTYPE_STRING, 1),
                ('rVar1', pyads.PLCTYPE_REAL, 1),
                ('iVar', pyads.PLCTYPE_DINT, 1),
                ('iVar1', pyads.PLCTYPE_INT, 3),
            )

            # i.e ('Variable Name', variable type, arr size (1 if not array),
            # length of string (if defined in PLC))

        """
        self._plc = plc
        self._handles_list: List[Tuple[int, int]] = []  # Notification handles
        self._auto_update_handle: Optional[Tuple[int, int]] = None

        # Check if the required info is present:
        missing_info = index_group is None or index_offset is None or symbol_type is None

        if missing_info:
            if name is None:
                raise ValueError(
                    "Please specify either `name`, or `index_group`, "
                    "`index_offset` and plc_type"
                )

        self.name = name
        self.index_offset = index_offset
        self.index_group = index_group
        self.symbol_type = symbol_type
        self.comment = comment
        self._value: Any = None

        # structure information
        self.structure_def = structure_def
        self.array_size = array_size
        self._structure_size = 0
        if self.structure_def is not None:
            from .ads import size_of_structure
            self._structure_size = size_of_structure(self.structure_def * self.array_size)

        if missing_info:
            self._create_symbol_from_info()  # Perform remote lookup

        # Now `self.symbol_type` should have a value, find the actual PLCTYPE
        # from it.
        # This is relevant for both lookup and full user definition.

        self.plc_type: Optional[Type[PLCDataType]] = None
        if self.symbol_type is not None:
            if isinstance(self.symbol_type, str):  # Perform lookup if string
                self.plc_type = AdsSymbol.get_type_from_str(self.symbol_type)
            else:  # Otherwise `symbol_type` is probably a pyads.PLCTYPE_* constant
                self.plc_type = self.symbol_type

        self.auto_update = auto_update

    def _create_symbol_from_info(self) -> None:
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
        self.symbol_type = info.symbol_type  # Save the type as string

    def _check_for_open_connection(self) -> None:
        """Assert the current object is ready to read from/write to.

        This checks only if the Connection is open.
        """
        if not self._plc.is_open:
            raise ValueError(
                "Cannot read or write data with missing or closed Connection"
            )

    def read(self) -> Any:
        """Read the current value of this symbol.

        The new read value is also saved in the buffer.
        """
        self._check_for_open_connection()

        if self.is_structure:
            self._value = self._plc.read_structure_by_name(self.name, self.structure_def,
                                                           structure_size=self._structure_size,
                                                           array_size=self.array_size)
        else:
            self._value = self._plc.read(self.index_group, self.index_offset, self.plc_type)

        return self._value

    def write(self, new_value: Optional[Any] = None) -> None:
        """Write a new value or the buffered value to the symbol.

        When a new value was written, the buffer is updated.

        :param new_value    Value to be written to symbol (if None,
                            the buffered value is send instead)
        """
        self._check_for_open_connection()

        if new_value is None:
            new_value = self._value  # Send buffered value instead
        else:
            self._value = new_value  # Update buffer with new value

        if self.is_structure:
            self._plc.write_structure_by_name(self.name, new_value, self.structure_def,
                                              structure_size=self._structure_size, array_size=self.array_size)
        else:
            self._plc.write(self.index_group, self.index_offset, new_value, self.plc_type)

    def __repr__(self) -> str:
        """Debug string"""
        t = type(self)
        return "<{}.{} object at {}, name: {}, type: {}>".format(
            t.__module__, t.__qualname__, hex(id(self)), self.name, self.symbol_type
        )

    def __del__(self) -> None:
        """Destructor"""
        self.clear_device_notifications()

    def add_device_notification(
            self,
            callback: Callable[[Any, Any], None],
            attr: Optional[NotificationAttrib] = None,
            user_handle: Optional[int] = None,
    ) -> Optional[Tuple[int, int]]:
        """Add on-change callback to symbol.

        See Connection.add_device_notification(...).

        When `attr` is omitted, the default will be used.

        The notification handles are returned but also stored locally. When
        this symbol is destructed any notifications will be freed up
        automatically.
        """

        if attr is None:
            attr = NotificationAttrib(length=sizeof(self.plc_type))

        handles = self._plc.add_device_notification(
            (self.index_group, self.index_offset), attr, callback, user_handle
        )

        self._handles_list.append(handles)

        return handles

    def clear_device_notifications(self) -> None:
        """Remove all registered notifications"""
        if self._handles_list:
            for handles in self._handles_list:
                self._plc.del_device_notification(*handles)
            self._handles_list = []  # Clear the list

        self._auto_update_handle = None  # If auto-update was enabled,
        # it won't work anymore

    def del_device_notification(self, handles: Tuple[int, int]) -> None:
        """Remove a single device notification by handles"""
        if handles in self._handles_list:
            self._plc.del_device_notification(*handles)
            self._handles_list.remove(handles)

    def _value_callback(self, notification: Any, data_name: Any) -> None:
        """Internal callback used by auto-update"""

        _handle, _datetime, value = self._plc.parse_notification(
            notification, self.plc_type
        )
        self._value = value

    @staticmethod
    def get_type_from_str(type_str: str) -> Optional[Type[PLCDataType]]:
        """Get PLCTYPE_* from PLC name string

        If PLC name could not be mapped, return None. This is done on
        purpose to prevent a program from crashing when an unusable symbol
        is found. Instead, exceptions will be thrown when this unmapped
        symbol is read/written.
        """

        # If simple scalar
        plc_name = "PLCTYPE_" + type_str
        if hasattr(constants, plc_name):
            # Map e.g. 'LREAL' to 'PLCTYPE_LREAL' directly based on the name
            return getattr(constants, plc_name)

        # If ARRAY
        reg_match = AdsSymbol._regex_array.match(type_str)
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
        reg_match = AdsSymbol._regex_matrix.match(type_str)
        if reg_match is not None:

            groups = reg_match.groups()
            size = int(groups[0])
            scalar_type_str = groups[1]

            if scalar_type_str in constants.PLC_ARRAY_MAP:
                return constants.PLC_ARRAY_MAP[scalar_type_str](size)

        # If list
        reg_match = AdsSymbol._regex_list.match(type_str)
        if reg_match is not None:

            groups = reg_match.groups()
            scalar_type_str = groups[0]
            size = int(groups[1])

            scalar_type = AdsSymbol.get_type_from_str(scalar_type_str)

            if scalar_type:
                return scalar_type * size

        # We allow unmapped types at this point - Instead we will throw  an
        # error when they are being addressed

        return None

    @property
    def auto_update(self) -> Any:
        """Return True if auto_update is enabled for this symbol."""
        return self._auto_update_handle is not None

    @auto_update.setter
    def auto_update(self, value: bool) -> None:
        """Enable or disable auto-update of the buffered value.

        This automatic update is done through a device notification. This
        can be efficient when a remote variables changes its values less often
        than your code run.

        Clearing all device notifications will also disable auto-update.
        Automatic update is disabled by default.
        """
        if value and self._auto_update_handle is None:
            self._auto_update_handle = self.add_device_notification(
                self._value_callback
            )
        elif not value and self._auto_update_handle is not None:
            self.del_device_notification(self._auto_update_handle)
            self._auto_update_handle = None

    @property
    def value(self) -> Any:
        """Return the current value of the symbol."""
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        """Set the current value of the symbol.

        If auto_update is True then the the write command will be called automatically.

        """
        self._value = val

        # write value to plc if auto_update is enabled
        if self.auto_update:
            self.write(val)

    @property
    def is_structure(self) -> bool:
        """Return True if the symbol object represents a structure.

        This is the case if a structure_def has been passed during initialization.
        """
        return self.structure_def is not None
