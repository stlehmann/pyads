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
    c_ubyte,
    sizeof,
)
from typing import Optional, Union, Tuple, Any, Type, Dict, List, Iterator

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
    PLCTYPE_WSTRING,
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
from .pyads_ex import (
    adsAddRoute,
    adsAddRouteToPLC,
    adsDelRoute,
    adsPortOpenEx,
    adsPortCloseEx,
    adsGetLocalAddressEx,
    adsGetNetIdForPLC,
    adsSyncSetTimeoutEx,
    adsSetLocalAddress,
    ADSError,
)
from .structs import (
    AmsAddr,
    SAmsNetId,
)
from .utils import platform_is_linux, find_wstring_null_terminator

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
                num_of_bytes += (str_len + 1) * size  # STRING uses 1 byte per character + null-terminator
            else:
                num_of_bytes += (PLC_DEFAULT_STRING_SIZE + 1) * size
        elif plc_datatype == PLCTYPE_WSTRING:
            if str_len is not None:
                num_of_bytes += 2 * (str_len + 1) * size  # WSTRING uses 2 bytes per character + null-terminator
            else:
                num_of_bytes += (PLC_DEFAULT_STRING_SIZE + 1) * 2 * size
        elif type(plc_datatype) is tuple:
            num_of_bytes += size_of_structure(plc_datatype) * size
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
                # str_len is the numbers of characters without null-terminator
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
                elif plc_datatype == PLCTYPE_WSTRING:
                    if str_len is None:  # if no str_len is given use default size
                        str_len = PLC_DEFAULT_STRING_SIZE
                    n_bytes = 2 * (str_len + 1)  # WSTRING uses 2 bytes per character + null-terminator
                    a = bytearray(byte_list[index: (index + n_bytes)])
                    null_idx = find_wstring_null_terminator(a)
                    var_array.append(a[:null_idx].decode("utf-16-le"))
                    index += n_bytes
                elif type(plc_datatype) is tuple:
                    n_bytes = size_of_structure(plc_datatype)
                    var_array.append(
                        dict_from_bytes(
                            byte_list[index : (index + n_bytes)],
                            structure_def=plc_datatype,
                        )
                    )
                    index += n_bytes
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
                        remaining_bytes = str_len + 1 - len(var[i])  # 1 byte a character plus null-terminator
                    else:
                        byte_list += list(var.encode("utf-8"))
                        remaining_bytes = str_len + 1 - len(var)  # 1 byte a character plus null-terminator
                    byte_list.extend(remaining_bytes * [0])
                elif plc_datatype == PLCTYPE_WSTRING:
                    if str_len is None:
                        str_len = PLC_DEFAULT_STRING_SIZE
                    if size > 1:
                        encoded = list(var[i].encode("utf-16-le"))
                        byte_list += encoded
                        remaining_bytes = 2 * (str_len + 1) - len(encoded)  # 2 bytes a character plus null-terminator
                    else:
                        encoded = list(var.encode("utf-16-le"))
                        byte_list += encoded
                        remaining_bytes = 2 * (str_len + 1) - len(encoded)  # 2 bytes a character plus null-terminator
                    byte_list.extend(remaining_bytes * [0])
                elif type(plc_datatype) is tuple:
                    bytecount = bytes_from_dict(
                        values=var[i], structure_def=plc_datatype
                    )
                    byte_list += bytecount
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
