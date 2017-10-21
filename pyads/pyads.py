# -*- coding: utf-8 -*-
"""
    pyads.pyads
    ~~~~~~~~~~~

    Contains ADS functions.

    :copyright: (c) 2013 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""
import ctypes
from ctypes import c_long, sizeof, pointer, c_int, \
    c_ulong, c_char_p, create_string_buffer, memmove, addressof, c_void_p, \
    POINTER
from functools import wraps

from .constants import PLCTYPE_STRING, PLCTYPE_UDINT, ADSIGRP_SYM_HNDBYNAME, \
    ADSIGRP_SYM_VALBYHND, ADSIGRP_SYM_RELEASEHND, STRING_BUFFER
from .structs import AdsVersion, SAdsVersion, SAmsAddr, AmsAddr, \
    SAdsNotificationAttrib, SAdsNotificationHeader
from .errorcodes import ERROR_CODES
from .utils import platform_is_windows


# load dynamic ADS library
if platform_is_windows():
    _adsDLL = ctypes.windll.TcAdsDll  #: ADS-DLL (Beckhoff TwinCAT)

    if not hasattr(_adsDLL, 'AdsPortOpenEx'):
        from warnings import warn
        warn(
            "Compatibility with this version of TcAdsDll.dll will be removed in the next pyads release (v2.3.0). "
            "Update to TwinCAT 2.10 1243 or greater to ensure continued compatibility.",
            DeprecationWarning
        )


class ADSError(Exception):
    def __init__(self, err_code):
        self.err_code = err_code
        try:
            self.msg = "{} ({})".format(ERROR_CODES[self.err_code],
                                        self.err_code)
        except KeyError:
            self.msg = 'Unknown Error ({0})'.format(self.err_code)

    def __str__(self):
        return "ADSError: " + self.msg


def win32_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not platform_is_windows():
            raise RuntimeError(
                '{0} is only supported when using the TcAdsDll (win32).'
                .format(fn.__name__)
            )
        return fn(*args, **kwargs)

    return wrapper


@win32_only
def adsGetDllVersion():
    """
    :summary: Return version, revision and build of the ADS library.
    :rtype: pyads.structs.AdsVersion
    :return: version, revision and build of the ads-dll

    """
    resLong = c_long(_adsDLL.AdsGetDllVersion())
    stVersion = SAdsVersion()
    fit = min(sizeof(stVersion), sizeof(resLong))
    memmove(addressof(stVersion), addressof(resLong), fit)
    return AdsVersion(stVersion)


@win32_only
def adsPortOpen():
    """
    :summary:  Connect to the TwinCAT message router.
    :rtype: int
    :return: port number

    """
    adsPortOpenFct = _adsDLL.AdsPortOpen
    adsPortOpenFct.restype = c_long
    portNr = adsPortOpenFct()
    return portNr


@win32_only
def adsPortClose():
    """
    :summary: Close the connection to the TwinCAT message router.

    """
    adsPortCloseFct = _adsDLL.AdsPortClose
    adsPortCloseFct.restype = c_long
    errCode = adsPortCloseFct()
    if errCode:
        raise ADSError(errCode)


@win32_only
def adsGetLocalAddress():
    """
    :summary: Return the local AMS-address and the port number.
    :rtype: pyads.structs.AmsAddr
    :return: AMS-address

    """
    adsGetLocalAddressFct = _adsDLL.AdsGetLocalAddress
    stAmsAddr = SAmsAddr()
    errCode = adsGetLocalAddressFct(pointer(stAmsAddr))

    if errCode:
        raise ADSError(errCode)

    adsLocalAddr = AmsAddr()
    adsLocalAddr._ams_addr = stAmsAddr
    return adsLocalAddr


@win32_only
def adsSyncReadStateReq(adr):
    """
    :summary: Read the current ADS-state and the machine-state from the
        ADS-server
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :rtype: (int, int)
    :return: adsState, deviceState

    """
    adsSyncReadStateReqFct = _adsDLL.AdsSyncReadStateReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    adsState = c_int()
    pAdsState = pointer(adsState)
    deviceState = c_int()
    pDeviceState = pointer(deviceState)

    errCode = adsSyncReadStateReqFct(pAmsAddr, pAdsState, pDeviceState)
    if errCode:
        raise ADSError(errCode)

    return (adsState.value, deviceState.value)


@win32_only
def adsSyncReadDeviceInfoReq(adr):
    """
    :summary: Read the name and the version number of the ADS-server
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :rtype: string, AdsVersion
    :return: device name, version

    """
    adsSyncReadDeviceInfoReqFct = _adsDLL.AdsSyncReadDeviceInfoReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    devNameStringBuffer = create_string_buffer(20)
    pDevName = pointer(devNameStringBuffer)
    stVersion = SAdsVersion()
    pVersion = pointer(stVersion)

    errCode = adsSyncReadDeviceInfoReqFct(pAmsAddr, pDevName, pVersion)
    if errCode:
        raise ADSError(errCode)
    return (devNameStringBuffer.value.decode(), AdsVersion(stVersion))


@win32_only
def adsSyncWriteControlReq(adr, adsState, deviceState, data, plcDataType):
    """
    :summary: Change the ADS state and the machine-state of the ADS-server

    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int adsState: new ADS-state, according to ADSTATE constants
    :param int deviceState: new machine-state
    :param data: additional data
    :param int plcDataType: plc datatype, according to PLCTYPE constants

    :note: Despite changing the ADS-state and the machine-state it is possible

    to send additional data to the ADS-server. For current ADS-devices
    additional data is not progressed.
    Every ADS-device is able to communicate its current state to other devices.
    There is a difference between the device-state and the state of the
    ADS-interface (AdsState). The possible states of an ADS-interface are
    defined in the ADS-specification.

    """
    adsSyncWriteControlReqFct = _adsDLL.AdsSyncWriteControlReq

    pAddr = pointer(adr.amsAddrStruct())
    nAdsState = c_ulong(adsState)
    nDeviceState = c_ulong(deviceState)

    if plcDataType == PLCTYPE_STRING:
        nData = c_char_p(data.encode())
        pData = nData
        nLength = len(pData.value) + 1
    else:
        nData = plcDataType(data)
        pData = pointer(nData)
        nLength = sizeof(nData)

    errCode = adsSyncWriteControlReqFct(pAddr, nAdsState, nDeviceState,
                                        nLength, pData)
    if errCode:
        raise ADSError(errCode)


@win32_only
def adsSyncWriteReq(adr, indexGroup, indexOffset, value, plcDataType):
    """
    :summary: Send data synchronous to an ADS-device

    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int indexGroup: PLC storage area, according to the INDEXGROUP
        constants
    :param int indexOffset: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int plcDataType: type of the data given to the PLC,
        according to PLCTYPE constants

    """

    adsSyncWriteReqFct = _adsDLL.AdsSyncWriteReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)

    if plcDataType == PLCTYPE_STRING:
        nData = c_char_p(value.encode())
        pData = nData
        nLength = len(pData.value) + 1
    else:
        if type(plcDataType).__name__ == 'PyCArrayType':
            nData = plcDataType(*value)
        else:
            nData = plcDataType(value)
        pData = pointer(nData)
        nLength = sizeof(nData)

    errCode = adsSyncWriteReqFct(pAmsAddr, nIndexGroup, nIndexOffset,
                                 nLength, pData)
    if errCode:
        raise ADSError(errCode)


@win32_only
def adsSyncReadWriteReq(adr, indexGroup, indexOffset, plcReadDataType,
                        value, plcWriteDataType):
    """
    :summary: Read and write data synchronous from/to an ADS-device
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int indexGroup: PLC storage area, according to the INDEXGROUP
        constants
    :param int indexOffset: PLC storage address
    :param int plcDataType: type of the data given to the PLC to respond to,
        according to PLCTYPE constants
    :param value: value to write to the storage address of the PLC
    :param plcWriteDataType: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: PLCTYPE
    :return: value: **value**

    """
    adsSyncReadWriteReqFct = _adsDLL.AdsSyncReadWriteReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)

    readData = plcReadDataType()
    nReadLength = c_ulong(sizeof(readData))

    if plcWriteDataType == PLCTYPE_STRING:
        # as we got the value as unicode string (python 3)
        # we have to convert it to ascii
        ascii_string = value.encode()
        data = c_char_p(ascii_string)
        data_length = len(value) + 1
    else:
        nData = plcWriteDataType(value)
        data = pointer(nData)
        data_length = sizeof(nData)

    err_code = adsSyncReadWriteReqFct(
        pAmsAddr, nIndexGroup, nIndexOffset, nReadLength, pointer(readData),
        data_length, data)

    if err_code:
        raise ADSError(err_code)

    if plcReadDataType == PLCTYPE_STRING:
        return readData.value.decode('utf-8')

    if type(plcReadDataType).__name__ == 'PyCArrayType':
        return [i for i in readData]

    if hasattr(readData, 'value'):
        return readData.value

    return readData


@win32_only
def adsSyncReadReq(adr, indexGroup, indexOffset, plcDataType):
    """
    :summary: Read data synchronous from an ADS-device
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int indexGroup: PLC storage area, according to the INDEXGROUP
        constants
    :param int indexOffset: PLC storage address
    :param int plcDataType: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: PLCTYPE
    :return: value: **value**

    """

    adsSyncReadReqFct = _adsDLL.AdsSyncReadReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)

    if plcDataType == PLCTYPE_STRING:
        data = (STRING_BUFFER * PLCTYPE_STRING)()
    else:
        data = plcDataType()

    pData = pointer(data)
    nLength = c_ulong(sizeof(data))
    errCode = adsSyncReadReqFct(
        pAmsAddr, nIndexGroup, nIndexOffset, nLength, pData)

    if errCode:
        raise ADSError(errCode)

    if plcDataType == PLCTYPE_STRING:
        return data.value.decode('utf-8')

    if type(plcDataType).__name__ == 'PyCArrayType':
        return [i for i in data]

    if hasattr(data, 'value'):
        return data.value

    return data


@win32_only
def adsSyncReadByName(adr, dataName, plcDataType):
    """
    :summary: Read data synchronous from an ADS-device from data name
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param string dataName: data name
    :param int plcDataType: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: PLCTYPE
    :return: value: **value**

    """
    # Get the handle of the PLC-variable
    hnl = adsSyncReadWriteReq(
        adr, ADSIGRP_SYM_HNDBYNAME, 0x0, PLCTYPE_UDINT,
        dataName, PLCTYPE_STRING
    )

    # Read the value of a PLC-variable, via handle
    value = adsSyncReadReq(adr, ADSIGRP_SYM_VALBYHND, hnl, plcDataType)

    # Release the handle of the PLC-variable
    adsSyncWriteReq(adr, ADSIGRP_SYM_RELEASEHND, 0, hnl, PLCTYPE_UDINT)

    return value


@win32_only
def adsSyncWriteByName(adr, dataName, value, plcDataType):
    """
    :summary: Send data synchronous to an ADS-device from data name

    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param string dataName: PLC storage address
    :param value: value to write to the storage address of the PLC
    :param int plcDataType: type of the data given to the PLC,
        according to PLCTYPE constants

    """
    # Get the handle of the PLC-variable
    hnl = adsSyncReadWriteReq(adr, ADSIGRP_SYM_HNDBYNAME, 0x0, PLCTYPE_UDINT,
                              dataName, PLCTYPE_STRING)

    # Write the value of a PLC-variable, via handle
    adsSyncWriteReq(adr, ADSIGRP_SYM_VALBYHND, hnl, value, plcDataType)

    # Release the handle of the PLC-variable
    adsSyncWriteReq(adr, ADSIGRP_SYM_RELEASEHND, 0, hnl, PLCTYPE_UDINT)


NOTEFUNC = None
if platform_is_windows():
    NOTEFUNC = ctypes.WINFUNCTYPE(c_void_p, POINTER(SAmsAddr),
                                  POINTER(SAdsNotificationHeader), c_ulong)

callback_store = dict()


@win32_only
def adsSyncAddDeviceNotificationReq(adr, data_name, pNoteAttrib, callback,
                                    user_handle=None):
    global callback_store   # use global variable to prevent garbage collection
    adsSyncAddDeviceNotificationReqFct = \
        _adsDLL.AdsSyncAddDeviceNotificationReq

    pAmsAddr = ctypes.pointer(adr.amsAddrStruct())
    hnl = adsSyncReadWriteReq(adr, ADSIGRP_SYM_HNDBYNAME, 0x0, PLCTYPE_UDINT,
                              data_name, PLCTYPE_STRING)

    nIndexGroup = ctypes.c_ulong(ADSIGRP_SYM_VALBYHND)
    nIndexOffset = ctypes.c_ulong(hnl)
    attrib = pNoteAttrib.notificationAttribStruct()

    pNotification = ctypes.c_ulong()
    nHUser = ctypes.c_ulong(hnl)
    if user_handle is not None:
        nHUser = ctypes.c_ulong(user_handle)

    if NOTEFUNC is None:
        raise TypeError("Callback function type can't be None")
    adsSyncAddDeviceNotificationReqFct.argtypes = [
        ctypes.POINTER(SAmsAddr),
        ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(SAdsNotificationAttrib),
        NOTEFUNC, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong)
    ]
    adsSyncAddDeviceNotificationReqFct.restype = c_ulong
    c_callback = NOTEFUNC(callback)
    err_code = adsSyncAddDeviceNotificationReqFct(pAmsAddr, nIndexGroup,
                                                  nIndexOffset,
                                                  pointer(attrib),
                                                  c_callback, nHUser,
                                                  pointer(pNotification))

    if err_code:
        raise ADSError(err_code)
    callback_store[pNotification.value] = c_callback
    return (pNotification.value, hnl)


@win32_only
def adsSyncDelDeviceNotificationReq(adr, notification_handle, user_handle):
    adsSyncDelDeviceNotificationReqFct = \
        _adsDLL.AdsSyncDelDeviceNotificationReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nHNotification = c_ulong(notification_handle)
    err_code = adsSyncDelDeviceNotificationReqFct(pAmsAddr, nHNotification)
    callback_store[notification_handle] = None
    if err_code:
        raise ADSError(err_code)

    adsSyncWriteReq(adr, ADSIGRP_SYM_RELEASEHND, 0, user_handle, PLCTYPE_UDINT)


@win32_only
def adsSyncSetTimeout(nMs):
    adsSyncSetTimeoutFct = \
        _adsDLL.AdsSyncSetTimeout
    cms = c_long(nMs)
    err_code = adsSyncSetTimeoutFct(cms)
    if err_code:
        raise ADSError(err_code)
