"""Pythonic ADS functions.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53

"""
from __future__ import annotations
import struct
import itertools
from collections import OrderedDict
from ctypes import (
    memmove,
    addressof,
    c_ubyte,
    Array,
    Structure,
    sizeof,
    create_string_buffer,
)
from datetime import datetime
from functools import partial
from typing import Optional, Union, Tuple, Any, Type, Callable, Dict, List, cast, Iterator

# noinspection PyUnresolvedReferences
from .constants import (
    ADSIGRP_SYM_UPLOAD,
    ADSIGRP_SYM_UPLOADINFO2,
    ADSIOFFS_DEVDATA_ADSSTATE,
    PLCTYPE_BOOL,
    PLCTYPE_BYTE,
    PLCTYPE_DATE,
    PLCTYPE_DINT,
    PLCTYPE_DT,
    PLCTYPE_DWORD,
    PLCTYPE_INT,
    PLCTYPE_LREAL,
    PLCTYPE_REAL,
    PLCTYPE_SINT,
    PLCTYPE_STRING,
    PLCTYPE_TIME,
    PLCTYPE_TOD,
    PLCTYPE_UDINT,
    PLCTYPE_UINT,
    PLCTYPE_USINT,
    PLCTYPE_WORD,
    PLC_DEFAULT_STRING_SIZE,
    DATATYPE_MAP,
    ADSIGRP_SUMUP_READ,
    ADSIGRP_SUMUP_WRITE,
    MAX_ADS_SUB_COMMANDS,
    ads_type_to_ctype,
    PLCSimpleDataType,
    PLCDataType,
)
from .filetimes import filetime_to_dt
from .pyads_ex import (
    adsAddRoute,
    adsAddRouteToPLC,
    adsDelRoute,
    adsPortOpenEx,
    adsPortCloseEx,
    adsGetLocalAddressEx,
    adsSyncReadStateReqEx,
    adsSyncReadDeviceInfoReqEx,
    adsSyncWriteControlReqEx,
    adsSyncWriteReqEx,
    adsSyncReadWriteReqEx2,
    adsSyncReadReqEx2,
    adsGetHandle,
    adsGetNetIdForPLC,
    adsGetSymbolInfo,
    adsSumRead,
    adsSumWrite,
    adsReleaseHandle,
    adsSyncReadByNameEx,
    adsSyncWriteByNameEx,
    adsSyncAddDeviceNotificationReqEx,
    adsSyncDelDeviceNotificationReqEx,
    adsSyncSetTimeoutEx,
    adsSetLocalAddress,
    ADSError,
)
from .structs import (
    AmsAddr,
    SAmsNetId,
    AdsVersion,
    NotificationAttrib,
    SAdsNotificationHeader,
    SAdsSymbolEntry,
)
from .symbol import AdsSymbol
from .utils import decode_ads, platform_is_linux

# custom types
StructureDef = Tuple[
    Union[Tuple[str, Type, int], Tuple[str, Type, int, Optional[int]]], ...
]

# global variables
linux: bool = platform_is_linux()
port: Optional[int] = None


def _parse_ams_netid(ams_netid: str) -> SAmsNetId:
    """Parse an AmsNetId from *str* to *SAmsNetId*.

    :param str ams_netid: NetId as a string
    :rtype: SAmsNetId
    :return: NetId as a struct

    """
    try:
        id_numbers = list(map(int, ams_netid.split(".")))
    except ValueError:
        raise ValueError("no valid netid")

    if len(id_numbers) != 6:
        raise ValueError("no valid netid")

    # Fill the netId struct with data
    ams_netid_st = SAmsNetId()
    ams_netid_st.b = (c_ubyte * 6)(*id_numbers)
    return ams_netid_st


def open_port() -> int:
    """Connect to the TwinCAT message router.

    :rtype: int
    :return: port number

    """
    global port

    port = port or adsPortOpenEx()
    return port


def close_port() -> None:
    """Close the connection to the TwinCAT message router."""
    global port

    if port is not None:
        adsPortCloseEx(port)
        port = None


def get_local_address() -> Optional[AmsAddr]:
    """Return the local AMS-address and the port number.

    :rtype: AmsAddr

    """
    if port is not None:
        return adsGetLocalAddressEx(port)

    return None


def set_local_address(ams_netid: Union[str, SAmsNetId]) -> None:
    """Set the local NetID (**Linux only**).

    :param str ams_netid: new AmsNetID
    :rtype: None

    **Usage:**

        >>> import pyads
        >>> pyads.open_port()
        >>> pyads.set_local_address('0.0.0.0.1.1')

    """
    if isinstance(ams_netid, str):
        ams_netid_st = _parse_ams_netid(ams_netid)
    else:
        ams_netid_st = ams_netid

    assert isinstance(ams_netid_st, SAmsNetId)

    if linux:
        return adsSetLocalAddress(ams_netid_st)
    else:
        raise ADSError(
            text="SetLocalAddress is not supported for Windows clients."
        )  # pragma: no cover


def add_route(adr: Optional[Union[str, AmsAddr]], ip_address: str) -> None:
    """Establish a new route in the AMS Router (linux Only).

    :param adr: AMS Address of routing endpoint as str or AmsAddr object. If
        None is provided, the net id of the PLC will be discovered.
    :param str ip_address: ip address of the routing endpoint

    """
    if adr is None:
        adr = adsGetNetIdForPLC(ip_address)
    if isinstance(adr, str):
        adr = AmsAddr(adr)

    return adsAddRoute(adr.netIdStruct(), ip_address)


def add_route_to_plc(
    sending_net_id: str,
    adding_host_name: str,
    ip_address: str,
    username: str,
    password: str,
    route_name: str = None,
    added_net_id: str = None,
) -> bool:
    """Embed a new route in the PLC.

    :param str sending_net_id: sending net id
    :param str adding_host_name: host name (or IP) of the PC being added
    :param str ip_address: ip address of the PLC
    :param str username: username for PLC
    :param str password: password for PLC
    :param str route_name: PLC side name for route, defaults to adding_host_name or the current hostname of this PC
    :param pyads.structs.SAmsNetId added_net_id: net id that is being added to the PLC, defaults to sending_net_id
    :rtype: bool
    :return: True if route was added

    """
    return adsAddRouteToPLC(
        sending_net_id,
        adding_host_name,
        ip_address,
        username,
        password,
        route_name=route_name,
        added_net_id=added_net_id,
    )


def delete_route(adr: AmsAddr) -> None:
    """Remove existing route from the AMS Router (Linux Only).

    :param pyads.structs.AmsAddr adr: AMS Address associated with the routing entry which is to be removed from the
        router.

    """
    return adsDelRoute(adr.netIdStruct())


def set_timeout(ms: int) -> None:
    """Set timeout."""
    if port is not None:
        return adsSyncSetTimeoutEx(port, ms)


def size_of_structure(structure_def: StructureDef) -> int:
    """Calculate the size of a structure in number of BYTEs.

    :param tuple structure_def: special tuple defining the structure and
        types contained within it according o PLCTYPE constants
    :return: data size required to read/write a structure of multiple types
    :rtype: int

    Expected input example for structure_def:

    .. code:: python

        structure_def = (
            ('rVar', pyads.PLCTYPE_LREAL, 1),
            ('sVar', pyads.PLCTYPE_STRING, 2, 35),
            ('sVar1', pyads.PLCTYPE_STRING, 1),
            ('rVar1', pyads.PLCTYPE_REAL, 1),
            ('iVar', pyads.PLCTYPE_DINT, 1),
            ('iVar1', pyads.PLCTYPE_INT, 3),
        )
        # i.e ('Variable Name', variable type, arr size (1 if not array),
        # length of string (if defined in PLC))

    If array of structure multiply structure_def input by array size.

    """
    num_of_bytes = 0
    for item in structure_def:
        try:
            var, plc_datatype, size = item  # type: ignore
            str_len = None
        except ValueError:
            var, plc_datatype, size, str_len = item  # type: ignore

        if plc_datatype == PLCTYPE_STRING:
            if str_len is not None:
                num_of_bytes += (str_len + 1) * size
            else:
                num_of_bytes += (PLC_DEFAULT_STRING_SIZE + 1) * size
        elif plc_datatype not in DATATYPE_MAP:
            raise RuntimeError("Datatype not found")
        else:
            num_of_bytes += sizeof(plc_datatype) * size

    return num_of_bytes


def dict_from_bytes(
    byte_list: bytearray, structure_def: StructureDef, array_size: int = 1
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Return an ordered dict of PLC values from a list of BYTE values read from PLC.

    :param bytearray byte_list: list of byte values for an entire structure
    :param tuple structure_def: special tuple defining the structure and
        types contained within it according o PLCTYPE constants
    :param Optional[int] array_size: size of array if reading array of structure, defaults to 1
    :return: ordered dictionary of values for each variable type in order of structure

    Expected input example for structure_def:

    .. code:: python

        structure_def = (
            ('rVar', pyads.PLCTYPE_LREAL, 1),
            ('sVar', pyads.PLCTYPE_STRING, 2, 35),
            ('sVar1', pyads.PLCTYPE_STRING, 1),
            ('rVar1', pyads.PLCTYPE_REAL, 1),
            ('iVar', pyads.PLCTYPE_DINT, 1),
            ('iVar1', pyads.PLCTYPE_INT, 3),
        )
        # i.e ('Variable Name', variable type, arr size (1 if not array),
        # length of string (if defined in PLC))

    """
    values_list: List[Dict[str, Any]] = []
    index = 0
    for structure in range(0, array_size):
        values: Dict[str, Any] = OrderedDict()
        for item in structure_def:
            try:
                var, plc_datatype, size = item  # type: ignore
                str_len = None
            except ValueError:
                var, plc_datatype, size, str_len = item  # type: ignore

            var_array = []
            for i in range(size):
                if plc_datatype == PLCTYPE_STRING:
                    if str_len is None:
                        str_len = PLC_DEFAULT_STRING_SIZE
                    var_array.append(
                        bytearray(byte_list[index: (index + (str_len + 1))])
                        .partition(b"\0")[0]
                        .decode("utf-8")
                    )
                    index += str_len + 1
                elif plc_datatype not in DATATYPE_MAP:
                    raise RuntimeError("Datatype not found. Check structure definition")
                else:
                    n_bytes = sizeof(plc_datatype)
                    var_array.append(
                        struct.unpack(
                            DATATYPE_MAP[plc_datatype],
                            bytearray(byte_list[index: (index + n_bytes)]),
                        )[0]
                    )
                    index += n_bytes
            if size == 1:  # if not an array, don't want a list in the dict return
                values[var] = var_array[0]
            else:
                values[var] = var_array
        values_list.append(values)

    if array_size != 1:
        return values_list
    else:
        return values_list[0]


def bytes_from_dict(
    values: Union[Dict[str, Any], List[Dict[str, Any]]],
    structure_def: StructureDef,
) -> List[int]:
    """Returns a byte array of values which can be written to the PLC from an ordered dict.

    :param values: ordered dictionary of values
        for each variable type in order of structure_def
    :param tuple structure_def: special tuple defining the structure and
        types contained within it according o PLCTYPE constants
    :param Optional[int] array_size: size of array if writing array of structure, defaults to 1
    :return: list of byte values for an entire structure
    :rtype: List[int]

    Expected input example for structure_def:

    .. code:: python

        structure_def = (
            ('rVar', pyads.PLCTYPE_LREAL, 1),
            ('sVar', pyads.PLCTYPE_STRING, 2, 35),
            ('sVar2', pyads.PLCTYPE_STRING, 1),
            ('rVar1', pyads.PLCTYPE_REAL, 1),
            ('iVar', pyads.PLCTYPE_DINT, 1),
            ('iVar1', pyads.PLCTYPE_INT, 3)
        )

        # i.e ('Variable Name', variable type, arr size (1 if not array),
        # length of string (if defined in PLC))

    """
    byte_list = []
    if not isinstance(values, list):
        values = [values]

    for cur_dict in values:
        for item in structure_def:
            try:
                var, plc_datatype, size = item  # type: ignore
                str_len = None
            except ValueError:
                var, plc_datatype, size, str_len = item  # type: ignore

            var = cur_dict[var]
            for i in range(0, size):
                if plc_datatype == PLCTYPE_STRING:
                    if str_len is None:
                        str_len = PLC_DEFAULT_STRING_SIZE
                    if size > 1:
                        byte_list += list(var[i].encode("utf-8"))
                        remaining_bytes = str_len + 1 - len(var[i])
                    else:
                        byte_list += list(var.encode("utf-8"))
                        remaining_bytes = str_len + 1 - len(var)
                    for byte in range(remaining_bytes):
                        byte_list.append(0)
                elif plc_datatype not in DATATYPE_MAP:
                    raise RuntimeError("Datatype not found. Check structure definition")
                else:
                    if size > 1:
                        byte_list += list(
                            struct.pack(DATATYPE_MAP[plc_datatype], var[i])
                        )
                    else:
                        byte_list += list(struct.pack(DATATYPE_MAP[plc_datatype], var))
    return byte_list


class Connection(object):
    """Class for managing the connection to an ADS device.

    :ivar str ams_net_id: AMS net id of the remote device
    :ivar int ams_net_port: port of the remote device
    :ivar str ip_address: the ip address of the device

    :note: If no IP address is given the ip address is automatically set
        to first 4 parts of the Ams net id.

    """

    def __init__(
        self, ams_net_id: str = None, ams_net_port: int = None, ip_address: str = None
    ) -> None:
        self._port = None  # type: Optional[int]
        self._adr = AmsAddr(ams_net_id, ams_net_port)
        self._open = False
        if ip_address is None:
            if ams_net_id is None:
                raise TypeError("Must provide an IP or net ID")
            self.ip_address = ".".join(ams_net_id.split(".")[:4])
        else:
            self.ip_address = ip_address
        self.ams_net_id = ams_net_id
        self.ams_net_port = ams_net_port
        self._notifications = {}  # type: Dict[int, str]
        self._symbol_info_cache: Dict[str, SAdsSymbolEntry] = {}

    @property
    def ams_netid(self) -> str:
        return self._adr.netid

    @ams_netid.setter
    def ams_netid(self, value: str) -> None:
        if self._open:
            raise AttributeError(
                "Setting netid is not allowed while connection is open."
            )
        self._adr.netid = value

    @property
    def ams_port(self) -> int:
        return self._adr.port

    @ams_port.setter
    def ams_port(self, value: int) -> None:
        if self._open:
            raise AttributeError(
                "Setting port is not allowed while connection is open."
            )
        self._adr.port = value

    def __enter__(self) -> "Connection":
        """Open on entering with-block."""
        self.open()
        return self

    def __exit__(self, _type: Type, _val: Any, _traceback: Any) -> None:
        """Close on leaving with-block."""
        self.close()

    def __del__(self) -> None:
        """Class destructor.

        Make sure to close the connection when an instance runs out of scope.
        """
        # If the connection is already closed, nothing new will happen
        self.close()

    def _query_plc_datatype_from_name(self, data_name: str, cache_symbol_info: bool) -> Type:
        """Return the plc_datatype by reading SymbolInfo from the target.

        If cache_symbol_info is True then the SymbolInfo will be cached and adsGetSymbolInfo
        will only used once.

        """
        if cache_symbol_info:
            info = self._symbol_info_cache.get(data_name)
            if info is None:
                info = adsGetSymbolInfo(self._port, self._adr, data_name)
                self._symbol_info_cache[data_name] = info
        else:
            info = adsGetSymbolInfo(self._port, self._adr, data_name)
        return AdsSymbol.get_type_from_str(info.symbol_type)

    def open(self) -> None:
        """Connect to the TwinCAT message router."""
        if self._open:
            return

        if self.ams_net_id is None:
            self.ams_net_id = adsGetNetIdForPLC(self.ip_address)
            self._adr = AmsAddr(self.ams_net_id, self.ams_net_port)
        self._port = adsPortOpenEx()

        if linux:
            adsAddRoute(self._adr.netIdStruct(), self.ip_address)

        self._open = True

    def close(self) -> None:
        """:summary: Close the connection to the TwinCAT message router."""
        if not self._open:
            return

        if linux:
            adsDelRoute(self._adr.netIdStruct())

        if self._port is not None:
            adsPortCloseEx(self._port)
            self._port = None

        self._open = False

    def get_local_address(self) -> Optional[AmsAddr]:
        """Return the local AMS-address and the port number.

        :rtype: AmsAddr

        """
        if self._port is not None:
            return adsGetLocalAddressEx(self._port)

        return None

    def read_state(self) -> Optional[Tuple[int, int]]:
        """Read the current ADS-state and the machine-state.

        Read the current ADS-state and the machine-state from the ADS-server.

        :rtype: (int, int)
        :return: adsState, deviceState

        """
        if self._port is not None:
            return adsSyncReadStateReqEx(self._port, self._adr)

        return None

    def write_control(
        self, ads_state: int, device_state: int, data: Any, plc_datatype: Type
    ) -> None:
        """Change the ADS state and the machine-state of the ADS-server.

        :param int ads_state: new ADS-state, according to ADSTATE constants
        :param int device_state: new machine-state
        :param data: additional data
        :param int plc_datatype: datatype, according to PLCTYPE constants

        :note: Despite changing the ADS-state and the machine-state it is
            possible to send additional data to the ADS-server. For current
            ADS-devices additional data is not progressed.
            Every ADS-device is able to communicate its current state to other
            devices. There is a difference between the device-state and the
            state of the ADS-interface (AdsState). The possible states of an
            ADS-interface are defined in the ADS-specification.

        """
        if self._port is not None:
            return adsSyncWriteControlReqEx(
                self._port, self._adr, ads_state, device_state, data, plc_datatype
            )

    def read_device_info(self) -> Optional[Tuple[str, AdsVersion]]:
        """Read the name and the version number of the ADS-server.

        :rtype: string, AdsVersion
        :return: device name, version

        """
        if self._port is not None:
            return adsSyncReadDeviceInfoReqEx(self._port, self._adr)

        return None

    def write(
        self, index_group: int, index_offset: int, value: Any, plc_datatype: Type["PLCDataType"]
    ) -> None:
        """Send data synchronous to an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param Any value: value to write to the storage address of the PLC
        :param Type["PLCDataType"] plc_datatype: type of the data given to the PLC,
            according to PLCTYPE constants

        """
        if self._port is not None:
            return adsSyncWriteReqEx(
                self._port, self._adr, index_group, index_offset, value, plc_datatype
            )

    def read_write(
        self,
        index_group: int,
        index_offset: int,
        plc_read_datatype: Optional[Type["PLCDataType"]],
        value: Any,
        plc_write_datatype: Optional[Type["PLCDataType"]],
        return_ctypes: bool = False,
        check_length: bool = True,
    ) -> Any:
        """Read and write data synchronous from/to an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param Type["PLCDataType"] plc_read_datatype: type of the data given to the PLC to respond to,
            according to PLCTYPE constants, or None to not read anything
        :param value: value to write to the storage address of the PLC
        :param Type["PLCDataType"] plc_write_datatype: type of the data given to the PLC, according to
            PLCTYPE constants, or None to not write anything
        :param bool return_ctypes: return ctypes instead of python types if True (default: False)
        :param bool check_length: check whether the amount of bytes read matches the size
            of the read data type (default: True)
        :return: value: **value**

        """
        if self._port is not None:
            return adsSyncReadWriteReqEx2(
                self._port,
                self._adr,
                index_group,
                index_offset,
                plc_read_datatype,
                value,
                plc_write_datatype,
                return_ctypes,
                check_length,
            )

        return None

    def read(
        self,
        index_group: int,
        index_offset: int,
        plc_datatype: Type["PLCDataType"],
        return_ctypes: bool = False,
        check_length: bool = True,
    ) -> Any:
        """Read data synchronous from an ADS-device.

        :param int index_group: PLC storage area, according to the INDEXGROUP
            constants
        :param int index_offset: PLC storage address
        :param Type["PLCDataType"] plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants
        :param bool return_ctypes: return ctypes instead of python types if True
            (default: False)
        :param bool check_length: check whether the amount of bytes read matches the size
            of the read data type (default: True)
        :return: value

        """
        if self._port is not None:
            return adsSyncReadReqEx2(
                self._port,
                self._adr,
                index_group,
                index_offset,
                plc_datatype,
                return_ctypes,
                check_length,
            )

        return None

    def get_symbol(
        self,
        name: Optional[str] = None,
        index_group: Optional[int] = None,
        index_offset: Optional[int] = None,
        plc_datatype: Optional[Union[Type["PLCDataType"], str]] = None,
        comment: Optional[str] = None,
        auto_update: bool = False,
        structure_def: Optional["StructureDef"] = None,
        array_size: Optional[int] = 1,
    ) -> AdsSymbol:
        """Create a symbol instance

        Specify either the variable name or the index_group **and**
        index_offset so the symbol can be located.
        If the name was specified but not all other attributes were,
        the other attributes will be looked up from the connection.
        `data_type` can be a PLCTYPE constant or  a string representing
        a PLC type (e.g. 'LREAL').

        :param str name:
        :param Optional[int] index_group:
        :param Optional[int] index_offset:
        :param plc_datatype: type of the  PLC variable, according
            to PLCTYPE constants
        :param str comment: comment
        :param bool auto_update: Create notification to update buffer (same as
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

        return AdsSymbol(self, name, index_group, index_offset, plc_datatype,
                         comment, auto_update=auto_update, structure_def=structure_def, array_size=array_size)

    def get_all_symbols(self) -> List[AdsSymbol]:
        """Read all symbols from an ADS-device.
        
        :return: List of AdsSymbols
        """
        symbols = []
        if self._port is not None:
            symbol_size_msg = self.read(
                ADSIGRP_SYM_UPLOADINFO2,
                ADSIOFFS_DEVDATA_ADSSTATE,
                PLCTYPE_STRING,
                return_ctypes=True,
            )
            sym_count = struct.unpack("I", symbol_size_msg[0:4])[0]
            sym_list_length = struct.unpack("I", symbol_size_msg[4:8])[0]

            data_type_creation_fn: Type = cast("Type", partial(create_string_buffer, sym_list_length))
            symbol_list_msg = self.read(
                ADSIGRP_SYM_UPLOAD,
                ADSIOFFS_DEVDATA_ADSSTATE,
                data_type_creation_fn,
                return_ctypes=True,
            )

            ptr = 0

            for idx in range(sym_count):
                read_length, index_group, index_offset = struct.unpack(
                    "III", symbol_list_msg[ptr + 0: ptr + 12]
                )
                name_length, type_length, comment_length = struct.unpack(
                    "HHH", symbol_list_msg[ptr + 24: ptr + 30]
                )

                name_start_ptr = ptr + 30
                name_end_ptr = name_start_ptr + name_length
                type_start_ptr = name_end_ptr + 1
                type_end_ptr = type_start_ptr + type_length
                comment_start_ptr = type_end_ptr + 1
                comment_end_ptr = comment_start_ptr + comment_length

                name = decode_ads(symbol_list_msg[name_start_ptr:name_end_ptr])
                symbol_type = decode_ads(symbol_list_msg[type_start_ptr:type_end_ptr])
                comment = decode_ads(symbol_list_msg[comment_start_ptr:comment_end_ptr])

                ptr = ptr + read_length
                symbol = AdsSymbol(plc=self, name=name,
                                   index_group=index_group,
                                   index_offset=index_offset,
                                   symbol_type=symbol_type, comment=comment)
                symbols.append(symbol)
        return symbols

    def get_handle(self, data_name: str) -> Optional[int]:
        """Get the handle of the PLC-variable, handles obtained using this
         method should be released using method 'release_handle'.

        :param string data_name: data name

        :rtype: int
        :return: int: PLC-variable handle
        """
        if self._port is not None:
            return adsGetHandle(self._port, self._adr, data_name)

        return None

    def release_handle(self, handle: int) -> None:
        """ Release handle of a PLC-variable.

        :param int handle: handle of PLC-variable to be released
        """
        if self._port is not None:
            adsReleaseHandle(self._port, self._adr, handle)

    def read_by_name(
        self,
        data_name: str,
        plc_datatype: Optional[Type["PLCDataType"]] = None,
        return_ctypes: bool = False,
        handle: Optional[int] = None,
        check_length: bool = True,
        cache_symbol_info: bool = True,
    ) -> Any:
        """Read data synchronous from an ADS-device from data name.

        :param string data_name: data name,  can be empty string if handle is used
        :param Optional[Type["PLCDataType"]] plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants, if None the datatype will be read from the target
            with adsGetSymbolInfo (default: None)
        :param bool return_ctypes: return ctypes instead of python types if True
            (default: False)
        :param int handle: PLC-variable handle, pass in handle if previously
            obtained to speed up reading (default: None)
        :param bool check_length: check whether the amount of bytes read matches the size
            of the read data type (default: True)
        :param bool cache_symbol_info: when True, symbol info will be cached for
            future reading, only relevant if plc_datatype is None (default: True)
        :return: value: **value**
        """
        if not self._port:
            return

        if plc_datatype is None:
            plc_datatype = self._query_plc_datatype_from_name(data_name, cache_symbol_info)

        return adsSyncReadByNameEx(
            self._port,
            self._adr,
            data_name,
            plc_datatype,
            return_ctypes=return_ctypes,
            handle=handle,
            check_length=check_length,
        )

    def read_list_by_name(
        self,
        data_names: List[str],
        cache_symbol_info: bool = True,
        ads_sub_commands: int = MAX_ADS_SUB_COMMANDS,
        structure_defs: Optional[Dict[str, StructureDef]] = None,
    ) -> Dict[str, Any]:
        """Read a list of variables.

        Will split the read into multiple ADS calls in chunks of ads_sub_commands by default.

        MAX_ADS_SUB_COMMANDS comes from Beckhoff recommendation:
        https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_adsdll2/9007199379576075.html&id=9180083787138954512

        :param List[str] data_names: list of variable names to be read
        :param bool cache_symbol_info: when True, symbol info will be cached for future reading
        :param int ads_sub_commands: Max number of ADS-Sub commands used to read the variables in a single ADS call.
            A larger number can be used but may jitter the PLC execution!
        :param Optional[Dict[str, StructureDef]] structure_defs: for structured variables, optional mapping of
            data name to special tuple defining the structure and types contained within it according to PLCTYPE constants
        :return adsSumRead: A dictionary containing variable names from data_names as keys and values read from PLC for each variable
        :rtype: Dict[str, Any]

        """
        if structure_defs is None:
            structure_defs = {}

        if cache_symbol_info:
            new_items = [i for i in data_names if i not in self._symbol_info_cache]
            new_cache = {
                i: adsGetSymbolInfo(self._port, self._adr, i) for i in new_items
            }
            self._symbol_info_cache.update(new_cache)
            data_symbols = {i: self._symbol_info_cache[i] for i in data_names}
        else:
            data_symbols = {
                i: adsGetSymbolInfo(self._port, self._adr, i) for i in data_names
            }

        def sum_read(port: int, adr: AmsAddr, data_names: List[str], data_symbols: Dict) -> Dict[str, str]:
            result = adsSumRead(port, adr, data_names, data_symbols, list(structure_defs.keys()))  # type: ignore

            for data_name, structure_def in structure_defs.items():  # type: ignore
                result[data_name] = dict_from_bytes(result[data_name], structure_def)  # type: ignore

            return result

        if len(data_names) <= ads_sub_commands:
            return sum_read(self._port, self._adr, data_names, data_symbols)

        return_data: Dict[str, Any] = {}
        for data_names_slice in _list_slice_generator(data_names, ads_sub_commands):
            return_data.update(
                sum_read(self._port, self._adr, data_names_slice, data_symbols)
            )
        return return_data

    def write_list_by_name(
        self,
        data_names_and_values: Dict[str, Any],
        cache_symbol_info: bool = True,
        ads_sub_commands: int = MAX_ADS_SUB_COMMANDS,
        structure_defs: Optional[Dict[str, StructureDef]] = None,
    ) -> Dict[str, str]:
        """Write a list of variables.

        Will split the write into multiple ADS calls in chunks of ads_sub_commands by default.

        MAX_ADS_SUB_COMMANDS comes from Beckhoff recommendation:
        https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_adsdll2/9007199379576075.html&id=9180083787138954512

        :param data_names_and_values: dictionary of variable names and their values to be written
        :type data_names_and_values: dict[str, Any]
        :param bool cache_symbol_info: when True, symbol info will be cached for future reading
        :param int ads_sub_commands: Max number of ADS-Sub commands used to write the variables in a single ADS call.
            A larger number can be used but may jitter the PLC execution!
        :param dict structure_defs: for structured variables, optional mapping of
            data name to special tuple defining the structure and
            types contained within it according to PLCTYPE constants
        :return adsSumWrite: A dictionary containing variable names from data_names as keys and values return codes for
            each write operation from the PLC
        :rtype: dict(str, str)

        """
        if cache_symbol_info:
            new_items = [
                i
                for i in data_names_and_values.keys()
                if i not in self._symbol_info_cache
            ]
            new_cache = {
                i: adsGetSymbolInfo(self._port, self._adr, i) for i in new_items
            }
            self._symbol_info_cache.update(new_cache)
            data_symbols = {
                i: self._symbol_info_cache[i] for i in data_names_and_values
            }
        else:
            data_symbols = {
                i: adsGetSymbolInfo(self._port, self._adr, i)
                for i in data_names_and_values.keys()
            }

        if structure_defs is None:
            structure_defs = {}
        else:
            data_names_and_values = data_names_and_values.copy()  # copy so the original does not get modified

        for name, structure_def in structure_defs.items():
            data_names_and_values[name] = bytes_from_dict(data_names_and_values[name], structure_def)

        structured_data_names = list(structure_defs.keys())

        if len(data_names_and_values) <= ads_sub_commands:
            return adsSumWrite(
                self._port, self._adr, data_names_and_values, data_symbols, structured_data_names
            )

        return_data: Dict[str, str] = {}
        for data_names_slice in _dict_slice_generator(data_names_and_values, ads_sub_commands):
            return_data.update(
                adsSumWrite(self._port, self._adr, data_names_slice, data_symbols, structured_data_names)
            )
        return return_data

    def read_structure_by_name(
        self,
        data_name: str,
        structure_def: StructureDef,
        array_size: Optional[int] = 1,
        structure_size: Optional[int] = None,
        handle: Optional[int] = None,
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Read a structure of multiple types.

        :param string data_name: data name
        :param tuple structure_def: special tuple defining the structure and
            types contained within it according to PLCTYPE constants, must match
            the structure defined in the PLC, PLC structure must be defined with
            {attribute 'pack_mode' :=  '1'}
        :param Optional[int] array_size: size of array if reading array of structure, defaults to 1
        :param Optional[int] structure_size: size of structure if known by previous use of
            size_of_structure, defaults to None
        :param Optional[int] handle: PLC-variable handle, pass in handle if previously
            obtained to speed up reading, defaults to None
        :return: values_dict: ordered dictionary of all values corresponding to the structure
            definition

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
        if structure_size is None:
            structure_size = size_of_structure(structure_def * array_size)
        values = self.read_by_name(data_name, c_ubyte * structure_size, handle=handle)
        if values is not None:
            return dict_from_bytes(values, structure_def, array_size=array_size)

        return None

    def write_by_name(
        self,
        data_name: str,
        value: Any,
        plc_datatype: Optional[Type["PLCDataType"]] = None,
        handle: Optional[int] = None,
        cache_symbol_info: bool = True,
    ) -> None:
        """Send data synchronous to an ADS-device from data name.

        :param string data_name: data name, can be empty string if handle is used
        :param value: value to write to the storage address of the PLC
        :param int plc_datatype: type of the data given to the PLC, according
            to PLCTYPE constants, if None the datatype will be read from the target
            with adsGetSymbolInfo (default: None)
        :param int handle: PLC-variable handle, pass in handle if previously
            obtained to speed up writing (default: None)
        :param bool cache_symbol_info: when True, symbol info will be cached for
            future reading, only relevant if plc_datatype is None (default: True)
        """
        if not self._port:
            return

        if plc_datatype is None:
            plc_datatype = self._query_plc_datatype_from_name(data_name, cache_symbol_info)

        return adsSyncWriteByNameEx(
            self._port, self._adr, data_name, value, plc_datatype, handle=handle
        )

    def write_structure_by_name(
        self,
        data_name: str,
        value: Union[Dict[str, Any], List[Dict[str, Any]]],
        structure_def: StructureDef,
        array_size: Optional[int] = 1,
        structure_size: Optional[int] = None,
        handle: Optional[int] = None,
    ) -> None:
        """Write a structure of multiple types.

        :param str data_name: data name
        :param Union[Dict[str, Any], List[Dict[str, Any]]] value: value to write to the storage address of the PLC
        :param StructureDef structure_def: special tuple defining the structure and
            types contained within it according to PLCTYPE constants, must match
            the structure defined in the PLC, PLC structure must be defined with
            {attribute 'pack_mode' :=  '1'}
        :param Optional[int] array_size: size of array if writing array of structure, defaults to 1
        :param Optional[int] structure_size: size of structure if known by previous use of
            size_of_structure, defaults to None
        :param Optional[int] handle: PLC-variable handle, pass in handle if previously
            obtained to speed up reading, defaults to None

        Expected input example for structure_def:

        .. code:: python

            structure_def = (
                ('rVar', pyads.PLCTYPE_LREAL, 1),
                ('sVar', pyads.PLCTYPE_STRING, 2, 35),
                ('sVar', pyads.PLCTYPE_STRING, 1),
                ('rVar1', pyads.PLCTYPE_REAL, 1),
                ('iVar', pyads.PLCTYPE_DINT, 1),
            )

            # i.e ('Variable Name', variable type, arr size (1 if not array),
            # length of string (if defined in PLC))

        """
        byte_values = bytes_from_dict(value, structure_def)
        if structure_size is None:
            structure_size = size_of_structure(structure_def * array_size)
        return self.write_by_name(
            data_name, byte_values, c_ubyte * structure_size, handle=handle
        )

    def add_device_notification(
        self,
        data: Union[str, Tuple[int, int]],
        attr: NotificationAttrib,
        callback: Callable,
        user_handle: Optional[int] = None,
    ) -> Optional[Tuple[int, int]]:
        """Add a device notification.

        :param Union[str, Tuple[int, int] data: PLC storage address as string or Tuple with index group and offset
        :param pyads.structs.NotificationAttrib attr: object that contains
            all the attributes for the definition of a notification
        :param callback: callback function that gets executed in the event of a notification
        :param user_handle: optional user handle

        :rtype: (int, int)
        :returns: notification handle, user handle

        Save the notification handle and the user handle on creating a
        notification if you want to be able to remove the notification
        later in your code.

        **Usage**:

            >>> import pyads
            >>> from ctypes import sizeof
            >>>
            >>> # Connect to the local TwinCAT PLC
            >>> plc = pyads.Connection('127.0.0.1.1.1', 851)
            >>>
            >>> # Create callback function that prints the value
            >>> def mycallback(notification, data):
            >>>     contents = notification.contents
            >>>     value = next(
            >>>         map(int,
            >>>             bytearray(contents.data)[0:contents.cbSampleSize])
            >>>     )
            >>>     print(value)
            >>>
            >>> with plc:
            >>>     # Add notification with default settings
            >>>     atr = pyads.NotificationAttrib(sizeof(pyads.PLCTYPE_INT))
            >>>     handles = plc.add_device_notification("GVL.myvalue", atr, mycallback)
            >>>
            >>>     # Remove notification
            >>>     plc.del_device_notification(handles)

        Note: the `user_handle` (passed or returned) is the same as the handle returned from
        :meth:`Connection.get_handle()`.

        """
        if self._port is not None:
            notification_handle, user_handle = adsSyncAddDeviceNotificationReqEx(
                self._port, self._adr, data, attr, callback, user_handle
            )
            return notification_handle, user_handle

        return None

    def del_device_notification(
        self, notification_handle: int, user_handle: int
    ) -> None:
        """Remove a device notification.

        :param notification_handle: address of the variable that contains
            the handle of the notification
        :param user_handle: user handle

        """
        if self._port is not None:
            adsSyncDelDeviceNotificationReqEx(
                self._port, self._adr, notification_handle, user_handle
            )

    @property
    def is_open(self) -> bool:
        """Show the current connection state.

        :return: True if connection is open

        """
        return self._open

    def set_timeout(self, ms: int) -> None:
        """Set Timeout."""
        if self._port is not None:
            adsSyncSetTimeoutEx(self._port, ms)

    def notification(
        self, plc_datatype: Optional[Type] = None, timestamp_as_filetime: bool = False
    ) -> Callable:
        """Decorate a callback function.

        **Decorator**.

        A decorator that can be used for callback functions in order to
        convert the data of the NotificationHeader into the fitting
        Python type.

        :param plc_datatype: The PLC datatype that needs to be converted. This can
            be any basic PLC datatype or a `ctypes.Structure`.
        :param timestamp_as_filetime: Whether the notification timestamp should be returned
            as `datetime.datetime` (False) or Windows `FILETIME` as originally transmitted
            via ADS (True). Be aware that the precision of `datetime.datetime` is limited to
            microseconds, while FILETIME allows for 100 ns. This may be relevant when using
            task cycle times such as 62.5 µs. Default: False.

        The callback functions need to be of the following type:

        >>> def callback(handle, name, timestamp, value)

        * `handle`: the notification handle
        * `name`: the variable name
        * `timestamp`: the timestamp as datetime value
        * `value`: the converted value of the variable

        **Usage**:

            >>> import pyads
            >>>
            >>> plc = pyads.Connection('172.18.3.25.1.1', 851)
            >>>
            >>>
            >>> @plc.notification(pyads.PLCTYPE_STRING)
            >>> def callback(handle, name, timestamp, value):
            >>>     print(handle, name, timestamp, value)
            >>>
            >>>
            >>> with plc:
            >>>    attr = pyads.NotificationAttrib(20,
            >>>                                    pyads.ADSTRANS_SERVERCYCLE)
            >>>    handles = plc.add_device_notification('GVL.test', attr,
            >>>                                          callback)
            >>>    while True:
            >>>        pass

        """

        def notification_decorator(
            func: Callable[[int, str, Union[datetime, int], Any], None]
        ) -> Callable[[Any, str], None]:
            def func_wrapper(notification: Any, data_name: str) -> None:
                h_notification, timestamp, value = self.parse_notification(
                    notification, plc_datatype, timestamp_as_filetime
                )
                return func(h_notification, data_name, timestamp, value)

            return func_wrapper

        return notification_decorator

    # noinspection PyMethodMayBeStatic
    def parse_notification(
        self,
        notification: Any,
        plc_datatype: Optional[Type],
        timestamp_as_filetime: bool = False,
    ) -> Tuple[int, Union[datetime, int], Any]:
        # noinspection PyTypeChecker
        """Parse a notification.

                        Convert the data of the NotificationHeader into the fitting Python type.

                        :param notification: The notification we recieve from PLC datatype to be
                            converted. This can be any basic PLC datatype or a `ctypes.Structure`.
                        :param plc_datatype: The PLC datatype that needs to be converted. This can
                            be any basic PLC datatype or a `ctypes.Structure`.
                        :param timestamp_as_filetime: Whether the notification timestamp should be returned
                            as `datetime.datetime` (False) or Windows `FILETIME` as originally transmitted
                            via ADS (True). Be aware that the precision of `datetime.datetime` is limited to
                            microseconds, while FILETIME allows for 100 ns. This may be relevant when using
                            task cycle times such as 62.5 µs. Default: False.

                        :rtype: (int, int, Any)
                        :returns: notification handle, timestamp, value

                        **Usage**:

                        >>> import pyads
                        >>> from ctypes import sizeof
                        >>>
                        >>> # Connect to the local TwinCAT PLC
                        >>> plc = pyads.Connection('127.0.0.1.1.1', 851)
                        >>> tag = {"GVL.myvalue": pyads.PLCTYPE_INT}
                        >>>
                        >>> # Create callback function that prints the value
                        >>> def mycallback(notification: SAdsNotificationHeader, data: str) -> None:
                        >>>     data_type = tag[data]
                        >>>     handle, timestamp, value = plc.parse_notification(notification, data_type)
                        >>>     print(value)
                        >>>
                        >>> with plc:
                        >>>     # Add notification with default settings
                        >>>     attr = pyads.NotificationAttrib(sizeof(pyads.PLCTYPE_INT))
                        >>>
                        >>>     handles = plc.add_device_notification("GVL.myvalue", attr, mycallback)
                        >>>
                        >>>     # Remove notification
                        >>>     plc.del_device_notification(handles)
                        """
        contents = notification.contents
        data_size = contents.cbSampleSize
        # Get dynamically sized data array
        data = (c_ubyte * data_size).from_address(
            addressof(contents) + SAdsNotificationHeader.data.offset
        )
        value: Any
        if plc_datatype == PLCTYPE_STRING:
            # read only until null-termination character
            value = bytearray(data).split(b"\0", 1)[0].decode("utf-8")

        elif plc_datatype is not None and issubclass(plc_datatype, Structure):
            value = plc_datatype()
            fit_size = min(data_size, sizeof(value))
            memmove(addressof(value), addressof(data), fit_size)

        elif plc_datatype is not None and issubclass(plc_datatype, Array):
            if data_size == sizeof(plc_datatype):
                value = list(plc_datatype.from_buffer_copy(bytes(data)))
            else:
                # invalid size
                value = None

        elif plc_datatype not in DATATYPE_MAP:
            value = bytearray(data)

        else:
            value = struct.unpack(DATATYPE_MAP[plc_datatype], bytearray(data))[0]

        if timestamp_as_filetime:
            timestamp = contents.nTimeStamp
        else:
            timestamp = filetime_to_dt(contents.nTimeStamp)

        return contents.hNotification, timestamp, value


def _dict_slice_generator(dict_: Dict[Any, Any], size: int) -> Iterator[Dict[Any, Any]]:
    """Generator for slicing a dictionary into parts of size long."""
    it = iter(dict_)
    for _ in range(0, len(dict_), size):
        yield {i: dict_[i] for i in itertools.islice(it, size)}


def _list_slice_generator(list_: List[Any], size: int) -> Iterator[List[Any]]:
    """Generator for slicing a list into parts of size long."""
    it = iter(list_)
    for _ in range(0, len(list_), size):
        yield [i for i in itertools.islice(it, size)]
