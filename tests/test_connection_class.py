"""Test AdsConnection class.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:58
:last modified by: Stefan Lehmann
:last modified time: 2018-07-19 10:46:49

"""
import time
import unittest
import pyads
import struct
from pyads.testserver import AdsTestServer, AmsPacket
from pyads import constants


# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = '127.0.0.1.1.1'
TEST_SERVER_IP_ADDRESS = '127.0.0.1'
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class AdsConnectionClassTestCase(unittest.TestCase):
    """Testcase for ADS connection class."""

    @classmethod
    def setUpClass(cls):
        # type: () -> None
        """Setup the ADS testserver."""
        cls.test_server = AdsTestServer(logging=True)
        cls.test_server.start()

        # wait a bit otherwise error might occur
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        # type: () -> None
        """Tear down the testserver."""
        cls.test_server.stop()

        # wait a bit for server to shutdown
        time.sleep(1)

    def setUp(self):
        # type: () -> None
        """Establish connection to the testserver."""
        self.test_server.request_history = []
        self.plc = pyads.Connection(TEST_SERVER_AMS_NET_ID,
                                    TEST_SERVER_AMS_PORT,
                                    TEST_SERVER_IP_ADDRESS)

    def assert_command_id(self, request, target_id):
        # type: (AmsPacket, int) -> None
        """Assert command_id and target_id."""
        # Check the request code received by the server
        command_id = request.ams_header.command_id
        command_id = struct.unpack('<H', command_id)[0]
        self.assertEqual(command_id, target_id)

    def test_initialization(self):
        # type: () -> None
        """Test init process."""
        with self.assertRaises(TypeError):
            pyads.Connection()

        with self.assertRaises(AttributeError):
            pyads.Connection(None, None)

    def test_no_ip_address(self):
        # type: () -> None
        """Autogenerate IP-address from AMS net id.

        Autogenerate IP-address from AMS net id if no ip address is given
        on initialization.

        """
        plc = pyads.Connection(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)
        self.assertEqual(TEST_SERVER_IP_ADDRESS, plc.ip_address)

    def test_open_twice(self):
        # type: () -> None
        """Open plc connection twice."""
        self.plc.close()

        with self.plc:
            # connection should now be open
            self.assertTrue(self.plc.is_open)
            self.plc.open()

        # connection should now be closed
        self.assertFalse(self.plc.is_open)

    def test_read_device_info(self):
        with self.plc:
            name, version = self.plc.read_device_info()
            requests = self.test_server.request_history

            self.assertEqual(len(requests), 1)
            self.assert_command_id(requests[0],
                                   constants.ADSCOMMAND_READDEVICEINFO)


    def test_read_uint(self):
        with self.plc:
            result = self.plc.read(pyads.INDEXGROUP_DATA, 1,
                                   pyads.PLCTYPE_UDINT)

            # Retrieve list of received requests from server
            requests = self.test_server.request_history

            # Assert that the server received a request
            self.assertEqual(len(requests), 1)

            # Assert that the server received the correct command
            self.assert_command_id(requests[0], constants.ADSCOMMAND_READ)

            # Test server just returns repeated bytes of 0x0F terminated with 0x00
            expected_result = struct.unpack('<I', '\x0F\x0F\x0F\x00'.encode('utf-8'))[0]

            self.assertEqual(result, expected_result)

    def test_read_string(self):
        # Make request to read data from a random index (the test server will
        # return the same thing regardless)
        with self.plc:
            result = self.plc.read(index_group=constants.INDEXGROUP_DATA,
                                   index_offset=1,
                                   plc_datatype=constants.PLCTYPE_STRING)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READ)

        # The string buffer is 1024 bytes long, this will be filled with \x0F
        # and null terminated with \x00 by our test server. The \x00 will get
        # chopped off during parsing to python string type
        expected_result = '\x0F' * 1023
        self.assertEqual(result, expected_result)

    def test_write_uint(self):
        value = 100

        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1, value=value,
                plc_datatype=constants.PLCTYPE_UDINT
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_WRITE)

        # Check the value received by the server
        received_value = struct.unpack('<I', requests[0].ams_header.data[12:])[0]

        self.assertEqual(value, received_value)

    def test_write_float(self):
        value = 123.456

        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1, value=value,
                plc_datatype=constants.PLCTYPE_REAL
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_WRITE)

        # Check the value received by the server
        received_value = struct.unpack('<f', requests[0].ams_header.data[12:])[0]

        # Pythons internal representation of a float has a higher precision
        # than 32 bits, so will be more precise than the value received by the
        # server. To do a comparison we must put the initial 'write' value
        # through the round-trip of converting to 32-bit precision.
        value_32 = struct.unpack('<f', struct.pack('<f', value))[0]

        self.assertEqual(value_32, received_value)

    def test_write_string(self):
        value = "Test String 1234."

        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1, value=value,
                plc_datatype=constants.PLCTYPE_STRING
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_WRITE)

        # Check the value received by the server
        received_value = requests[0].ams_header.data[12:]

        # String should have been sent null terminated
        sent_value = (value + '\x00').encode('utf-8')

        self.assertEqual(sent_value, received_value)

    def test_read_state(self):

        with self.plc:
            ads_state, device_state = self.plc.read_state()

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READSTATE)

        # Test server should return 'running'
        self.assertEqual(ads_state, constants.ADSSTATE_RUN)

        # Device state... Always zero?
        self.assertEqual(device_state, 0)

    def test_write_control(self):
        # Set the ADS State to reset
        # Device state is unused I think? Always seems to be zero
        with self.plc:
            self.plc.write_control(
                ads_state=constants.ADSSTATE_RESET, device_state=0, data=0,
                plc_datatype=constants.PLCTYPE_BYTE
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_WRITECTRL)

    def test_read_write(self):
        write_value = 100

        with self.plc:
            read_value = self.plc.read_write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1, plc_read_datatype=constants.PLCTYPE_UDINT,
                value=write_value, plc_write_datatype=constants.PLCTYPE_UDINT
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)

        # Check the value received by the server
        received_value = struct.unpack('<I', requests[0].ams_header.data[16:])[0]
        self.assertEqual(write_value, received_value)

        # Check read value returned by server:
        # Test server just returns repeated bytes of 0x0F terminated with 0x00
        expected_result = struct.unpack('<I', '\x0F\x0F\x0F\x00'.encode('utf-8'))[0]
        self.assertEqual(read_value, expected_result)

    def test_read_by_name(self):
        handle_name = "TestHandle"

        with self.plc:
            read_value = self.plc.read_by_name(handle_name,
                                               constants.PLCTYPE_BYTE)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 3 requests
        self.assertEqual(len(requests), 3)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        # Assert that the server received the handle by name
        received_value = requests[0].ams_header.data[16:]
        sent_value = (handle_name + '\x00').encode('utf-8')
        self.assertEqual(sent_value, received_value)

        # Assert that next, the Read command was used to get the value
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READ)

        # Assert that Write was used to release the handle
        self.assert_command_id(requests[2], constants.ADSCOMMAND_WRITE)

        # Check read value returned by server:
        # Test server just returns repeated bytes of 0x0F terminated with 0x00
        # But because the read value is only 1-byte long, we just get 0x00
        expected_result = 0
        self.assertEqual(read_value, expected_result)

    def test_write_by_name(self):
        handle_name = "TestHandle"
        value = "Test Value"

        with self.plc:
            self.plc.write_by_name(
                handle_name, value, constants.PLCTYPE_STRING
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 3 requests
        self.assertEqual(len(requests), 3)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)

        # Assert that Write command was used to write the value
        self.assert_command_id(requests[1], constants.ADSCOMMAND_WRITE)
        # Check the value written matches our value
        received_value = requests[1].ams_header.data[12:].decode('utf-8').rstrip('\x00')
        self.assertEqual(value, received_value)

        # Assert that Write was used to release the handle
        self.assert_command_id(requests[2], constants.ADSCOMMAND_WRITE)

    def test_device_notification(self):

        def callback(adr, notification, user):
            pass

        handle_name = 'test'
        attr = pyads.NotificationAttrib(8)
        requests = self.test_server.request_history

        with self.plc:
            notification, user = self.plc.add_device_notification(
                handle_name, attr, callback
            )

            # Assert that Read/Write command was used to get the handle by name
            self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
            # Assert that ADDDEVICENOTIFICATION was used to add device notification
            self.assert_command_id(requests[1], constants.ADSCOMMAND_ADDDEVICENOTE)

            self.plc.del_device_notification(notification, user)

        # Assert that ADDDEVICENOTIFICATION was used to add device notification
        self.assert_command_id(requests[2], constants.ADSCOMMAND_DELDEVICENOTE)

    def test_multiple_connect(self):
        """
        Using context manager multiple times after each other for
        disconnecting and connecting to/from server should work without any
        errors.

        """
        handle_name = "TestHandle"
        value = "Test Value"

        with self.plc:
            self.assertTrue(self.plc.is_open)
            self.plc.write_by_name(
                handle_name, value, constants.PLCTYPE_STRING
            )
        self.assertFalse(self.plc.is_open)
        with self.plc:
            self.assertTrue(self.plc.is_open)
            self.plc.read_by_name(
                handle_name, constants.PLCTYPE_STRING
            )
        self.assertFalse(self.plc.is_open)

    def test_get_local_address(self):
        # type: () -> None
        """Test get_local_address method."""
        with self.plc:
            self.plc.get_local_address()

    def test_methods_with_closed_port(self):
        # type: () -> None
        """Test pyads.Connection methods with no open port."""
        with self.plc:
            adr = self.plc.get_local_address()
            self.assertIsNotNone(adr)

        plc = pyads.Connection('127.0.0.1.1.1', 851)
        self.assertIsNone(plc.get_local_address())
        self.assertIsNone(plc.read_state())
        self.assertIsNone(plc.read_device_info())
        self.assertIsNone(
            plc.read_write(1, 2, pyads.PLCTYPE_INT, 1, pyads.PLCTYPE_INT)
        )
        self.assertIsNone(plc.read(1, 2, pyads.PLCTYPE_INT))
        self.assertIsNone(plc.read_by_name("hello", pyads.PLCTYPE_INT))
        self.assertIsNone(
            plc.read_structure_by_name("hello", (('', pyads.PLCTYPE_BOOL, 1),
                                                 ('', pyads.PLCTYPE_BOOL, 1))
            )
        )
        self.assertIsNone(
            plc.add_device_notification(
                "test", pyads.NotificationAttrib(4), lambda x: x
            )
        )

    def test_set_timeout(self):
        # type: () -> None
        """Test timeout function."""
        with self.plc:
            self.assertIsNone(self.plc.set_timeout(100))


if __name__ == '__main__':
    unittest.main()
    if __name__ == '__main__':
        unittest.main()
