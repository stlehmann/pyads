import ctypes
import struct
import unittest
import datetime
import pyads
from pyads.testserver_ex import structs
from pyads.structs import AmsAddr
from pyads.filetimes import dt_to_filetime, filetime_to_dt


class TestserverExStructsTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_amstcpheader(self):

        # test for empty data
        x = structs.AmsTcpHeader()
        self.assertEqual(b'\x00' * 6, x.to_bytes())
        self.assertEqual(0, x.length)

        # check for correct unpacking
        x = structs.AmsTcpHeader.from_bytes(b'\x00\x00\x1f\x00\x00\x00')

        # check for correct packing
        x.length = 255
        self.assertEqual(b'\x00\x00\xff\x00\x00\x00', x.to_bytes())

    def test_amsheader(self):
        source_addr = AmsAddr('127.0.0.1.1.1', 59558)
        target_addr = AmsAddr('172.38.1.1.1.1', 59559)

        header1 = structs.AmsHeader(
            target_net_id=target_addr.netIdStruct(),
            target_port=target_addr.port,
            source_net_id=source_addr.netIdStruct(),
            source_port=source_addr.port,
            command_id=pyads.constants.ADSCOMMAND_READDEVICEINFO,
            state_flags=pyads.constants.ADSSTATEFLAG_COMMAND,
            data_length=6,
            error_code=1,
            invoke_id=2,
        )

        data_bytes = header1.to_bytes()
        self.assertEqual(len(data_bytes), header1.length)
        header2 = structs.AmsHeader.from_bytes(data_bytes)

        self.assertEqual(bytearray(header1.target_net_id.b),
                         bytearray(header2.target_net_id.b))
        self.assertEqual(header1.target_port, header2.target_port)
        self.assertEqual(bytearray(header1.source_net_id),
                         bytearray(header2.source_net_id))
        self.assertEqual(header1.source_port, header2.source_port)
        self.assertEqual(header1.command_id, header2.command_id)
        self.assertEqual(header1.state_flags, header2.state_flags)
        self.assertEqual(header1.data_length, header2.data_length)
        self.assertEqual(header1.error_code, header2.error_code)
        self.assertEqual(header1.invoke_id, header2.invoke_id)

    def test_ams_packet(self):
        source_addr = AmsAddr('127.0.0.1.1.1', 59558)
        target_addr = AmsAddr('172.38.1.1.1.1', 59559)

        header1 = structs.AmsHeader(
            target_net_id=target_addr.netIdStruct(),
            target_port=target_addr.port,
            source_net_id=source_addr.netIdStruct(),
            source_port=source_addr.port,
            command_id=pyads.constants.ADSCOMMAND_READDEVICEINFO,
            state_flags=pyads.constants.ADSSTATEFLAG_COMMAND,
            data_length=6,
            error_code=1,
            invoke_id=2,
        )
        ads_data = b'\x00' * 6
        amstcpheader = structs.AmsTcpHeader(header1.length + len(ads_data))
        packet = structs.AmsPacket(amstcpheader, header1, ads_data)

        # first six bytes should be amstcpheader
        self.assertEqual(packet.to_bytes()[:6], amstcpheader.to_bytes())

        # next 32 bytes should be ams header
        self.assertEqual(packet.to_bytes()[6:38], header1.to_bytes())

        # last bytes should be data
        self.assertEqual(packet.to_bytes()[38:44], ads_data)

        # check from bytes function
        self.assertEqual(
            structs.AmsPacket.from_bytes(packet.to_bytes()).to_bytes(),
            packet.to_bytes()
        )

    def test_ads_notification_sample(self):
        sample = structs.AdsNotificationSample(
            handle=1,
            sample_size=ctypes.sizeof(pyads.PLCTYPE_INT),
            data=struct.pack('<H', 12)
        )

        self.assertEqual(
            b'\x01\x00\x00\x00'  # handle
            b'\x02\x00\x00\x00'  # sample_size
            b'\x0C\x00',         # data
            sample.to_bytes()
        )

        self.assertEqual(sample.length, 10)

    def test_ads_stamp_header(self):
        dt = datetime.datetime(2017, 9, 1, 10, 10, 10)
        filetime = dt_to_filetime(dt)
        stamp_header = structs.AdsStampHeader(
            timestamp=filetime,
            samples=[structs.AdsNotificationSample(
                handle=1,
                sample_size=ctypes.sizeof(pyads.PLCTYPE_INT),
                data=struct.pack('<H', 12)
            )]
        )

        self.assertEqual(
            b'\x00\xadT~\n#\xd3\x01'    # timestamp
            b'\x01\x00\x00\x00'         # sample count
            b'\x01\x00\x00\x00'         # sample handle
            b'\x02\x00\x00\x00'         # sample sample_size
            b'\x0C\x00',                # sample data
            stamp_header.to_bytes()
        )

        self.assertEqual(stamp_header.length, 22)

    def test_ads_notification_stream(self):
        dt = datetime.datetime(2017, 9, 1, 10, 10, 10)
        filetime = dt_to_filetime(dt)

        stream = structs.AdsNotificationStream([
            structs.AdsStampHeader(
                timestamp=filetime,
                samples=[structs.AdsNotificationSample(
                    handle=1,
                    sample_size=ctypes.sizeof(pyads.PLCTYPE_INT),
                    data=struct.pack('<H', 12)
                )]
            )
        ])

        self.assertEqual(
            b'\x16\x00\x00\x00'         # length
            b'\x01\x00\x00\x00'         # stamp count
            b'\x00\xadT~\n#\xd3\x01'      # stamp timestamp
            b'\x01\x00\x00\x00'           # stamp sample count
            b'\x01\x00\x00\x00'             # sample handle
            b'\x02\x00\x00\x00'             # sample sample_size
            b'\x0C\x00',                    # sample data
            stream.to_bytes()
        )

        self.assertEqual(stream.length, 30)


if __name__ == '__main__':
    unittest.main()
