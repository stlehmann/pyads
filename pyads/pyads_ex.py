# -*- coding: utf-8 -*-
"""Contains cross platform ADS extension functions.

:author: David Browne <davidabrowne@gmail.com>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:53
:last modified by: lehmann
:last modified time: 2018-08-16 10:05:32

"""
from typing import Union, Callable, Any, Tuple, Type, Optional
import ctypes
import os
import sys

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
    NotificationAttrib,
)
from .constants import (
    PLCTYPE_STRING,
    STRING_BUFFER,
    ADSIGRP_SYM_HNDBYNAME,
    PLCTYPE_UDINT,
    ADSIGRP_SYM_VALBYHND,
    ADSIGRP_SYM_RELEASEHND,
)
from .errorcodes import ERROR_CODES


# Python version checking
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


NOTEFUNC = None

# load dynamic ADS library
if platform_is_windows():
    _adsDLL = ctypes.windll.TcAdsDll  # type: Union[ctypes.CDLL, ctypes.WinDLL]
    NOTEFUNC = ctypes.WINFUNCTYPE(
        ctypes.c_void_p,
        ctypes.POINTER(SAmsAddr),
        ctypes.POINTER(SAdsNotificationHeader),
        ctypes.c_ulong,
    )

elif platform_is_linux:
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
else:
    raise RuntimeError("Unsupported platform {0}.".format(sys.platform))

callback_store = dict()


class ADSError(Exception):
    """Error class for errors related to ADS communication."""

    def __init__(self, err_code=None, text=None):
        # type: (Optional[int], Optional[str]) -> None
        if err_code is not None:
            self.err_code = err_code
            try:
                self.msg = "{} ({}). ".format(
                    ERROR_CODES[self.err_code], self.err_code
                )
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


def router_function(fn):
    # type: (Callable) -> Callable
    """Raise a runtime error if on Win32 systems.

    Decorator.

    Decorator for functions that interact with the router for the Linux
    implementation of the ADS library.

    Unlike the Windows implementation which uses a separate router daemon,
    the Linux library manages AMS routing in-process. As such, routing must be
    configured programatically via. the provided API. These endpoints are
    invalid on Win32 systems, so an exception will be raised.

    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # type: (Any, Any) -> Callable
        if platform_is_windows():
            raise RuntimeError(
                "Router interface is not available on Win32 systems.\n"
                "Configure AMS routes using the TwinCAT router service."
            )
        return fn(*args, **kwargs)

    return wrapper


@router_function
def adsAddRoute(net_id, ip_address):
    # type: (SAmsNetId, str) -> None
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


@router_function
def adsDelRoute(net_id):
    # type: (SAmsNetId) -> None
    """Remove existing route from the AMS Router.

    :param pyads.structs.SAmsNetId net_id: net id associated with the routing
        entry which is to be removed from the router.

    """
    delete_route = _adsDLL.AdsDelRoute
    delete_route(net_id)


def adsPortOpenEx():
    # type: () -> int
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


def adsPortCloseEx(port):
    # type: (int) -> None
    """Close the connection to the TwinCAT message router."""
    port_close_ex = _adsDLL.AdsPortCloseEx
    port_close_ex.restype = ctypes.c_long
    error_code = port_close_ex(port)

    if error_code:
        raise ADSError(error_code)


def adsGetLocalAddressEx(port):
    # type: (int) -> AmsAddr
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


def adsSetLocalAddress(ams_netid):
    # type: (SAmsNetId) -> None
    """Change the local NetId.

    :param pyads.structs.SAmsNetId ams_netid: new AmsNetID
    :rtype: None

    """
    set_local_address = _adsDLL.AdsSetLocalAddress
    set_local_address(ams_netid)


def adsSyncReadStateReqEx(port, address):
    # type: (int, AmsAddr) -> Tuple[int, int]
    """Read the current ADS-state and the machine-state.

    Read the current ADS-state and the machine-state from the
    ADS-server.

    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :rtype: (int, int)
    :return: ads_state, device_state

    """
    sync_read_state_request = _adsDLL.AdsSyncReadStateReqEx

    # C pointer to ams address struct
    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())

    # Current ADS status and corresponding pointer
    ads_state = ctypes.c_int()
    ads_state_pointer = ctypes.pointer(ads_state)

    # Current device status and corresponding pointer
    device_state = ctypes.c_int()
    device_state_pointer = ctypes.pointer(device_state)

    error_code = sync_read_state_request(
        port, ams_address_pointer, ads_state_pointer, device_state_pointer
    )

    if error_code:
        raise ADSError(error_code)

    return (ads_state.value, device_state.value)


def adsSyncReadDeviceInfoReqEx(port, address):
    # type: (int, AmsAddr) -> Tuple[str, AdsVersion]
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

    return (device_name_buffer.value.decode(), AdsVersion(ads_version))


def adsSyncWriteControlReqEx(
    port, address, ads_state, device_state, data, plc_data_type
):
    # type: (int, AmsAddr, int, int, Any, Type) -> None
    """Change the ADS state and the machine-state of the ADS-server.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int ads_state: new ADS-state, according to ADSTATE constants
    :param int device_state: new machine-state
    :param data: additional data
    :param int plc_data_type: plc datatype, according to PLCTYPE constants

    """
    sync_write_control_request = _adsDLL.AdsSyncWriteControlReqEx

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    ads_state_c = ctypes.c_ulong(ads_state)
    device_state_c = ctypes.c_ulong(device_state)

    if plc_data_type == PLCTYPE_STRING:
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
    port, address, index_group, index_offset, value, plc_data_type
):
    # type: (int, AmsAddr, int, int, Any, Type) -> None
    """Send data synchronous to an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int indexGroup: PLC storage area, according to the INDEXGROUP
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

    if plc_data_type == PLCTYPE_STRING:
        data = ctypes.c_char_p(value.encode("utf-8"))
        data_pointer = data  # type: Union[ctypes.c_char_p, ctypes.pointer]
        data_length = len(data_pointer.value) + 1  # type: ignore

    else:
        if type(plc_data_type).__name__ == "PyCArrayType":
            data = plc_data_type(*value)
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
    port,
    address,
    index_group,
    index_offset,
    read_data_type,
    value,
    write_data_type,
):
    # type: (int, AmsAddr, int, int, Type, Any, Type) -> Any
    """Read and write data synchronous from/to an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param Type read_data_type: type of the data given to the PLC to respond to,
        according to PLCTYPE constants
    :param value: value to write to the storage address of the PLC
    :param Type write_data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: read_data_type
    :return: value: value read from PLC

    """
    sync_read_write_request = _adsDLL.AdsSyncReadWriteReqEx2

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group_c = ctypes.c_ulong(index_group)
    index_offset_c = ctypes.c_ulong(index_offset)

    if read_data_type == PLCTYPE_STRING:
        read_data = (STRING_BUFFER * PLCTYPE_STRING)()
    else:
        read_data = read_data_type()

    read_data_pointer = ctypes.pointer(read_data)
    read_length = ctypes.c_ulong(ctypes.sizeof(read_data))

    bytes_read = ctypes.c_ulong()
    bytes_read_pointer = ctypes.pointer(bytes_read)

    if write_data_type == PLCTYPE_STRING:
        # Get pointer to string
        write_data_pointer = ctypes.c_char_p(
            value.encode("utf-8")
        )  # type: Union[ctypes.c_char_p, ctypes.pointer]  # noqa: E501
        # Add an extra byte to the data length for the null terminator
        write_length = len(value) + 1
    else:
        write_data = write_data_type(value)
        write_data_pointer = ctypes.pointer(write_data)
        write_length = ctypes.sizeof(write_data)

    err_code = sync_read_write_request(
        port,
        ams_address_pointer,
        index_group_c,
        index_offset_c,
        read_length,
        read_data_pointer,
        write_length,
        write_data_pointer,
        bytes_read_pointer,
    )

    if err_code:
        raise ADSError(err_code)

    # If we're reading a value of predetermined size (anything but a string),
    # validate that the correct number of bytes were read
    if (
        read_data_type != PLCTYPE_STRING
        and bytes_read.value != read_length.value
    ):
        raise RuntimeError(
            "Insufficient data (expected {0} bytes, {1} were read).".format(
                read_length.value, bytes_read.value
            )
        )

    if read_data_type == PLCTYPE_STRING:
        return read_data.value.decode("utf-8")

    if type(read_data_type).__name__ == "PyCArrayType":
        return [i for i in read_data]

    if hasattr(read_data, "value"):
        return read_data.value

    return read_data


def adsSyncReadReqEx2(port, address, index_group, index_offset, data_type):
    # type: (int, AmsAddr, int, int, Type) -> Any
    """Read data synchronous from an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param Type data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: data_type
    :return: value: **value**

    """
    sync_read_request = _adsDLL.AdsSyncReadReqEx2

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group_c = ctypes.c_ulong(index_group)
    index_offset_c = ctypes.c_ulong(index_offset)

    if data_type == PLCTYPE_STRING:
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
    if data_type != PLCTYPE_STRING and bytes_read.value != data_length.value:
        raise RuntimeError(
            "Insufficient data (expected {0} bytes, {1} were read).".format(
                data_length.value, bytes_read.value
            )
        )

    if data_type == PLCTYPE_STRING:
        return data.value.decode("utf-8")

    if type(data_type).__name__ == "PyCArrayType":
        return [i for i in data]

    if hasattr(data, "value"):
        return data.value

    return data


def adsSyncReadByNameEx(port, address, data_name, data_type):
    # type: (int, AmsAddr, str, Type) -> Any
    """Read data synchronous from an ADS-device from data name.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: data name
    :param Type data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: data_type
    :return: value: **value**

    """
    # Get the handle of the PLC-variable
    handle = adsSyncReadWriteReqEx2(
        port,
        address,
        ADSIGRP_SYM_HNDBYNAME,
        0x0,
        PLCTYPE_UDINT,
        data_name,
        PLCTYPE_STRING,
    )

    # Read the value of a PLC-variable, via handle
    value = adsSyncReadReqEx2(
        port, address, ADSIGRP_SYM_VALBYHND, handle, data_type
    )

    # Release the handle of the PLC-variable
    adsSyncWriteReqEx(
        port, address, ADSIGRP_SYM_RELEASEHND, 0, handle, PLCTYPE_UDINT
    )

    return value


def adsSyncWriteByNameEx(port, address, data_name, value, data_type):
    # type: (int, AmsAddr, str, Any, Type) -> None
    """Send data synchronous to an ADS-device from data name.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param Type data_type: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    # Get the handle of the PLC-variable
    handle = adsSyncReadWriteReqEx2(
        port,
        address,
        ADSIGRP_SYM_HNDBYNAME,
        0x0,
        PLCTYPE_UDINT,
        data_name,
        PLCTYPE_STRING,
    )

    # Write the value of a PLC-variable, via handle
    adsSyncWriteReqEx(
        port, address, ADSIGRP_SYM_VALBYHND, handle, value, data_type
    )

    # Release the handle of the PLC-variable
    adsSyncWriteReqEx(
        port, address, ADSIGRP_SYM_RELEASEHND, 0, handle, PLCTYPE_UDINT
    )


def adsSyncAddDeviceNotificationReqEx(
    port, adr, data_name, pNoteAttrib, callback, user_handle=None
):
    # type: (int, AmsAddr, str, NotificationAttrib, Callable, int) -> Tuple[int, int]
    """Add a device notification.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param string data_name: PLC storage address
    :param pyads.structs.NotificationAttrib pNoteAttrib: notification attributes
    :param callback: Callback function to handle notification
    :param user_handle: User Handle
    :rtype: (int, int)
    :returns: notification handle, user handle

    """
    global callback_store

    if NOTEFUNC is None:
        raise TypeError("Callback function type can't be None")

    adsSyncAddDeviceNotificationReqFct = (
        _adsDLL.AdsSyncAddDeviceNotificationReqEx
    )

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    hnl = adsSyncReadWriteReqEx2(
        port,
        adr,
        ADSIGRP_SYM_HNDBYNAME,
        0x0,
        PLCTYPE_UDINT,
        data_name,
        PLCTYPE_STRING,
    )

    nIndexGroup = ctypes.c_ulong(ADSIGRP_SYM_VALBYHND)
    nIndexOffset = ctypes.c_ulong(hnl)
    attrib = pNoteAttrib.notificationAttribStruct()
    pNotification = ctypes.c_ulong()

    nHUser = ctypes.c_ulong(hnl)
    if user_handle is not None:
        nHUser = ctypes.c_ulong(user_handle)

    adsSyncAddDeviceNotificationReqFct.argtypes = [
        ctypes.c_ulong,
        ctypes.POINTER(SAmsAddr),
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(SAdsNotificationAttrib),
        NOTEFUNC,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    adsSyncAddDeviceNotificationReqFct.restype = ctypes.c_long

    def wrapper(addr, notification, user):
        return callback(notification, data_name)

    c_callback = NOTEFUNC(wrapper)
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
    callback_store[pNotification.value] = c_callback
    return (pNotification.value, hnl)


def adsSyncDelDeviceNotificationReqEx(
    port, adr, notification_handle, user_handle
):
    # type: (int, AmsAddr, int, int) -> None
    """Remove a device notification.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int notification_handle: Notification Handle
    :param int user_handle: User Handle

    """
    adsSyncDelDeviceNotificationReqFct = (
        _adsDLL.AdsSyncDelDeviceNotificationReqEx
    )

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    nHNotification = ctypes.c_ulong(notification_handle)
    err_code = adsSyncDelDeviceNotificationReqFct(
        port, pAmsAddr, nHNotification
    )
    callback_store.pop(notification_handle, None)
    if err_code:
        raise ADSError(err_code)

    adsSyncWriteReqEx(
        port, adr, ADSIGRP_SYM_RELEASEHND, 0, user_handle, PLCTYPE_UDINT
    )


def adsSyncSetTimeoutEx(port, nMs):
    # type: (int, int) -> None
    """Set Timeout.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param int nMs: timeout in ms

    """
    adsSyncSetTimeoutFct = _adsDLL.AdsSyncSetTimeoutEx
    cms = ctypes.c_long(nMs)
    err_code = adsSyncSetTimeoutFct(port, cms)
    if err_code:
        raise ADSError(err_code)
