"""Contains cross platform ADS extension functions.

:author: David Browne <davidabrowne@gmail.com>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53

"""
from typing import Union, Callable, Any, Tuple, Type, Optional, List, Dict
import ctypes
import os
import platform
import socket
import struct
import sys
from contextlib import closing
from functools import wraps

from .utils import platform_is_linux, platform_is_windows
from .structs import (
    AmsAddr,
    SAmsAddr,
    AdsVersion,
    SAdsVersion,
    SAdsNotificationAttrib,
    SAdsNotificationHeader,
    SAmsNetId,
    SAdsSymbolEntry,
    NotificationAttrib,
    SAdsSumRequest,
)
from .constants import (
    PLCTYPE_STRING,
    STRING_BUFFER,
    ADSIGRP_SYM_HNDBYNAME,
    PLCTYPE_UDINT,
    ADST_STRING,
    ADST_WSTRING,
    ADSIGRP_SYM_INFOBYNAMEEX,
    ADSIGRP_SYM_VALBYHND,
    ADSIGRP_SYM_RELEASEHND,
    PORT_SYSTEMSERVICE,
    PORT_REMOTE_UDP,
    ADSIGRP_SUMUP_READ,
    ADSIGRP_SUMUP_WRITE,
    DATATYPE_MAP,
    ads_type_to_ctype,
)
from .errorcodes import ERROR_CODES


NOTEFUNC: Optional[Callable] = None

# _adslib can be WinDLL or CDLL depending on OS
_adsDLL: Union["ctypes.WinDLL", "ctypes.CDLL"]

# load dynamic ADS library
if platform_is_windows():  # pragma: no cover, skip Windows test
    dlldir_handle = None
    if sys.version_info >= (3, 8) and "TWINCAT3DIR" in os.environ:
        # Starting with version 3.8, CPython does not consider the PATH environment
        # variable any more when resolving DLL paths. The following works with the default
        # installation of the Beckhoff TwinCAT ADS DLL.
        dll_path = os.environ["TWINCAT3DIR"] + "\\..\\AdsApi\\TcAdsDll"
        if platform.architecture()[0] == "64bit":
            dll_path += "\\x64"
        dlldir_handle = os.add_dll_directory(dll_path)
    try:
        _adsDLL = ctypes.WinDLL("TcAdsDll.dll")  # type: ignore
    finally:
        if dlldir_handle:
            # Do not clobber the load path for other modules
            dlldir_handle.close()
    NOTEFUNC = ctypes.WINFUNCTYPE(  # type: ignore
        ctypes.c_void_p,
        ctypes.POINTER(SAmsAddr),
        ctypes.POINTER(SAdsNotificationHeader),
        ctypes.c_ulong,
    )

elif platform_is_linux():
    # try to load local adslib.so in favor to global one
    local_adslib = os.path.join(os.path.dirname(__file__), "adslib.so")
    if os.path.isfile(local_adslib):
        adslib = local_adslib
    else:
        adslib = "adslib.so"

    _adsDLL = ctypes.CDLL(adslib)

    NOTEFUNC = ctypes.CFUNCTYPE(
        None,
        ctypes.POINTER(SAmsAddr),
        ctypes.POINTER(SAdsNotificationHeader),
        ctypes.c_ulong,
    )
else:  # pragma: no cover, can not test unsupported platform
    raise RuntimeError("Unsupported platform {0}.".format(sys.platform))

callback_store: Dict[Tuple[AmsAddr, int], Callable[[SAmsAddr, SAdsNotificationHeader, int], None]] = dict()


class ADSError(Exception):
    """Error class for errors related to ADS communication."""

    def __init__(
        self, err_code: Optional[int] = None, text: Optional[str] = None
    ) -> None:
        if err_code is not None:
            self.err_code = err_code
            try:
                self.msg = "{} ({}). ".format(ERROR_CODES[self.err_code], self.err_code)
            except KeyError:
                self.msg = "Unknown Error ({0}). ".format(self.err_code)
        else:
            self.msg = ""

        if text is not None:
            self.msg += text

    def __str__(self):
        # type: () -> str
        """Return text representation of the object."""
        return "ADSError: " + self.msg


def router_function(fn: Callable) -> Callable:
    """Raise a runtime error if on Win32 systems.

    Decorator.

    Decorator for functions that interact with the router for the Linux
    implementation of the ADS library.

    Unlike the Windows implementation which uses a separate router daemon,
    the Linux library manages AMS routing in-process. As such, routing must be
    configured programmatically via. the provided API. These endpoints are
    invalid on Win32 systems, so an exception will be raised.

    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Callable:
        if platform_is_windows():  # pragma: no cover, skip Windows test
            raise RuntimeError(
                "Router interface is not available on Win32 systems.\n"
                "Configure AMS routes using the TwinCAT router service."
            )
        return fn(*args, **kwargs)

    return wrapper


@router_function
def adsAddRoute(net_id: SAmsNetId, ip_address: str) -> None:
    """Establish a new route in the AMS Router.

    :param pyads.structs.SAmsNetId net_id: net id of routing endpoint
    :param str ip_address: ip address of the routing endpoint

    """
    add_route = _adsDLL.AdsAddRoute
    add_route.restype = ctypes.c_long

    # Convert ip address to bytes (PY3) and get pointer.
    ip_address_p = ctypes.c_char_p(ip_address.encode("utf-8"))

    error_code = add_route(net_id, ip_address_p)

    if error_code:
        raise ADSError(error_code)


def send_raw_udp_message(
    ip_address: str, message: bytes, expected_return_length: int
) -> Tuple[bytes, Tuple[str, int]]:
    """Send a raw UDP message to the PLC and return the response.

    :param str ip_address: ip address of the PLC
    :param bytes message: the message to send to the PLC
    :param int expected_return_length: number of bytes to expect in response
    :rtype: Tuple[bytes, Tuple[str, int]]
    :return: A tuple containing the response and a tuple containing the IP address and port of the
             sending socket
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:  # UDP
        # Listen on any available port for the response from the PLC
        sock.bind(("", 0))

        # Send our data to the PLC
        sock.sendto(message, (ip_address, PORT_REMOTE_UDP))

        # Response should come in in less than .5 seconds, but wait longer to account for slow
        # communications
        sock.settimeout(5)

        # Allow TimeoutError to be raised so user can handle it how they please
        return sock.recvfrom(expected_return_length)


def type_is_string(plc_type: Type) -> bool:
    """Return true if the given class is a string type."""

    # If single char
    if plc_type == PLCTYPE_STRING:
        return True

    # If char array
    if type(plc_type).__name__ == "PyCArrayType":
        if plc_type._type_ == PLCTYPE_STRING:
            return True

    return False


@router_function
def adsAddRouteToPLC(
    sending_net_id: str,
    adding_host_name: str,
    ip_address: str,
    username: str,
    password: str,
    route_name: Optional[str] = None,
    added_net_id: Optional[str] = None,
) -> bool:
    """Embed a new route in the PLC.

    :param pyads.structs.SAmsNetId sending_net_id: sending net id
    :param str adding_host_name: host name (or IP) of the PC being added
    :param str ip_address: ip address of the PLC
    :param str username: username for PLC
    :param str password: password for PLC
    :param str route_name: PLC side name for route, defaults to adding_host_name or the current hostname of this PC
    :param pyads.structs.SAmsNetId added_net_id: net id that is being added to the PLC, defaults to sending_net_id
    :rtype: bool
    :return: True if the provided credentials are correct, False otherwise

    """
    # ALL SENT STRINGS MUST BE NULL TERMINATED
    adding_host_name += "\0"
    added_net_id = added_net_id if added_net_id else sending_net_id
    route_name = route_name + "\0" if route_name else adding_host_name

    username = username + "\0"
    password = password + "\0"

    # The head of the UDP AMS packet containing host routing information
    data_header = struct.pack(
        ">12s", b"\x03\x66\x14\x71\x00\x00\x00\x00\x06\x00\x00\x00"
    )
    data_header += struct.pack(
        ">6B", *map(int, sending_net_id.split("."))
    )  # Sending net ID
    data_header += struct.pack("<H", PORT_SYSTEMSERVICE)  # Internal communication port
    data_header += struct.pack(">2s", b"\x05\x00")  # Write command
    data_header += struct.pack(">4s", b"\x00\x00\x0c\x00")  # Block of unknown
    data_header += struct.pack("<H", len(route_name))  # Length of sender host name
    data_header += route_name.encode("utf-8")  # Sender host name
    data_header += struct.pack(">2s", b"\x07\x00")  # Block of unknown

    actual_data = struct.pack("<H", 6)  # Byte length of AMS ID (always 6)
    actual_data += struct.pack(
        ">6B", *map(int, added_net_id.split("."))
    )  # Net ID being added to the PLC
    actual_data += struct.pack(
        ">2s", b"\x0d\x00"
    )  # Block of unknown (maybe encryption?)
    actual_data += struct.pack("<H", len(username))  # Length of the user name field
    actual_data += username.encode("utf-8")  # PLC Username
    actual_data += struct.pack(">2s", b"\x02\x00")  # Block of unknown
    actual_data += struct.pack("<H", len(password))  # Length of password field
    actual_data += password.encode("utf-8")  # PLC Password
    actual_data += struct.pack(">2s", b"\x05\x00")  # Block of unknown
    actual_data += struct.pack("<H", len(adding_host_name))  # Length of route name
    actual_data += adding_host_name.encode(
        "utf-8"
    )  # Name of route being added to the PLC

    data, addr = send_raw_udp_message(
        ip_address, data_header + actual_data, 32
    )  # PLC response is 32 bytes long

    rcvd_packet_header = data[
        0:12
    ]  # AMS Packet header, seems to define communication type
    # If the last byte in the header is 0x80, then this is a response to our request
    if struct.unpack(">B", rcvd_packet_header[-1:])[0] == 0x80:
        rcvd_PLC_AMS_ID = struct.unpack(">6B", data[12:18])[0]  # AMS ID of PLC
        # Convert to a String AMS ID
        rcvd_AMS_port = struct.unpack(
            "<H", data[18:20]
        )  # Some sort of AMS port? Little endian
        rcvd_command_code = struct.unpack(
            "<2s", data[20:22]
        )  # Command code (should be read) Little endian
        rcvd_protocol_block = data[22:]  # Unknown block of protocol
        rcvd_is_password_correct = rcvd_protocol_block[
            4:7
        ]  # 0x040000 when password was correct, 0x000407 when it was incorrect

        if rcvd_is_password_correct == b"\x04\x00\x00":
            return True
        elif rcvd_is_password_correct == b"\x00\x04\x07":
            return False

    # If we fell through the whole way to the bottom, then we got a weird response
    raise RuntimeError(f"Unexpected response from PLC: {data!r}")


def adsGetNetIdForPLC(ip_address: str) -> str:
    """Get AMS Net ID from IP address.
    
    :param str ip_address: ip address of the PLC
    :rtype: str
    :return: net id of the device at the provided ip address
    
    """
    # The head of the UDP AMS packet containing host routing information
    data_header = struct.pack(
        ">12s", b"\x03\x66\x14\x71\x00\x00\x00\x00\x01\x00\x00\x00"
    )
    data_header += struct.pack(
        ">6B", *[1, 1, 1, 1, 1, 1]
    )  # It doesn't matter what NetID you use here, so just send 1.1.1.1.1.1
    data_header += struct.pack("<H", PORT_SYSTEMSERVICE)  # Internal communication port
    data_header += struct.pack(">4s", b"\x00\x00\x00\x00")  # Block of unknown

    data, addr = send_raw_udp_message(
        ip_address, data_header, 395
    )  # PLC response is 395 bytes long

    rcvd_packet_header = data[
        0:12
    ]  # AMS Packet header, seems to define communication type
    # If the last byte in the header is 0x80, then this is a response to our request
    if struct.unpack(">B", rcvd_packet_header[-1:])[0] == 0x80:
        ams_id_tuple = struct.unpack(">6B", data[12:18])  # AMS ID of PLC
        return ".".join(map(str, ams_id_tuple))

    # If we fell through the whole way to the bottom, then we got a weird response
    raise RuntimeError(f"Unexpected response from PLC: {data!r}")


@router_function
def adsDelRoute(net_id: SAmsNetId) -> None:
    """Remove existing route from the AMS Router.

    :param pyads.structs.SAmsNetId net_id: net id associated with the routing
        entry which is to be removed from the router.

    """
    delete_route = _adsDLL.AdsDelRoute
    delete_route(net_id)


def adsPortOpenEx() -> int:
    """Connect to the TwinCAT message router.

    :rtype: int
    :return: port number

    """
    port_open_ex = _adsDLL.AdsPortOpenEx
    port_open_ex.restype = ctypes.c_long
    port = port_open_ex()

    if port == 0:
        raise RuntimeError("Failed to open port on AMS router.")

    return port


def adsPortCloseEx(port: int) -> None:
    """Close the connection to the TwinCAT message router."""
    port_close_ex = _adsDLL.AdsPortCloseEx
    port_close_ex.restype = ctypes.c_long
    error_code = port_close_ex(port)

    if error_code:
        raise ADSError(error_code)


def adsGetLocalAddressEx(port: int) -> AmsAddr:
    """Return the local AMS-address and the port number.

    :rtype: pyads.structs.AmsAddr
    :return: AMS-address

    """
    get_local_address_ex = _adsDLL.AdsGetLocalAddressEx
    ams_address_struct = SAmsAddr()
    error_code = get_local_address_ex(port, ctypes.pointer(ams_address_struct))

    if error_code:
        raise ADSError(error_code)

    local_ams_address = AmsAddr()
    local_ams_address._ams_addr = ams_address_struct

    return local_ams_address


def adsSetLocalAddress(ams_netid: SAmsNetId) -> None:
    """Change the local NetId.

    :param pyads.structs.SAmsNetId ams_netid: new AmsNetID
    :rtype: None

    """
    set_local_address = _adsDLL.AdsSetLocalAddress
    set_local_address(ams_netid)


def adsSyncReadStateReqEx(port: int, address: AmsAddr) -> Tuple[int, int]:
    """Read the current ADS-state and the machine-state.

    Read the current ADS-state and the machine-state from the
    ADS-server.

    :param port: AMS port
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :rtype: (int, int)
    :return: ads_state, device_state

    """
    sync_read_state_request = _adsDLL.AdsSyncReadStateReqEx

    # C pointer to ams address struct
    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())

    # Current ADS status and corresponding pointer
    ads_state = ctypes.c_uint16()
    ads_state_pointer = ctypes.pointer(ads_state)

    # Current device status and corresponding pointer
    device_state = ctypes.c_uint16()
    device_state_pointer = ctypes.pointer(device_state)

    error_code = sync_read_state_request(
        port, ams_address_pointer, ads_state_pointer, device_state_pointer
    )

    if error_code:
        raise ADSError(error_code)

    return ads_state.value, device_state.value


def adsSyncReadDeviceInfoReqEx(port: int, address: AmsAddr) -> Tuple[str, AdsVersion]:
    """Read the name and the version number of the ADS-server.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :rtype: string, AdsVersion
    :return: device name, version

    """
    sync_read_device_info_request = _adsDLL.AdsSyncReadDeviceInfoReqEx

    # Get pointer to the target AMS address
    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())

    # Create buffer to be filled with device name, get pointer to said buffer
    device_name_buffer = ctypes.create_string_buffer(20)
    device_name_pointer = ctypes.pointer(device_name_buffer)

    # Create ADS Version struct and get pointer.
    ads_version = SAdsVersion()
    ads_version_pointer = ctypes.pointer(ads_version)

    error_code = sync_read_device_info_request(
        port, ams_address_pointer, device_name_pointer, ads_version_pointer
    )

    if error_code:
        raise ADSError(error_code)

    return device_name_buffer.value.decode(), AdsVersion(ads_version)


def adsSyncWriteControlReqEx(
    port: int,
    address: AmsAddr,
    ads_state: int,
    device_state: int,
    data: Any,
    plc_data_type: Type,
) -> None:
    """Change the ADS state and the machine-state of the ADS-server.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int ads_state: new ADS-state, according to ADSTATE constants
    :param int device_state: new machine-state
    :param data: additional data
    :param int plc_data_type: plc datatype, according to PLCTYPE constants

    """
    sync_write_control_request = _adsDLL.AdsSyncWriteControlReqEx

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    ads_state_c = ctypes.c_ulong(ads_state)
    device_state_c = ctypes.c_ulong(device_state)

    if type_is_string(plc_data_type):
        data = ctypes.c_char_p(data.encode("utf-8"))
        data_pointer = data
        data_length = len(data_pointer.value) + 1
    else:
        data = plc_data_type(data)
        data_pointer = ctypes.pointer(data)
        data_length = ctypes.sizeof(data)

    error_code = sync_write_control_request(
        port,
        ams_address_pointer,
        ads_state_c,
        device_state_c,
        data_length,
        data_pointer,
    )

    if error_code:
        raise ADSError(error_code)


def adsSyncWriteReqEx(
    port: int,
    address: AmsAddr,
    index_group: int,
    index_offset: int,
    value: Any,
    plc_data_type: Type,
) -> None:
    """Send data synchronous to an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int plc_data_type: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    sync_write_request = _adsDLL.AdsSyncWriteReqEx

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group_c = ctypes.c_ulong(index_group)
    index_offset_c = ctypes.c_ulong(index_offset)

    if type_is_string(plc_data_type):
        data = ctypes.c_char_p(value.encode("utf-8"))
        data_pointer = data  # type: Union[ctypes.c_char_p, ctypes.pointer]
        data_length = len(data_pointer.value) + 1  # type: ignore

    else:
        if type(plc_data_type).__name__ == "PyCArrayType":
            data = plc_data_type(*value)
        elif type(value) is plc_data_type:
            data = value
        else:
            data = plc_data_type(value)

        data_pointer = ctypes.pointer(data)
        data_length = ctypes.sizeof(data)

    error_code = sync_write_request(
        port,
        ams_address_pointer,
        index_group_c,
        index_offset_c,
        data_length,
        data_pointer,
    )

    if error_code:
        raise ADSError(error_code)


def adsSyncReadWriteReqEx2(
    port: int,
    address: AmsAddr,
    index_group: int,
    index_offset: int,
    read_data_type: Optional[Type],
    value: Any,
    write_data_type: Optional[Type],
    return_ctypes: bool = False,
    check_length: bool = True,
) -> Any:
    """Read and write data synchronous from/to an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param Type read_data_type: type of the data given to the PLC to respond to,
        according to PLCTYPE constants, or None to not read anything
    :param value: value to write to the storage address of the PLC
    :param Type write_data_type: type of the data given to the PLC, according to
        PLCTYPE constants, or None to not write anything
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :param bool check_length: check whether the amount of bytes read matches the size
        of the read data type (default: True)
    :rtype: read_data_type
    :return: value: value read from PLC

    """
    sync_read_write_request = _adsDLL.AdsSyncReadWriteReqEx2

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group_c = ctypes.c_ulong(index_group)
    index_offset_c = ctypes.c_ulong(index_offset)
    read_data: Optional[Any]
    read_data_pointer: Optional[ctypes.pointer]
    response_size: int = 0

    if index_group == ADSIGRP_SUMUP_READ:
        response_size = 4 * len(value)
        for _ in value:
            response_size += _.size
        read_data_buf = bytearray(response_size)
        read_data = (ctypes.c_byte * len(read_data_buf)).from_buffer(read_data_buf)
        read_data_pointer = ctypes.pointer(read_data)
        read_length = response_size

    elif index_group == ADSIGRP_SUMUP_WRITE:
        response_size = (
            index_offset * 4
        )  # expect 4 bytes back for every value written (error data)
        read_data_buf = bytearray(response_size)
        read_data = (ctypes.c_byte * len(read_data_buf)).from_buffer(read_data_buf)
        read_data_pointer = ctypes.pointer(read_data)
        read_length = response_size

    elif read_data_type is None:
        read_data = None
        read_data_pointer = None
        read_length = 0
    else:
        if type_is_string(read_data_type):
            read_data = (STRING_BUFFER * PLCTYPE_STRING)()
        else:
            read_data = read_data_type()

        read_data_pointer = ctypes.pointer(read_data)
        read_length = ctypes.sizeof(read_data)

    bytes_read = ctypes.c_ulong()
    bytes_read_pointer = ctypes.pointer(bytes_read)

    write_data_pointer: Optional[Union[ctypes.c_char_p, ctypes.pointer]]
    if index_group == ADSIGRP_SUMUP_READ:
        write_data_pointer = ctypes.pointer(value)
        write_length = ctypes.sizeof(value)
    elif index_group == ADSIGRP_SUMUP_WRITE:
        write_data = (ctypes.c_byte * len(value)).from_buffer(value)
        write_data_pointer = ctypes.pointer(write_data)
        write_length = ctypes.sizeof(write_data)
    elif write_data_type is None:
        write_data_pointer = None
        write_length = 0
    elif type_is_string(write_data_type):
        # Get pointer to string
        write_data_pointer = ctypes.c_char_p(value.encode("utf-8"))
        # Add an extra byte to the data length for the null terminator
        write_length = len(value) + 1
    else:
        if type(write_data_type).__name__ == "PyCArrayType":
            write_data = write_data_type(*value)
        elif type(value) is write_data_type:
            write_data = value
        else:
            write_data = write_data_type(value)
        write_data_pointer = ctypes.pointer(write_data)
        write_length = ctypes.sizeof(write_data)

    err_code = sync_read_write_request(
        port,
        ams_address_pointer,
        index_group_c,
        index_offset_c,
        ctypes.c_ulong(read_length),
        read_data_pointer,
        ctypes.c_ulong(write_length),
        write_data_pointer,
        bytes_read_pointer,
    )

    if err_code:
        raise ADSError(err_code)

    if index_group == ADSIGRP_SUMUP_READ or index_group == ADSIGRP_SUMUP_WRITE:
        expected_length = response_size
    else:
        expected_length = (
            read_data.entryLength
            if isinstance(read_data, SAdsSymbolEntry)
            else read_length
        )

    # If we're reading a value of predetermined size (anything but a string),
    # validate that the correct number of bytes were read
    if (
        check_length
        and not type_is_string(read_data_type)
        and bytes_read.value != expected_length
    ):
        raise RuntimeError(
            "Insufficient data (expected {0} bytes, {1} were read).".format(
                expected_length, bytes_read.value
            )
        )

    if return_ctypes:
        return read_data

    if read_data is not None and type_is_string(read_data_type):
        return read_data.value.decode("utf-8")

    if read_data is not None and type(read_data_type).__name__ == "PyCArrayType":
        return [i for i in read_data]

    if read_data is not None and hasattr(read_data, "value"):
        return read_data.value

    return read_data


def adsSyncReadReqEx2(
    port: int,
    address: AmsAddr,
    index_group: int,
    index_offset: int,
    data_type: Type,
    return_ctypes: bool = False,
    check_length: bool = True,
) -> Any:
    """Read data synchronous from an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param Type data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :param bool check_length: check whether the amount of bytes read matches the size
        of the read data type (default: True)
    :rtype: data_type
    :return: value: **value**

    """
    sync_read_request = _adsDLL.AdsSyncReadReqEx2

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group_c = ctypes.c_ulong(index_group)
    index_offset_c = ctypes.c_ulong(index_offset)

    if type_is_string(data_type):
        data = (STRING_BUFFER * PLCTYPE_STRING)()
    else:
        data = data_type()

    data_pointer = ctypes.pointer(data)
    data_length = ctypes.c_ulong(ctypes.sizeof(data))

    bytes_read = ctypes.c_ulong()
    bytes_read_pointer = ctypes.pointer(bytes_read)

    error_code = sync_read_request(
        port,
        ams_address_pointer,
        index_group_c,
        index_offset_c,
        data_length,
        data_pointer,
        bytes_read_pointer,
    )

    if error_code:
        raise ADSError(error_code)

    # If we're reading a value of predetermined size (anything but a string),
    # validate that the correct number of bytes were read
    if (
        check_length
        and not type_is_string(data_type)
        and bytes_read.value != data_length.value
    ):
        raise RuntimeError(
            "Insufficient data (expected {0} bytes, {1} were read).".format(
                data_length.value, bytes_read.value
            )
        )

    if return_ctypes:
        return data

    if type_is_string(data_type):
        # Note: this does not catch a string with a specified size
        return data.value.decode("utf-8")

    if type(data_type).__name__ == "PyCArrayType":

        if type_is_string(data_type._type_):
            # If the type is a char-array
            return data.value.decode("utf-8")

        return [i for i in data]

    if hasattr(data, "value"):
        return data.value

    return data


def adsGetHandle(port: int, address: AmsAddr, data_name: str) -> int:
    """Get the handle of the PLC-variable.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: data name
    :rtype: int
    :return: handle: PLC-variable handle
    """
    handle = adsSyncReadWriteReqEx2(
        port,
        address,
        ADSIGRP_SYM_HNDBYNAME,
        0x0,
        PLCTYPE_UDINT,
        data_name,
        PLCTYPE_STRING,
    )

    return handle


def adsGetSymbolInfo(port: int, address: AmsAddr, data_name: str) -> SAdsSymbolEntry:
    """Get the symbol information of the PLC-variable.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: data name
    :rtype: SAdsSymbolInfo
    :return: symbol_info: PLC Symbol info
    """
    symbol_info = adsSyncReadWriteReqEx2(
        port,
        address,
        ADSIGRP_SYM_INFOBYNAMEEX,
        0x0,
        SAdsSymbolEntry,
        data_name,
        PLCTYPE_STRING,
    )

    return symbol_info


def adsSumRead(
    port: int, address: AmsAddr, data_names: List[str], data_symbols: Dict[str, SAdsSymbolEntry],
    structured_data_names: List[str],
) -> Dict[str, Any]:
    """Perform a sum read to get the value of multiple variables

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param data_names: list of variables names to read
    :param Dict[str, SAdsSymbolEntry] data_symbols: dictionary of ADS Symbol Info
    :param structured_data_names: list of structured variable names
    :return: result: dict of variable names and values
    :rtype: dict[str, Any]

    """
    result: Dict[str, Optional[Any]] = {i: None for i in data_names}

    num_requests = len(data_names)
    sum_req_array_type = SAdsSumRequest * num_requests
    sum_req_array = sum_req_array_type()

    for i, value in enumerate(data_names):
        sum_req_array[i].iGroup = data_symbols[value].iGroup
        sum_req_array[i].iOffset = data_symbols[value].iOffs
        sum_req_array[i].size = data_symbols[value].size

    sum_response = adsSyncReadWriteReqEx2(
        port,
        address,
        ADSIGRP_SUMUP_READ,
        num_requests,
        None,
        sum_req_array,
        None,
        return_ctypes=False,
        check_length=False,
    )

    offset = 0
    data_start = 4 * num_requests

    for i, data_name in enumerate(data_names):
        error = struct.unpack_from("<I", sum_response, offset=i * 4)[0]
        if error:
            result[data_name] = ERROR_CODES[error]
        else:
            if data_name in structured_data_names:
                value = sum_response[
                    data_start + offset :
                    data_start + offset + data_symbols[data_name].size]
            elif (
                data_symbols[data_name].dataType != ADST_STRING
                and data_symbols[data_name].dataType != ADST_WSTRING
            ):
                value = struct.unpack_from(
                    DATATYPE_MAP[ads_type_to_ctype[data_symbols[data_name].dataType]],
                    sum_response,
                    offset=data_start + offset,
                )[0]
            else:
                null_idx = sum_response[
                    data_start
                    + offset : data_start
                    + offset
                    + data_symbols[data_name].size
                ].index(0)
                value = bytearray(
                    sum_response[data_start + offset : data_start + offset + null_idx]
                ).decode("utf-8")
            result[data_name] = value
        offset += data_symbols[data_name].size

    return result


def adsSumWrite(
    port: int,
    address: AmsAddr,
    data_names_and_values: Dict[str, Any],
    data_symbols: Dict[str, SAdsSymbolEntry],
    structured_data_names: List[str],
) -> Dict[str, str]:
    """Perform a sum write to write the value of multiple ADS variables

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param data_names_and_values: dict of variable names and values to be written
    :type data_names_and_values: dict[str, Any]
    :param data_symbols: list of dictionaries of ADS Symbol Info
    :type data_symbols: dict[str, ADSSymbolInfo]
    :param structured_data_names: list of structured variable names
    :return: result: dict of variable names and error codes
    :rtype: dict[str, ADSError]
    """
    offset = 0
    num_requests = len(data_names_and_values)
    total_request_size = num_requests * 3 * 4  # iGroup, iOffset & size

    for data_name in data_names_and_values.keys():
        total_request_size += data_symbols[data_name].size

    buf = bytearray(total_request_size)

    for data_name in data_names_and_values.keys():
        struct.pack_into("<I", buf, offset, data_symbols[data_name].iGroup)
        struct.pack_into("<I", buf, offset + 4, data_symbols[data_name].iOffs)
        struct.pack_into("<I", buf, offset + 8, data_symbols[data_name].size)
        offset += 12

    for data_name, value in data_names_and_values.items():
        if data_name in structured_data_names:
            buf[offset : offset + data_symbols[data_name].size] = value
        elif (
            data_symbols[data_name].dataType != ADST_STRING
            and data_symbols[data_name].dataType != ADST_WSTRING
        ):
            struct.pack_into(
                DATATYPE_MAP[ads_type_to_ctype[data_symbols[data_name].dataType]],
                buf,
                offset,
                value,
            )
        else:
            buf[offset : offset + len(value)] = value.encode("utf-8")
        offset += data_symbols[data_name].size

    sum_response = adsSyncReadWriteReqEx2(
        port,
        address,
        ADSIGRP_SUMUP_WRITE,
        num_requests,
        None,
        buf,
        None,
        return_ctypes=False,
        check_length=False,
    )

    errors = list(struct.iter_unpack("<I", sum_response))
    error_descriptions = [ERROR_CODES[i[0]] for i in errors]

    return dict(zip(data_names_and_values.keys(), error_descriptions))


def adsReleaseHandle(port: int, address: AmsAddr, handle: int) -> None:
    """Release the handle of the PLC-variable.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int handle: handle of PLC-variable to be released
    """
    adsSyncWriteReqEx(port, address, ADSIGRP_SYM_RELEASEHND, 0, handle, PLCTYPE_UDINT)


def adsSyncReadByNameEx(
    port: int,
    address: AmsAddr,
    data_name: str,
    data_type: Type,
    return_ctypes: bool = False,
    handle: int = None,
    check_length: bool = True,
) -> Any:
    """Read data synchronous from an ADS-device from data name.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: data name
    :param Type data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :param bool return_ctypes: return ctypes instead of python types if True
        (default: False)
    :param int handle: PLC-variable handle (default: None)
    :param bool check_length: check whether the amount of bytes read matches the size
        of the read data type (default: True)
    :rtype: data_type
    :return: value: **value**

    """
    if handle is None:
        no_handle = True
        handle = adsGetHandle(port, address, data_name)
    else:
        no_handle = False

    # Read the value of a PLC-variable, via handle
    value = adsSyncReadReqEx2(
        port,
        address,
        ADSIGRP_SYM_VALBYHND,
        handle,
        data_type,
        return_ctypes,
        check_length,
    )

    if no_handle is True:
        adsReleaseHandle(port, address, handle)

    return value


def adsSyncWriteByNameEx(
    port: int,
    address: AmsAddr,
    data_name: str,
    value: Any,
    data_type: Type,
    handle: int = None,
) -> None:
    """Send data synchronous to an ADS-device from data name.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: PLC storage name
    :param value: value to write to the storage address of the PLC
    :param Type data_type: type of the data given to the PLC,
        according to PLCTYPE constants
    :param int handle: PLC-variable handle (default: None)
    """
    if handle is None:
        no_handle = True
        handle = adsGetHandle(port, address, data_name)
    else:
        no_handle = False

    # Write the value of a PLC-variable, via handle
    adsSyncWriteReqEx(port, address, ADSIGRP_SYM_VALBYHND, handle, value, data_type)

    if no_handle is True:
        adsReleaseHandle(port, address, handle)


def adsSyncAddDeviceNotificationReqEx(
    port: int,
    adr: AmsAddr,
    data: Union[str, Tuple[int, int]],
    pNoteAttrib: NotificationAttrib,
    callback: Callable,
    user_handle: Optional[int] = None,
) -> Tuple[int, int]:
    """Add a device notification.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param Union[str, Tuple[int, int]] data: PLC storage address by name or index group and offset
    :param pyads.structs.NotificationAttrib pNoteAttrib: notification attributes
    :param callback: Callback function to handle notification
    :param user_handle: User Handle
    :rtype: (int, int)
    :returns: notification handle, user handle

    """
    global callback_store

    if NOTEFUNC is None:
        raise TypeError("Callback function type can't be None")

    adsSyncAddDeviceNotificationReqFct = _adsDLL.AdsSyncAddDeviceNotificationReqEx

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    if isinstance(data, str):
        hnl = adsSyncReadWriteReqEx2(
            port, adr, ADSIGRP_SYM_HNDBYNAME, 0x0, PLCTYPE_UDINT, data, PLCTYPE_STRING
        )

        nIndexGroup = ctypes.c_ulong(ADSIGRP_SYM_VALBYHND)
        nIndexOffset = ctypes.c_ulong(hnl)
    elif isinstance(data, tuple):
        nIndexGroup = ctypes.c_ulong(data[0])
        nIndexOffset = ctypes.c_ulong(data[1])
        hnl = None
    else:
        raise TypeError(
            "Parameter data has the wrong type %s. Allowed types are: str, Tuple[int, int]."
            % (type(data))
        )

    attrib = pNoteAttrib.notificationAttribStruct()
    pNotification = ctypes.c_ulong()

    nHUser = ctypes.c_ulong(0)
    if hnl is not None:
        nHUser = ctypes.c_ulong(hnl)
    if user_handle is not None:
        nHUser = ctypes.c_ulong(user_handle)

    adsSyncAddDeviceNotificationReqFct.argtypes = [
        ctypes.c_ulong,
        ctypes.POINTER(SAmsAddr),
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(SAdsNotificationAttrib),
        NOTEFUNC,  # type: ignore
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    adsSyncAddDeviceNotificationReqFct.restype = ctypes.c_long

    # noinspection PyUnusedLocal
    def wrapper(addr: SAmsAddr, notification: SAdsNotificationHeader, user: int) -> Callable[
            [SAdsNotificationHeader, str], None]:
        return callback(notification, data)

    # noinspection PyTypeChecker
    c_callback = NOTEFUNC(wrapper)  # type: ignore
    err_code = adsSyncAddDeviceNotificationReqFct(
        port,
        pAmsAddr,
        nIndexGroup,
        nIndexOffset,
        ctypes.byref(attrib),
        c_callback,
        nHUser,
        ctypes.byref(pNotification),
    )

    if err_code:
        raise ADSError(err_code)
    callback_store[(adr, pNotification.value)] = c_callback
    return pNotification.value, hnl


def adsSyncDelDeviceNotificationReqEx(
    port: int, adr: AmsAddr, notification_handle: int, user_handle: int
) -> None:
    """Remove a device notification.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int notification_handle: Notification Handle
    :param int user_handle: User Handle

    """
    adsSyncDelDeviceNotificationReqFct = _adsDLL.AdsSyncDelDeviceNotificationReqEx

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    nHNotification = ctypes.c_ulong(notification_handle)
    err_code = adsSyncDelDeviceNotificationReqFct(port, pAmsAddr, nHNotification)
    del callback_store[(adr, notification_handle)]
    if err_code:
        raise ADSError(err_code)

    if user_handle is not None:
        adsSyncWriteReqEx(
            port, adr, ADSIGRP_SYM_RELEASEHND, 0, user_handle, PLCTYPE_UDINT
        )


def adsSyncSetTimeoutEx(port: int, n_ms: int) -> None:
    """Set Timeout.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param int n_ms: timeout in ms

    """
    adsSyncSetTimeoutFct = _adsDLL.AdsSyncSetTimeoutEx
    cms = ctypes.c_long(n_ms)
    err_code = adsSyncSetTimeoutFct(port, cms)
    if err_code:
        raise ADSError(err_code)
