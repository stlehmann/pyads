# -*- coding: utf-8 -*-
"""
    pyads.pyads
    ~~~~~~~~~~~

    Contains ADS functions.

    :copyright: (c) 2013 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""

from ctypes import *

from constants import *
from structs import *


# load dynamic ADS library
_adsDLL = CDLL("TcAdsDll.dll") #: ADS-DLL (Beckhoff TwinCAT)


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

def adsPortClose():
    """
    :summary: Close the connection to the TwinCAT message router.
    :rtype: int
    :return: error state

    """
    adsPortCloseFct = _adsDLL.AdsPortClose
    adsPortCloseFct.restype = c_long
    errCode = adsPortCloseFct()
    return errCode

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
        return None

    adsLocalAddr = AmsAddr(errCode, stAmsAddr)
    return adsLocalAddr

def adsSyncReadStateReq(adr):
    """
    :summary: Read the current ADS-state and the machine-state from the
        ADS-server
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :rtype: (int, int, int)
    :return: errCode, adsState, deviceState

    """
    adsSyncReadStateReqFct = _adsDLL.AdsSyncReadStateReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    adsState = c_int()
    pAdsState = pointer(adsState)
    deviceState = c_int()
    pDeviceState = pointer(deviceState)

    errCode = adsSyncReadStateReqFct(pAmsAddr, pAdsState, pDeviceState)
    return (errCode, adsState.value, deviceState.value)

def adsSyncReadDeviceInfoReq(adr):
    """
    :summary: Read the name and the version number of the ADS-server
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :rtype: int, string, AdsVersion
    :return: errCode, device name, version

    """
    adsSyncReadDeviceInfoReqFct = _adsDLL.AdsSyncReadDeviceInfoReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    devNameStringBuffer = create_string_buffer(20)
    pDevName = pointer(devNameStringBuffer)
    stVersion = SAdsVersion()
    pVersion = pointer(stVersion)

    errCode = adsSyncReadDeviceInfoReqFct(pAmsAddr, pDevName, pVersion)
    return (errCode, devNameStringBuffer.value, AdsVersion(stVersion))

def adsSyncWriteControlReq(adr, adsState, deviceState, data, plcDataType):
    """
    :summary: Change the ADS state and the machine-state of the ADS-server

    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int adsState: new ADS-state, according to ADSTATE constants
    :param int deviceState: new machine-state
    :param data: additional data
    :param int plcDataType: plc datatype, according to PLCTYPE constants
    :rtype: int
    :return: error-state of the function

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
        nData = c_char_p(data)
        pData = nData
        nLength = len(pData.value)+1
    else:
        nData = plcDataType(data)
        pData = pointer(nData)
        nLength = sizeof(nData)

    errCode = adsSyncWriteControlReqFct(pAddr, nAdsState, nDeviceState,
                                        nLength, pData)
    return errCode

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
    :rtype: int
    :return: error-state of the function

    """

    adsSyncWriteReqFct = _adsDLL.AdsSyncWriteReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)

    if plcDataType == PLCTYPE_STRING:
        nData = c_char_p(value)
        pData = nData
        nLength = len(pData.value)+1
    else:
        if type(plcDataType).__name__ == 'PyCArrayType':
            nData = plcDataType(*value)
        else:
            nData = plcDataType(value)
        pData = pointer(nData)
        nLength = sizeof(nData)


    errCode = adsSyncWriteReqFct(pAmsAddr, nIndexGroup, nIndexOffset,
                                 nLength, pData)
    return errCode

def adsSyncReadWriteReq(adr, indexGroup, indexOffset,  plcReadDataType,
                        value, plcWriteDataType):
    """
    :summary: Read ands write data synchronous from/to an ADS-device
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int indexGroup: PLC storage area, according to the INDEXGROUP
        constants
    :param int indexOffset: PLC storage address
    :param int plcDataType: type of the data given to the PLC to respond to,
        according to PLCTYPE constants
    :param value: value to write to the storage address of the PLC
    :param plcWriteDataType: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: (int, PLCTYPE)
    :return: (err_code, value): **err_code** error-state of the function,
        **value**

    """
    adsSyncReadWriteReqFct = _adsDLL.AdsSyncReadWriteReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)

    readData = plcReadDataType()
    nReadLength = c_ulong(sizeof(readData))

    if plcWriteDataType == PLCTYPE_STRING:
        ## as we got the value as unicode string (python 3) we have to convert it to ascii
        ascii_string = value.encode()
        data = c_char_p(ascii_string)
        data_length = len(value) + 1
    else:
        nData = plcWriteDataType(value)
        data = pointer(nData)
        data_length = sizeof(nData)

    err_code = adsSyncReadWriteReqFct(pAmsAddr, nIndexGroup, nIndexOffset, nReadLength,
                                     pointer(readData), data_length, data)
    return err_code, readData.value

def adsSyncReadReq(adr, indexGroup, indexOffset, plcDataType):
    """
    :summary: Read data synchronous from an ADS-device
    :param pyads.structs.AmsAddr adr: local or remote AmsAddr
    :param int indexGroup: PLC storage area, according to the INDEXGROUP
        constants
    :param int indexOffset: PLC storage address
    :param int plcDataType: type of the data given to the PLC, according to
        PLCTYPE constants
    :rtype: (int, PLCTYPE)
    :return: (errCode, value): **errCode** error-state of the function,
        **value**

    """

    adsSyncReadReqFct = _adsDLL.AdsSyncReadReq

    pAmsAddr = pointer(adr.amsAddrStruct())
    nIndexGroup = c_ulong(indexGroup)
    nIndexOffset = c_ulong(indexOffset)

    data = plcDataType()
    pData = pointer(data)
    nLength = c_ulong(sizeof(data))
    errCode = adsSyncReadReqFct(pAmsAddr, nIndexGroup, nIndexOffset, nLength, pData)

    if hasattr(data,'value'):
        return (errCode, data.value)
    else:
        if type(plcDataType).__name__ == 'PyCArrayType':
            dout = [i for i in data]
            return (errCode, data)
        else:
        ## if we return structures, they may not have a value attribute
            return (errCode, data)
