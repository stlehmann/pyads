"""Structs for the work with ADS API.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT
:created on: 2018-06-11 18:15:53

"""

import ctypes
from ctypes import Structure, c_ubyte, c_uint16, c_uint32, c_uint64
from typing import Union

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

    def __init__(self, stAdsVersion: SAdsVersion) -> None:
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

    def __init__(self, netid: str = None, port: int = None) -> None:
        """Create a new AmsAddr object by a given netid and port.

        :param netid: NetId of an ADS device
        :param port: port of an ADS device

        """
        self._ams_addr = SAmsAddr()

        if netid is not None:
            self.netid = netid
        if port is not None:
            self.port = port

    def toString(self) -> str:
        """Textual representation of the AMS address.

        :rtype: string
        :return:  textual representation of the AMS address
        """
        return self.netid + ": " + str(self._ams_addr.port)

    # property netid
    @property
    def netid(self) -> str:
        """Netid of the AmsAddress.

        The Netid is always returned as a String. If the NetId is set
        it can be passed as a String or as a SAmsNetId struct.

        """
        return ".".join(map(str, self._ams_addr.netId.b))

    @netid.setter
    def netid(self, value: Union[str, SAmsNetId]) -> None:
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
    def port(self) -> int:
        """Port of the AmsAddress object."""
        return self._ams_addr.port

    @port.setter
    def port(self, value: int) -> None:
        self._ams_addr.port = c_uint16(value)

    def amsAddrStruct(self) -> SAmsAddr:
        """Return the c-types structure SAmsAddr."""
        return self._ams_addr

    def netIdStruct(self) -> SAmsNetId:
        """Return the c-types structure SAmsNetId."""
        return self._ams_addr.netId

    def setAdr(self, adrString: str) -> None:
        """Set the AMS-address according to the given IP-address.

        :type adrString: string
        :param adrString: ip-address of an ADS device

        """
        self.netid = adrString

    def __repr__(self) -> str:
        """Return object name."""
        return "<AmsAddress {}:{}>".format(self.netid, self.port)


class NotificationAttrib(object):
    """Notification Attribute."""

    def __init__(
        self, length: int, trans_mode: int = ADSTRANS_SERVERONCHA, max_delay: float = 1e-4, cycle_time: float = 1e-4
    ) -> None:
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

    def notificationAttribStruct(self) -> "SAdsNotificationAttrib":
        """Return the raw struct."""
        return self._attrib

    @property
    def length(self) -> int:
        """Notification data length."""
        return self._attrib.cbLength

    @length.setter
    def length(self, val: int) -> None:
        self._attrib.cbLength = val

    @property
    def trans_mode(self) -> int:
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
    def trans_mode(self, val: int) -> None:
        self._attrib.nTransMode = val

    @property
    def max_delay(self) -> None:
        """Maximum allowed delay between notifications in ms."""
        return self._attrib.nMaxDelay

    @max_delay.setter
    def max_delay(self, val: int) -> None:
        self._attrib.nMaxDelay = val

    @property
    def cycle_time(self) -> int:
        """Notification cycle time in ms for cycle transmission mode."""
        return self._attrib.nCycleTime

    @cycle_time.setter
    def cycle_time(self, val: int) -> None:
        self._attrib.nCycleTime = val
        self._attrib.dwChangeFilter = val

    def __repr__(self) -> str:
        """Return object name."""
        return "<NotificationAttrib {} {} {} {}>".format(
            self.length, self.trans_mode, self.max_delay, self.cycle_time
        )


class _AttribUnion(ctypes.Union):
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


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
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

    A complete example could be:

    .. code:: python

        value: 57172            # Current value
        info.entryLength: 88    # Total storage space for this symbol
        info.iGroup: 16448      # Group index
        info.iOffs: 385000      # Offset index inside group
        info.size: 2            # Number of bytes needed for the value
        info.dataType: 18       # Symbol type, in this case
                                  constants.ADST_UINT16 (18)
        info.flags: 8           # TwinCAT byte flags
        info.nameLength: 11     # Number of characters in the name
        info.typeLength: 4      # Number of characters in the PLC string
                                  representation of the type
        info.commentLength: 20  # Number of characters in the comment
        info.stringBuffer: <pyads.structs.c_ubyte_Array_768 object>
                                # Concatenation of all string info
        bytes(info.stringBuffer): b'GVL.counter\x00UINT\x00 Counter (in '
                                  'pulses)\x00\x95\x19\x07\x18\x00\x00\x00\x00'
        bytes(info.stringBuffer).encode(): "GVL.counter UINT Counter (in
                                            pulses)"

        info.name: "GVL.counter"    # The name section from the buffer
        info.symbol_type: "UINT"    # The symbol_type section from the
                                      buffer
        info.comment: " Counter (in pulses)"  # The comment (if any)
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
        # 3 strings contained, with max length 256 each
    ]

    def _get_string(self, offset: int, length: int) -> str:
        """Get portion of the bigger string buffer"""
        return bytes(self.stringBuffer[offset:(offset + length)]) \
            .decode("utf-8")

    @property
    def name(self) -> str:
        """The symbol name."""
        return self._get_string(0, self.nameLength)

    @property
    def symbol_type(self) -> str:
        """The qualified type name, including the namespace."""
        return self._get_string(self.nameLength + 1, self.typeLength)

    @property
    def comment(self) -> str:
        """User-defined comment."""
        return self._get_string(
            self.nameLength + self.typeLength + 2, self.commentLength
        )


class SAdsSumRequest(Structure):
    """ADS sum request structure.

    :ivar iGroup: indexGroup of request
    :ivar iOffs: indexOffset of request
    :ivar size: size of request
    """

    _pack_ = 1
    _fields_ = [("iGroup", c_uint32), ("iOffset", c_uint32), ("size", c_uint32)]
