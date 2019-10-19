"""Structs for the work with ADS API.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:53
:last modified by: Stefan Lehmann
:last modified time: 2018-07-12 14:33:11

"""
import typing
from ctypes import c_byte, Structure, c_ubyte, Union, c_uint16, c_uint32, c_uint64
from .constants import ADSTRANS_SERVERONCHA


class SAdsVersion(Structure):
    """Struct containing ADS version information."""

    _fields_ = [("version", c_ubyte), ("revision", c_ubyte), ("build", c_uint16)]


class AdsVersion:
    """Contains version number, revision number, build number of the ADS-DLL.

    :ivar int version: version number
    :ivar int revision: revision number
    :ivar int build: build number

    """

    def __init__(self, stAdsVersion):
        # type: (SAdsVersion) -> None
        """Create new AdsVersion object.

        :param pyads.constants.SAdsVersion stAdsVersion: ctypes structure
            with the version info

        """
        self.version = stAdsVersion.version
        self.revision = stAdsVersion.revision
        self.build = stAdsVersion.build


class SAmsNetId(Structure):
    """Struct with array of 6 bytes used to describe a net id."""

    _pack_ = 1
    _fields_ = [("b", c_ubyte * 6)]


class SAmsAddr(Structure):
    """Struct containing the netId and port of an ADS device."""

    _pack_ = 1
    _fields_ = [("netId", SAmsNetId), ("port", c_uint16)]


class AmsAddr(object):
    """Wrapper for SAmsAddr-structure to address an ADS device.

    :type _ams_addr: SAmsAddr
    :ivar _ams_addr: ctypes-structure SAmsAddr

    """

    def __init__(self, netid=None, port=None):
        # type: (str, int) -> None
        """Create a new AmsAddr object by a given netid and port.

        :param netid: NetId of an ADS device
        :param port: port of an ADS device

        """
        self._ams_addr = SAmsAddr()

        if netid is not None:
            self.netid = netid
        if port is not None:
            self.port = port

    def toString(self):
        # type: () -> str
        """Textual representation of the AMS address.

        :rtype: string
        :return:  textual representation of the AMS address
        """
        return self.netid + ": " + str(self._ams_addr.port)

    # property netid
    @property
    def netid(self):
        # type: () -> str
        """Netid of the AmsAddress.

        The Netid is always returned as a String. If the NetId is set
        it can be passed as a String or as a SAmsNetId struct.

        """
        return ".".join(map(str, self._ams_addr.netId.b))

    @netid.setter
    def netid(self, value):
        # type: (typing.Union[str, SAmsNetId]) -> None
        # Check if the value is already an instance of the SAmsNetId struct
        if isinstance(value, SAmsNetId):
            self._ams_addr.netId = value

        # Otherwise, attempt to parse the id as a string
        else:
            id_numbers = list(map(int, value.split(".")))

            if len(id_numbers) != 6:
                raise ValueError("no valid netid")

            # Fill the netId struct with data
            self._ams_addr.netId.b = (c_ubyte * 6)(*id_numbers)

    # property port
    @property
    def port(self):
        # type: () -> int
        """Port of the AmsAddress object."""
        return self._ams_addr.port

    @port.setter
    def port(self, value):
        # type: (int) -> None
        self._ams_addr.port = c_uint16(value)

    def amsAddrStruct(self):
        # type: () -> SAmsAddr
        """Return the c-types structure SAmsAddr."""
        return self._ams_addr

    def netIdStruct(self):
        # type: () -> SAmsNetId
        """Return the c-types structure SAmsNetId."""
        return self._ams_addr.netId

    def setAdr(self, adrString):
        # type: (str) -> None
        """Set the AMS-address according to the given IP-address.

        :type adrString: string
        :param adrString: ip-address of an ADS device

        """
        self.netid = adrString

    def __repr__(self):
        # type: () -> str
        """Return object name."""
        return "<AmsAddress {}:{}>".format(self.netid, self.port)


class NotificationAttrib(object):
    """Notification Attribute."""

    def __init__(
        self, length, trans_mode=ADSTRANS_SERVERONCHA, max_delay=1e-4, cycle_time=1e-4
    ):
        # type: (int, int, float, float) -> None
        """Create a new NotificationAttrib object.

        :param int length: length of the data
        :param int trans_mode: transmission mode
        :param float max_delay: maximum delay in ms
        :param float cycle_time: cycle time in ms

        """
        self._attrib = SAdsNotificationAttrib()
        if length:
            self._attrib.cbLength = length
        if trans_mode:
            self._attrib.nTransMode = trans_mode
        if max_delay:
            self._attrib.nMaxDelay = int(max_delay * 1e4)
        if cycle_time:
            self._attrib.nCycleTime = int(cycle_time * 1e4)

    def notificationAttribStruct(self):
        # type: () -> SAdsNotificationAttrib
        """Return the raw struct."""
        return self._attrib

    @property
    def length(self):
        # type: () -> int
        """Notification data length."""
        return self._attrib.cbLength

    @length.setter
    def length(self, val):
        # type: (int) -> None
        self._attrib.cbLength = val

    @property
    def trans_mode(self):
        # type: () -> int
        """Mode of transmission.

        This can be one of the following:

        * ADSTRANS_NOTRANS
        * ADSTRANS_CLIENTCYCLE
        * ADSTRANS_CLIENT1REQ
        * ADSTRANS_SERVERCYCLE
        * ADSTRANS_SERVERONCHA

        """
        return self._attrib.nTransMode

    @trans_mode.setter
    def trans_mode(self, val):
        # type: (int) -> None
        self._attrib.nTransMode = val

    @property
    def max_delay(self):
        # type: () -> int
        """Maximum allowed delay between notifications in ms."""
        return self._attrib.nMaxDelay

    @max_delay.setter
    def max_delay(self, val):
        # type: (int) -> None
        self._attrib.nMaxDelay = val

    @property
    def cycle_time(self):
        # type: () -> int
        """Notification cycle time in ms for cycle transmission mode."""
        return self._attrib.nCycleTime

    @cycle_time.setter
    def cycle_time(self, val):
        # type: (int) -> None
        self._attrib.nCycleTime = val
        self._attrib.dwChangeFilter = val

    def __repr__(self):
        # type: () -> str
        """Return object name."""
        return "<NotificationAttrib {} {} {} {}>".format(
            self.length, self.trans_mode, self.max_delay, self.cycle_time
        )


class _AttribUnion(Union):
    _fields_ = [("nCycleTime", c_uint32), ("dwChangeFilter", c_uint32)]


class SAdsNotificationAttrib(Structure):
    """C structure representation of AdsNotificationAttrib."""

    _pack_ = 1
    _anonymous_ = ("AttribUnion",)
    _fields_ = [
        ("cbLength", c_uint32),
        ("nTransMode", c_uint32),
        ("nMaxDelay", c_uint32),
        ("AttribUnion", _AttribUnion),
    ]


class SAdsNotificationHeader(Structure):
    """C structure representation of AdsNotificationHeader.

    :ivar hNotification: notification handle
    :ivar nTimeStamp: time stamp in FILETIME format
    :ivar cbSampleSize: number of data bytes
    :ivar data: variable-length data field, get via ctypes.addressof + offset

    """

    _pack_ = 1
    _fields_ = [
        ("hNotification", c_uint32),
        ("nTimeStamp", c_uint64),
        ("cbSampleSize", c_uint32),
        ("data", c_ubyte),
    ]


class SAdsSymbolUploadInfo(Structure):
    """C structure representation of AdsSymbolUploadInfo."""

    _pack_ = 1
    _fields_ = [("nSymbols", c_uint32), ("nSymSize", c_uint32)]


class SAdsSymbolEntry(Structure):
    """ADS symbol information.

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
    _fields_ = [
        ("entryLength", c_uint32),
        ("iGroup", c_uint32),
        ("iOffs", c_uint32),
        ("size", c_uint32),
        ("dataType", c_uint32),
        ("flags", c_uint32),
        ("nameLength", c_uint16),
        ("typeLength", c_uint16),
        ("commentLength", c_uint16),
        ("stringBuffer", c_ubyte * (256 * 3)),
        # 3 strings contained, with max length 256
    ]
