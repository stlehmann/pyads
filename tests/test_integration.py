"""
Integration testing for the pyads module.

Author: David Browne <davidabrowne@gmail.com>

"""
import time
import unittest
from unittest import TestCase

import struct

from pyads import ads, constants
from pyads.utils import platform_is_linux
from pyads.structs import AmsAddr, NotificationAttrib
from pyads.testserver import AdsTestServer


# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = '127.0.0.1.1.1'
TEST_SERVER_IP_ADDRESS = '127.0.0.1'
TEST_SERVER_AMS_PORT = constants.PORT_SPS1


class AdsApiTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        # Start dummy ADS Endpoint
        cls.test_server = AdsTestServer(logging=False)
        cls.test_server.start()

        # Endpoint AMS Address
        cls.endpoint = AmsAddr(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)

        # Open AMS Port
        ads.open_port()

        # wait a bit otherwise error might occur
        time.sleep(1)

        # NOTE: On a Windows machine, this route needs to be configured
        # within the router service for the tests to work.
        if platform_is_linux():
            ads.add_route(cls.endpoint, TEST_SERVER_IP_ADDRESS)

    @classmethod
    def tearDownClass(cls):
        cls.test_server.stop()

        # wait a bit for server to shutdown
        time.sleep(1)

        ads.close_port()

        if platform_is_linux():
            ads.delete_route(cls.endpoint)

    def setUp(self):
        # Clear request history before each test
        self.test_server.request_history = []

    def assert_command_id(self, request, target_id):
        # Check the request code received by the server
        command_id = request.ams_header.command_id
        command_id = struct.unpack('<H', command_id)[0]
        self.assertEqual(command_id, target_id)

    def test_read_device_info(self):
        # Make request to read device info
        name, version = ads.read_device_info(self.endpoint)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READDEVICEINFO)

        # Check the response data from the server
        self.assertEqual(name, 'TestServer')
        self.assertEqual(version.version, 1)
        self.assertEqual(version.revision, 2)
        self.assertEqual(version.build, 3)

    def test_read_uint(self):
        # Make request to read data from a random index (the test server will
        # return the same thing regardless)
        result = ads.read(
            self.endpoint, index_group=constants.INDEXGROUP_DATA,
            index_offset=1, plc_datatype=constants.PLCTYPE_UDINT
        )

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
        result = ads.read(
            self.endpoint, index_group=constants.INDEXGROUP_DATA,
            index_offset=1, plc_datatype=constants.PLCTYPE_STRING
        )

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

        ads.write(
            self.endpoint, index_group=constants.INDEXGROUP_DATA,
            index_offset=1, value=value, plc_datatype=constants.PLCTYPE_UDINT
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

        ads.write(
            self.endpoint, index_group=constants.INDEXGROUP_DATA,
            index_offset=1, value=value, plc_datatype=constants.PLCTYPE_REAL
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

        ads.write(
            self.endpoint, index_group=constants.INDEXGROUP_DATA,
            index_offset=1, value=value, plc_datatype=constants.PLCTYPE_STRING
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
        ads_state, device_state = ads.read_state(self.endpoint)

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
        ads.write_control(
            self.endpoint,
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

        read_value = ads.read_write(
            self.endpoint, index_group=constants.INDEXGROUP_DATA,
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

        read_value = ads.read_by_name(self.endpoint, handle_name,
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

        ads.write_by_name(
            self.endpoint, handle_name, value, constants.PLCTYPE_STRING
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

        handle_name = 'TestHandle'
        attr = NotificationAttrib(length=4)
        requests = self.test_server.request_history

        notification, user = ads.add_device_notification(
            self.endpoint, handle_name, attr, callback
        )

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        # Assert that ADDDEVICENOTIFICATION was used to add device notification
        self.assert_command_id(requests[1], constants.ADSCOMMAND_ADDDEVICENOTE)

        ads.del_device_notification(self.endpoint, notification, user)

        # Assert that ADDDEVICENOTIFICATION was used to add device notification
        self.assert_command_id(requests[2], constants.ADSCOMMAND_DELDEVICENOTE)


if __name__ == '__main__':
    unittest.main()
