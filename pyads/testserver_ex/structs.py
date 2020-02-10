import struct
from ..structs import SAmsNetId
from ..filetimes import filetime_to_dt, dt_to_filetime


class AmsTcpHeader:
    """ First layer of a ADS packet. """

    def __init__(self, length=0):
        self.length = length

    @staticmethod
    def from_bytes(data):
        assert isinstance(data, (bytes, bytearray))
        assert len(data) == 6

        return AmsTcpHeader(struct.unpack("<I", data[2:6])[0])

    def to_bytes(self):
        return b"\x00" * 2 + struct.pack("<I", self.length)


class AmsHeader:
    """ Second layer of an ADS packet. """

    def __init__(
        self,
        target_net_id,
        target_port,
        source_net_id,
        source_port,
        command_id,
        state_flags,
        data_length,
        error_code,
        invoke_id,
    ):

        self.target_net_id = target_net_id
        self.target_port = target_port
        self.source_net_id = source_net_id
        self.source_port = source_port
        self.command_id = command_id
        self.state_flags = state_flags
        self.data_length = data_length
        self.error_code = error_code
        self.invoke_id = invoke_id

    @staticmethod
    def from_bytes(data):
        return AmsHeader(
            target_net_id=SAmsNetId.from_buffer(bytearray(data[0:6])),
            target_port=struct.unpack("<H", data[6:8])[0],
            source_net_id=SAmsNetId.from_buffer(bytearray(data[8:14])),
            source_port=struct.unpack("<H", data[14:16])[0],
            command_id=struct.unpack("<H", data[16:18])[0],
            state_flags=struct.unpack("<H", data[18:20])[0],
            data_length=struct.unpack("<I", data[20:24])[0],
            error_code=struct.unpack("<I", data[24:28])[0],
            invoke_id=struct.unpack("<I", data[28:32])[0],
        )

    def to_bytes(self):
        return (
            bytearray(self.target_net_id)
            + struct.pack("<H", self.target_port)
            + bytearray(self.source_net_id.b)
            + struct.pack("<H", self.source_port)
            + struct.pack("<H", self.command_id)
            + struct.pack("<H", self.state_flags)
            + struct.pack("<I", self.data_length)
            + struct.pack("<I", self.error_code)
            + struct.pack("<I", self.invoke_id)
        )

    @property
    def length(self):
        return len(self.to_bytes())


class AmsPacket:
    def __init__(self, amstcp_header, ams_header, ads_data):

        self.amstcp_header = amstcp_header
        self.ams_header = ams_header
        self.ads_data = ads_data

    @staticmethod
    def from_bytes(data):
        return AmsPacket(
            AmsTcpHeader.from_bytes(data[:6]), AmsHeader.from_bytes(data[6:]), data[38:]
        )

    def to_bytes(self):
        return (
            self.amstcp_header.to_bytes() + self.ams_header.to_bytes() + self.ads_data
        )


class AdsNotificationStream:
    def __init__(self, stamps):

        self.stamps = stamps

    def to_bytes(self):
        return (
            struct.pack("<I", self.data_size)
            + struct.pack("<I", len(self.stamps))
            + b"".join([stamp.to_bytes() for stamp in self.stamps])
        )

    @property
    def data_size(self):
        return sum([stamp.length for stamp in self.stamps])

    @property
    def length(self):
        return len(self.to_bytes())


class AdsStampHeader:
    def __init__(self, timestamp, samples):

        self.timestamp = timestamp
        self.samples = samples

    def to_bytes(self):
        return (
            struct.pack("<Q", self.timestamp)
            + struct.pack("<I", self.sample_count)
            + b"".join([sample.to_bytes() for sample in self.samples])
        )

    @property
    def sample_count(self):
        return len(self.samples)

    @property
    def length(self):
        return len(self.to_bytes())


class AdsNotificationSample:
    def __init__(self, handle, sample_size, data):

        self.handle = handle
        self.sample_size = sample_size
        self.data = data

    def to_bytes(self):
        return (
            struct.pack("<I", self.handle)
            + struct.pack("<I", self.sample_size)
            + self.data
        )

    @property
    def length(self):
        return len(self.to_bytes())
