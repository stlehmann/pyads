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


class AdsVersion():

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


class SAmsNetId(Structure):
    """
    :summary: structure with array of 6 bytes used to describe a net id
    """
    _pack_ = 1
    _fields_ = [("b", c_ubyte * 6)]


class SAmsAddr(Structure):

    """
    :summary: structure containing the netId and port of an ADS device

    """
    _pack_ = 1
    _fields_ = [("netId", SAmsNetId),
                ("port", c_ushort)]


class AmsAddr(object):

    """
    :summary: wrapper for SAmsAddr-structure to adress an ADS device

    :type _ams_addr: SAmsAddr
    :ivar _ams_addr: ctypes-structure SAmsAddr

    """

    def __init__(self, netid=None, port=None):
        self._ams_addr = SAmsAddr()

        if netid is not None:
            self.netid = netid
        if port is not None:
            self.port = port

    def toString(self):
        """
        :summary: textual representation of the AMS adress
        :rtype: string
        :return:  textual representation of the AMS adress
        """
        return self.netid + ": " + str(self._ams_addr.port)

    # property netid
    @property
    def netid(self):
        return '.'.join(map(str, self._ams_addr.netId.b))

    @netid.setter
    def netid(self, value):
        # Check if the value is already an instance of the SAmsNetId struct
        if isinstance(value, SAmsNetId):
            self._ams_addr.netId = value

        # Otherwise, attempt to parse the id as a string
        else:
            id_numbers = list(map(int, value.split('.')))

            if len(id_numbers) != 6:
                raise ValueError('no valid netid')

            # Fill the netId struct with data
            self._ams_addr.netId.b = (c_ubyte * 6)(*id_numbers)

    # property port
    @property
    def port(self):
        return self._ams_addr.port

    @port.setter
    def port(self, value):
        self._ams_addr.port = c_ushort(value)

    def amsAddrStruct(self):
        """
        :summary: access to the c-types structure SAmsAddr
        """
        return self._ams_addr

    def netIdStruct(self):
        """
        :summary: access to the c-types structure SAmsNetId
        """
        return self._ams_addr.netId

    def setAdr(self, adrString):
        """
        :summary: Sets the AMS-adress according to the given string
                  containing the IP-address

        :type adrString: string
        :param adrString: ip-address of an ADS device

        """
        self.netid = adrString

    def __repr__(self):
        return '<AmsAddress {}:{}>'.format(self.netid, self.port)


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
