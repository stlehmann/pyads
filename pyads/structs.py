"""
    pyads.structs
    -------------

    Structs for the work with ADS API.

    :copyright: 2013 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""
from ctypes import *


class SAdsVersion(Structure):

    _fields_ = [
        ("version", c_byte),
        ("revision", c_byte),
        ("build", c_short)
    ]


class AdsVersion ():

    """
    :summary: contains version number, revision number,
              build number of the ADS-DLL

    :ivar int version: version number
    :ivar int revision: revision number
    :ivar int build: build number

    """

    def __init__(self, stAdsVersion):
        """
        :param pyads.constants.SAdsVersion stAdsVersion: ctypes structure
            with the version info

        """
        self.version = stAdsVersion.version
        self.revision = stAdsVersion.revision
        self.build = stAdsVersion.build


class SAmsAddr(Structure):

    """
    :summary: structure containing the netId and port of an ADS device

    """
    _pack_ = 1
    _fields_ = [("netId", c_ubyte * 6),
                ("port", c_ushort)]


class AmsAddr():

    """
    :summary: wrapper for SAmsAddr-structure to adress an ADS device

    :type stAmsAddr: SAmsAddr
    :ivar stAmsAddr: ctypes-structure SAmsAddr

    :type errCode: int
    :ivar errCode: error code

    """

    def __init__(self, errCode, stAmsAddr):
        self.stAmsAddr = stAmsAddr
        self.errCode = errCode

    def toString(self):
        """
        :summary: textual representation of the AMS adress
        :rtype: string
        :return:  textual representation of the AMS adress
        """
        tmpList = [
            str(self.stAmsAddr.netId[i])
            for i in range(sizeof(self.stAmsAddr.netId))
        ]
        netId = ".".join(tmpList) + ": " + str(self.stAmsAddr.port)
        return netId

    def port(self):
        """
        :summary: returns port number
        """
        return int(self.stAmsAddr.port)

    def setPort(self, value):
        """
        :summary: sets port number
        """
        self.stAmsAddr.port = c_ushort(value)

    def amsAddrStruct(self):
        """
        :summary: access to the c-types structure SAmsAddr
        """
        return self.stAmsAddr

    def setAdr(self, adrString):
        """
        :summary: Sets the AMS-adress according to the given string
                  containing the IP-adress

        :type adrString: string
        :param adrString: ip-adress of an ADS device

        """
        a = adrString.split(".")

        if not len(a) == 6:
            return

        for i in range(len(a)):
            self.stAmsAddr.netId[i] = c_ubyte(int(a[i]))


class SAdsNotificationAttrib(Structure):
    _pack_ = 1
    _fields_ = [("cbLength", c_ulong),
                ("nTransMode", c_ulong),
                ("nMaxDelay", c_ulong),
                ("nCycleTime", c_ulong)]


class SAdsSymbolUploadInfo(Structure):

    _pack_ = 1
    _fields_ = [("nSymbols", c_ulong),
                ("nSymSize", c_ulong)]


class SAdsSymbolEntry(Structure):

    """
    ADS symbol information

    :ivar entryLength: length of complete symbol entry
    :ivar iGroup: indexGroup of symbol: input, output etc.
    :ivar iOffs: indexOffset of symbol
    :ivar size: size of symbol (in bytes, 0=bit)
    :ivar dataType: adsDataType of symbol
    :ivar flags: symbol flags
    :ivar nameLength: length of symbol name
    :ivar typeLength: length of type name
    :ivar commentLength: length of comment

    """
    _pack_ = 1
    _fields_ = [("entryLength", c_ulong),
                ("iGroup", c_ulong),
                ("iOffs", c_ulong),
                ("size", c_ulong),
                ("dataType", c_ulong),
                ("flags", c_ulong),
                ("nameLength", c_ushort),
                ("typeLength", c_ushort),
                ("commentLength", c_ushort)]
