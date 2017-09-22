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
            length=6,
            error_code=1,
            invoke_id=2,
        )

        data_bytes = header1.to_bytes()
        header2 = structs.AmsHeader.from_bytes(data_bytes)

        self.assertEqual(bytearray(header1.target_net_id.b),
                         bytearray(header2.target_net_id.b))
        self.assertEqual(header1.target_port, header2.target_port)
        self.assertEqual(bytearray(header1.source_net_id),
                         bytearray(header2.source_net_id))
        self.assertEqual(header1.source_port, header2.source_port)
        self.assertEqual(header1.command_id, header2.command_id)
        self.assertEqual(header1.state_flags, header2.state_flags)
        self.assertEqual(header1.length, header2.length)
        self.assertEqual(header1.error_code, header2.error_code)
        self.assertEqual(header1.invoke_id, header2.invoke_id)

    def test_adsnotificationheader(self):
        header1 = structs.AdsNotificationHeader(
            notification_handle=1,
            timestamp=datetime.datetime.utcnow(),
            sample_size=10,
            data=bytearray(b'\x00' * 10)
        )

        data_bytes = header1.to_bytes()
        header2 = structs.AdsNotificationHeader.from_bytes(data_bytes)

        self.assertEqual(header1.notification_handle,
                         header2.notification_handle)
        self.assertEqual(header1.timestamp.utctimetuple(),
                         header2.timestamp.utctimetuple())
        self.assertEqual(header1.sample_size, header2.sample_size)
        self.assertEqual(header1.data, header2.data)


if __name__ == '__main__':
    unittest.main()
