"""
    pyads.structs
    -------------

    Structs for the work with ADS API.

    :copyright: 2013 by Stefan Lehmann
    :license: MIT, see LICENSE for details

"""
from ctypes import c_byte, c_short, Structure, c_ubyte, c_ushort, c_ulong, \
    c_ulonglong, POINTER, Union, c_uint32, c_uint64
from .constants import ADSTRANS_SERVERONCHA


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


class NotificationAttrib(object):
    def __init__(self, length, trans_mode=ADSTRANS_SERVERONCHA,
                 max_delay=100, cycle_time=100):
        self._attrib = SAdsNotificationAttrib()
        if length:
            self._attrib.cbLength = length
        if trans_mode:
            self._attrib.nTransMode = trans_mode
        if max_delay:
            self._attrib.nMaxDelay = max_delay
        if cycle_time:
            self._attrib.nCycleTime = cycle_time

    def notificationAttribStruct(self):
        return self._attrib

    @property
    def length(self):
        return self._attrib.cbLength

    @length.setter
    def length(self, val):
        self._attrib.cbLength = val

    @property
    def trans_mode(self):
        return self._attrib.nTransMode

    @trans_mode.setter
    def trans_mode(self, val):
        self._attrib.nTransMode = val

    @property
    def max_delay(self):
        return self._attrib.nMaxDelay

    @max_delay.setter
    def max_delay(self, val):
        self._attrib.nMaxDelay = val

    @property
    def cycle_time(self):
        return self._attrib.nCycleTime

    @cycle_time.setter
    def cycle_time(self, val):
        self._attrib.nCycleTime = val
        self._attrib.dwChangeFilter = val

    def __repr__(self):
        return ('<NotificationAttrib {} {} {} {}>'
                .format(self.length, self.trans_mode, self.max_delay,
                        self.cycle_time))


class _AttribUnion(Union):
    _fields_ = [("nCycleTime", c_uint32), ("dwChangeFilter", c_uint32)]


class SAdsNotificationAttrib(Structure):
    _pack_ = 1
    _anonymous_ = ("AttribUnion",)
    _fields_ = [("cbLength", c_uint32),
                ("nTransMode", c_uint32),
                ("nMaxDelay", c_uint32),
                ("AttribUnion", _AttribUnion), ]


class SAdsNotificationHeader(Structure):
    _pack_ = 1
    _fields_ = [("hNotification", c_uint32),
                ("nTimeStamp", c_uint64),
                ("cbSampleSize", c_uint32),
                ("data", POINTER(c_ubyte))]


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
