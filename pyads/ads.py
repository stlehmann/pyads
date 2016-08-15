from ctypes import windll, c_ubyte, c_long, c_ushort, pointer
from .structs import SAmsAddr
from .errorcodes import ERROR_CODES


_adsDLL = windll.TcAdsDll  #: ADS-DLL (Beckhoff TwinCAT)


class ADSError(Exception):
    def __init__(self, err_code):
        self.err_code = err_code
        self.msg = "{} ({})".format(ERROR_CODES[self.err_code], self.err_code)

    def __str__(self):
        return "ADSError: " + self.msg


class AmsAddr:
    def __init__(self, netid=None, port=None):
        self._ams_addr = SAmsAddr()
        if netid is not None:
            self.netid = netid
        if port is not None:
            self.port = port

    # property netid
    @property
    def netid(self):
        return '.'.join(map(str, self._ams_addr.netId))

    @netid.setter
    def netid(self, value):
        id_numbers = list(map(int, value.split('.')))
        if len(id_numbers) != 6:
            raise ValueError('no valid netid')

        for i, nr in enumerate(id_numbers):
            self._ams_addr.netId[i] = c_ubyte(nr)

    # property port
    @property
    def port(self):
        return self._ams_addr.port

    @port.setter
    def port(self, value: int):
        self._ams_addr.port = c_ushort(value)

    def amsAddrStruct(self):
        """
        :summary: access to the c-types structure SAmsAddr
        """
        return self._ams_addr

    def __repr__(self):
        return '<AmsAddress {}:{}>'.format(self.netid, self.port)


def open_port():
    f = _adsDLL.AdsPortOpen
    f.restype = c_long
    port = f()
    return port


def close_port():
    f = _adsDLL.AdsPortClose
    f.restype = c_long
    err_code = f()

    if err_code:
        raise ADSError(err_code)


def get_local_address():
    f = _adsDLL.AdsGetLocalAddress
    st_ams_addr = SAmsAddr()
    err_code = f(pointer(st_ams_addr))

    if err_code:
        raise ADSError(err_code)

    ams_addr = AmsAddr()
    ams_addr._ams_addr = st_ams_addr
    return ams_addr
