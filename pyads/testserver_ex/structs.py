import struct
from collections import namedtuple


_AmsTcpHeader = namedtuple('AmsTcpHeader', 'length')

_AmsHeader = namedtuple(
    'AmsHeader', (
        'target_net_id', 'target_port', 'source_net_id', 'source_port',
        'command_id', 'state_flags', 'length', 'error_code', 'invoke_id',
        'data'
    )
)


class AmsTcpHeader:
    """ First layer of a ADS packet. """

    def __init__(self, data=None, length=None):
        if data is not None:
            assert isinstance(data, (bytes, bytearray))
            assert len(data) == 6

        if data is None:
            self.data = b'\x00' * 6
        else:
            self.data = data

        if length is not None:
            self.length = length

    @property
    def length(self):
        return struct.unpack('<I', self.data[2:6])[0]

    @length.setter
    def length(self, value):
        assert isinstance(value, int)
        self.data = self.data[0:2] + struct.pack('<I', value)


class AmsHeader(_AmsHeader):
    """ Second layer of an ADS packet. """

    def __init__(self, data=None):

        if data is None:
            self.data = b'\x00' * 

    @staticmethod
    def from_bytes(data):
        ams_header = AmsHeader(
            # Extract target/source net ID's and ports
            data[0:6], data[6:8], data[8:14], data[14:16],
            # Extract command ID, state flags, and data length
            data[16:18], data[18:20], data[20:24],
            # Extract error code, invoke ID, and data
            data[24:28], data[28:32], data[32:]
        )
