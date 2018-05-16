# -*- coding: utf-8 -*-
"""
pyads.pyads_ex
~~~~~~~~~~~~~~

Contains cross platform ADS extension functions.

:Author: David Browne <davidabrowne@gmail.com>
:license: MIT, see LICENSE for details

"""
import ctypes
import os
import sys

from functools import wraps

from .utils import platform_is_linux, platform_is_windows
from .structs import AmsAddr, SAmsAddr, AdsVersion, SAdsVersion, \
    SAdsNotificationAttrib, SAdsNotificationHeader
from .pyads import ADSError
from .constants import (
    PLCTYPE_STRING, STRING_BUFFER, ADSIGRP_SYM_HNDBYNAME, PLCTYPE_UDINT,
    ADSIGRP_SYM_VALBYHND, ADSIGRP_SYM_RELEASEHND
)

# Python version checking
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


LNOTEFUNC = None

# load dynamic ADS library
if platform_is_windows():
    _adsDLL = ctypes.windll.TcAdsDll

elif platform_is_linux:
    # try to load local adslib.so in favor to global one
    local_adslib = os.path.join(os.path.dirname(__file__), 'adslib.so')
    if os.path.isfile(local_adslib):
        adslib = local_adslib
    else:
        adslib = 'adslib.so'

    _adsDLL = ctypes.CDLL(adslib)

    LNOTEFUNC = ctypes.CFUNCTYPE(None, ctypes.POINTER(SAmsAddr),
                                 ctypes.POINTER(SAdsNotificationHeader),
                                 ctypes.c_ulong)
else:
    raise RuntimeError('Unsupported platform {0}.'.format(sys.platform))

callback_store = dict()


def router_function(fn):
    """
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
        if platform_is_windows():
            raise RuntimeError(
                'Router interface is not available on Win32 systems.\n'
                'Configure AMS routes using the TwinCAT router service.'
            )
        return fn(*args, **kwargs)

    return wrapper


@router_function
def adsAddRoute(net_id, ip_address):
    """
    :summary: Establish a new route in the AMS Router.

    :param pyads.structs.SAmsNetId net_id: net id of routing endpoint
    :param str ip_address: ip address of the routing endpoint

    """
    add_route = _adsDLL.AdsAddRoute
    add_route.restype = ctypes.c_long

    # Convert ip address to bytes (PY3) and get pointer.
    ip_address = ctypes.c_char_p(ip_address.encode('utf-8'))

    error_code = add_route(net_id, ip_address)

    if error_code:
        raise ADSError(error_code)


@router_function
def adsDelRoute(net_id):
    """
    :summary:  Remove existing route from the AMS Router.

    :param pyads.structs.SAmsNetId net_id: net id associated with the routing
        entry which is to be removed from the router.

    """
    delete_route = _adsDLL.AdsDelRoute
    delete_route(net_id)


def adsPortOpenEx():
    """
    :summary:  Connect to the TwinCAT message router.

    :rtype: int
    :return: port number

    """
    port_open_ex = _adsDLL.AdsPortOpenEx
    port_open_ex.restype = ctypes.c_long
    port = port_open_ex()

    if port == 0:
        raise RuntimeError('Failed to open port on AMS router.')

    return port


def adsPortCloseEx(port):
    """:summary: Close the connection to the TwinCAT message router."""
    port_close_ex = _adsDLL.AdsPortCloseEx
    port_close_ex.restype = ctypes.c_long
    error_code = port_close_ex(port)

    if error_code:
        raise ADSError(error_code)


def adsGetLocalAddressEx(port):
    """
    :summary: Return the local AMS-address and the port number.

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
    """
    :summary: Change the local NetId.

    :param pyads.structs.SAmsNetId ams_netid: new AmsNetID
    :rtype: None

    """
    set_local_address = _adsDLL.AdsSetLocalAddress
    set_local_address(ams_netid)


def adsSyncReadStateReqEx(port, address):
    """
    :summary: Read the current ADS-state and the machine-state.

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
    """
    :summary: Read the name and the version number of the ADS-server.

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


def adsSyncWriteControlReqEx(port, address, ads_state, device_state,
                             data, plc_data_type):
    """
    :summary: Change the ADS state and the machine-state of the ADS-server.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int ads_state: new ADS-state, according to ADSTATE constants
    :param int device_state: new machine-state
    :param data: additional data
    :param int plc_data_type: plc datatype, according to PLCTYPE constants

    """
    sync_write_control_request = _adsDLL.AdsSyncWriteControlReqEx

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    ads_state = ctypes.c_ulong(ads_state)
    device_state = ctypes.c_ulong(device_state)

    if plc_data_type == PLCTYPE_STRING:
        data = ctypes.c_char_p(data.encode('utf-8'))
        data_pointer = data
        data_length = len(data_pointer.value) + 1
    else:
        data = plc_data_type(data)
        data_pointer = ctypes.pointer(data)
        data_length = ctypes.sizeof(data)

    error_code = sync_write_control_request(
        port, ams_address_pointer, ads_state,
        device_state, data_length, data_pointer
    )

    if error_code:
        raise ADSError(error_code)


def adsSyncWriteReqEx(port, address, index_group, index_offset, value,
                      plc_data_type):
    """
    :summary: Send data synchronous to an ADS-device.

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
    index_group = ctypes.c_ulong(index_group)
    index_offset = ctypes.c_ulong(index_offset)

    if plc_data_type == PLCTYPE_STRING:
        data = ctypes.c_char_p(value.encode('utf-8'))
        data_pointer = data
        data_length = len(data_pointer.value) + 1

    else:
        if type(plc_data_type).__name__ == 'PyCArrayType':
            data = plc_data_type(*value)
        else:
            data = plc_data_type(value)

        data_pointer = ctypes.pointer(data)
        data_length = ctypes.sizeof(data)

    error_code = sync_write_request(
        port, ams_address_pointer, index_group,
        index_offset, data_length, data_pointer
    )

    if error_code:
        raise ADSError(error_code)


def adsSyncReadWriteReqEx2(port, address, index_group, index_offset,
                           read_data_type, value, write_data_type):
    """
    :summary: Read and write data synchronous from/to an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param int read_data_type: type of the data given to the PLC to respond to,
        according to PLCTYPE constants
    :param value: value to write to the storage address of the PLC
    :param write_data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: read_data_type
    :return: value: value read from PLC

    """
    sync_read_write_request = _adsDLL.AdsSyncReadWriteReqEx2

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group = ctypes.c_ulong(index_group)
    index_offset = ctypes.c_ulong(index_offset)

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
        write_data_pointer = ctypes.c_char_p(value.encode('utf-8'))
        # Add an extra byte to the data length for the null terminator
        write_length = len(value) + 1
    else:
        write_data = write_data_type(value)
        write_data_pointer = ctypes.pointer(write_data)
        write_length = ctypes.sizeof(write_data)

    err_code = sync_read_write_request(
        port, ams_address_pointer, index_group, index_offset, read_length,
        read_data_pointer, write_length, write_data_pointer, bytes_read_pointer
    )

    if err_code:
        raise ADSError(err_code)

    # If we're reading a value of predetermined size (anything but a string),
    # validate that the correct number of bytes were read
    if (read_data_type != PLCTYPE_STRING and
            bytes_read.value != read_length.value):
        raise RuntimeError(
            "Insufficient data (expected {0} bytes, {1} were read)."
            .format(read_length.value, bytes_read.value)
        )

    if read_data_type == PLCTYPE_STRING:
        return read_data.value.decode('utf-8')

    if type(read_data_type).__name__ == 'PyCArrayType':
        return [i for i in read_data]

    if hasattr(read_data, 'value'):
        return read_data.value

    return read_data


def adsSyncReadReqEx2(port, address, index_group, index_offset, data_type):
    """
    :summary: Read data synchronous from an ADS-device.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param int index_group: PLC storage area, according to the INDEXGROUP
        constants
    :param int index_offset: PLC storage address
    :param int data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: data_type
    :return: value: **value**

    """
    sync_read_request = _adsDLL.AdsSyncReadReqEx2

    ams_address_pointer = ctypes.pointer(address.amsAddrStruct())
    index_group = ctypes.c_ulong(index_group)
    index_offset = ctypes.c_ulong(index_offset)

    if data_type == PLCTYPE_STRING:
        data = (STRING_BUFFER * PLCTYPE_STRING)()
    else:
        data = data_type()

    data_pointer = ctypes.pointer(data)
    data_length = ctypes.c_ulong(ctypes.sizeof(data))

    bytes_read = ctypes.c_ulong()
    bytes_read_pointer = ctypes.pointer(bytes_read)

    error_code = sync_read_request(
        port, ams_address_pointer, index_group, index_offset,
        data_length, data_pointer, bytes_read_pointer
    )

    if error_code:
        raise ADSError(error_code)

    # If we're reading a value of predetermined size (anything but a string),
    # validate that the correct number of bytes were read
    if data_type != PLCTYPE_STRING and bytes_read.value != data_length.value:
        raise RuntimeError(
            "Insufficient data (expected {0} bytes, {1} were read)."
            .format(data_length.value, bytes_read.value)
        )

    if data_type == PLCTYPE_STRING:
        return data.value.decode('utf-8')

    if type(data_type).__name__ == 'PyCArrayType':
        return [i for i in data]

    if hasattr(data, 'value'):
        return data.value

    return data


def adsSyncReadByNameEx(port, address, data_name, data_type):
    """
    :summary: Read data synchronous from an ADS-device from data name.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: data name
    :param int data_type: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: data_type
    :return: value: **value**

    """
    # Get the handle of the PLC-variable
    handle = adsSyncReadWriteReqEx2(
        port, address, ADSIGRP_SYM_HNDBYNAME, 0x0,
        PLCTYPE_UDINT, data_name, PLCTYPE_STRING
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
    """
    :summary: Send data synchronous to an ADS-device from data name.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr address: local or remote AmsAddr
    :param string data_name: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int data_type: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    # Get the handle of the PLC-variable
    handle = adsSyncReadWriteReqEx2(
        port, address, ADSIGRP_SYM_HNDBYNAME, 0x0,
        PLCTYPE_UDINT, data_name, PLCTYPE_STRING
    )

    # Write the value of a PLC-variable, via handle
    adsSyncWriteReqEx(
        port, address, ADSIGRP_SYM_VALBYHND, handle, value, data_type
    )

    # Release the handle of the PLC-variable
    adsSyncWriteReqEx(
        port, address, ADSIGRP_SYM_RELEASEHND, 0, handle, PLCTYPE_UDINT
    )


def adsSyncAddDeviceNotificationReqEx(port, adr, data_name, pNoteAttrib,
                                      callback, user_handle=None):
    """
    :summary: Add a device notification.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param string data_name: PLC storage address
    :param pNoteAttrib: notification attributes
    :param callback: Callback function to handle notification
    :param user_handle: User Handle
    :rtype: (int, int)
    :returns: notification handle, user handle

    """
    global callback_store

    adsSyncAddDeviceNotificationReqFct = \
        _adsDLL.AdsSyncAddDeviceNotificationReqEx

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    hnl = adsSyncReadWriteReqEx2(port, adr, ADSIGRP_SYM_HNDBYNAME, 0x0,
                                 PLCTYPE_UDINT, data_name, PLCTYPE_STRING)

    nIndexGroup = ctypes.c_ulong(ADSIGRP_SYM_VALBYHND)
    nIndexOffset = ctypes.c_ulong(hnl)
    attrib = pNoteAttrib.notificationAttribStruct()
    pNotification = ctypes.c_ulong()

    nHUser = ctypes.c_ulong(hnl)
    if user_handle is not None:
        nHUser = ctypes.c_ulong(user_handle)

    if LNOTEFUNC is None:
        raise TypeError("Callback function type can't be None")
    adsSyncAddDeviceNotificationReqFct.argtypes = [
        ctypes.c_ulong, ctypes.POINTER(SAmsAddr),
        ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(SAdsNotificationAttrib),
        LNOTEFUNC, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong)
    ]
    adsSyncAddDeviceNotificationReqFct.restype = ctypes.c_long

    c_callback = LNOTEFUNC(callback)
    err_code = adsSyncAddDeviceNotificationReqFct(
        port, pAmsAddr, nIndexGroup, nIndexOffset,
        ctypes.byref(attrib),
        c_callback, nHUser,
        ctypes.byref(pNotification))

    if err_code:
        raise ADSError(err_code)
    callback_store[pNotification.value] = c_callback
    return (pNotification.value, hnl)


def adsSyncDelDeviceNotificationReqEx(port, adr, notification_handle,
                                      user_handle):
    """
    :summary: Remove a device notification.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int notification_handle: Notification Handle
    :param int user_handle: User Handle

    """
    adsSyncDelDeviceNotificationReqFct = \
        _adsDLL.AdsSyncDelDeviceNotificationReqEx

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    nHNotification = ctypes.c_ulong(notification_handle)
    err_code = adsSyncDelDeviceNotificationReqFct(port, pAmsAddr,
                                                  nHNotification)
    callback_store[notification_handle] = None
    if err_code:
        raise ADSError(err_code)

    adsSyncWriteReqEx(port, adr, ADSIGRP_SYM_RELEASEHND, 0, user_handle,
                      PLCTYPE_UDINT)


def adsSyncSetTimeoutEx(port, nMs):
    """
    :summary: Set Timeout.

    :param int port: local AMS port as returned by adsPortOpenEx()
    :param int nMs: timeout in ms

    """
    adsSyncSetTimeoutFct = _adsDLL.AdsSyncSetTimeoutEx
    cms = ctypes.c_long(nMs)
    err_code = adsSyncSetTimeoutFct(port, cms)
    if err_code:
        raise ADSError(err_code)
