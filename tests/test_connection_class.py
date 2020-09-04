"""Test AdsConnection class.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:58

"""
import ctypes
from ctypes import addressof, memmove, resize, sizeof, pointer
import datetime
import time
import unittest
import pyads
import struct
from pyads.testserver import AdsTestServer, AmsPacket, AdvancedHandler
from pyads.structs import NotificationAttrib
from pyads import constants, structs
from collections import OrderedDict


# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class _Struct(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


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
        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT, TEST_SERVER_IP_ADDRESS
        )

    def assert_command_id(self, request, target_id):
        # type: (AmsPacket, int) -> None
        """Assert command_id and target_id."""
        # Check the request code received by the server
        command_id = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id)[0]
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

    def test_netid_port(self):
        self.assertEqual(self.plc.ams_netid, TEST_SERVER_AMS_NET_ID)
        self.assertEqual(self.plc.ams_port, TEST_SERVER_AMS_PORT)
        with self.assertRaises(ValueError):
            self.plc.ams_netid = "1.1.1.1.1.1.1"
        self.plc.ams_netid = "1.1.1.1.1.1"
        self.assertEqual(self.plc.ams_netid, "1.1.1.1.1.1")
        self.plc.ams_port = 1
        self.assertEqual(self.plc.ams_port, 1)

        # test for AttributeError when trying to set netid or port
        # for an open connection
        self.plc._open = True
        with self.assertRaises(AttributeError):
            self.plc.ams_netid = "1.1.1.1.1.2"
        with self.assertRaises(AttributeError):
            self.plc.ams_port = 2

    def test_read_array(self):
        # Make request to read array data from a random index (the test server will
        # return the same thing regardless)
        with self.plc:
            result = self.plc.read(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_datatype=constants.PLCTYPE_ARR_INT(5),
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
            expected_result = list(struct.unpack("<hhhhh", b"\x0F" * 9 + b"\x00"))

            self.assertEqual(result, expected_result)

    def test_read_array_return_ctypes(self):
        # Make request to read array data from a random index (the test server will
        # return the same thing regardless)
        with self.plc:
            result = self.plc.read(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_datatype=constants.PLCTYPE_ARR_INT(5),
                return_ctypes=True,
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
            expected_result_raw = b"\x0F" * 9 + b"\x00"
            expected_result = list(struct.unpack("<hhhhh", expected_result_raw))
            self.assertEqual([x for x in result], expected_result)

    def test_read_device_info(self):
        with self.plc:
            name, version = self.plc.read_device_info()
            requests = self.test_server.request_history

            self.assertEqual(len(requests), 1)
            self.assert_command_id(requests[0], constants.ADSCOMMAND_READDEVICEINFO)

    def test_read_uint(self):
        with self.plc:
            result = self.plc.read(pyads.INDEXGROUP_DATA, 1, pyads.PLCTYPE_UDINT)

            # Retrieve list of received requests from server
            requests = self.test_server.request_history

            # Assert that the server received a request
            self.assertEqual(len(requests), 1)

            # Assert that the server received the correct command
            self.assert_command_id(requests[0], constants.ADSCOMMAND_READ)

            # Test server just returns repeated bytes of 0x0F terminated with 0x00
            expected_result = struct.unpack("<I", "\x0F\x0F\x0F\x00".encode("utf-8"))[0]

            self.assertEqual(result, expected_result)

    def test_read_string(self):
        # Make request to read data from a random index (the test server will
        # return the same thing regardless)
        with self.plc:
            result = self.plc.read(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_datatype=constants.PLCTYPE_STRING,
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
        expected_result = "\x0F" * 1023
        self.assertEqual(result, expected_result)

    def test_write_uint(self):
        value = 100

        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                value=value,
                plc_datatype=constants.PLCTYPE_UDINT,
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_WRITE)

        # Check the value received by the server
        received_value = struct.unpack("<I", requests[0].ams_header.data[12:])[0]

        self.assertEqual(value, received_value)

    def test_write_float(self):
        value = 123.456

        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                value=value,
                plc_datatype=constants.PLCTYPE_REAL,
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_WRITE)

        # Check the value received by the server
        received_value = struct.unpack("<f", requests[0].ams_header.data[12:])[0]

        # Pythons internal representation of a float has a higher precision
        # than 32 bits, so will be more precise than the value received by the
        # server. To do a comparison we must put the initial 'write' value
        # through the round-trip of converting to 32-bit precision.
        value_32 = struct.unpack("<f", struct.pack("<f", value))[0]

        self.assertEqual(value_32, received_value)

    def test_write_string(self):
        value = "Test String 1234."

        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                value=value,
                plc_datatype=constants.PLCTYPE_STRING,
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
        sent_value = (value + "\x00").encode("utf-8")

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

    def test_write_struct(self):
        write_value = _Struct(-123, 456)
        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                value=write_value,
                plc_datatype=_Struct,
            )
            # Retrieve list of received requests from server
            requests = self.test_server.request_history
            # Check the value received by the server
            received_value = _Struct.from_buffer_copy(requests[0].ams_header.data[12:])
            self.assertEqual(write_value.x, received_value.x)
            self.assertEqual(write_value.y, received_value.y)

    def test_write_array(self):
        write_value = tuple(range(5))
        with self.plc:
            self.plc.write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                value=write_value,
                plc_datatype=constants.PLCTYPE_UDINT * 5,
            )

            # Retrieve list of received requests from server
            requests = self.test_server.request_history

            # Check the value received by the server
            received_value = struct.unpack("<IIIII", requests[0].ams_header.data[12:])
            self.assertEqual(write_value, received_value)

    def test_write_control(self):
        # Set the ADS State to reset
        # Device state is unused I think? Always seems to be zero
        with self.plc:
            self.plc.write_control(
                ads_state=constants.ADSSTATE_RESET,
                device_state=0,
                data=0,
                plc_datatype=constants.PLCTYPE_BYTE,
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
                index_offset=1,
                plc_read_datatype=constants.PLCTYPE_UDINT,
                value=write_value,
                plc_write_datatype=constants.PLCTYPE_UDINT,
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a request
        self.assertEqual(len(requests), 1)

        # Assert that the server received the correct command
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)

        # Check the value received by the server
        received_value = struct.unpack("<I", requests[0].ams_header.data[16:])[0]
        self.assertEqual(write_value, received_value)

        # Check read value returned by server:
        # Test server just returns repeated bytes of 0x0F terminated with 0x00
        expected_result = struct.unpack("<I", "\x0F\x0F\x0F\x00".encode("utf-8"))[0]
        self.assertEqual(read_value, expected_result)

    def test_read_write_read_none(self):
        write_value = 100

        with self.plc:
            read_value = self.plc.read_write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_read_datatype=None,
                value=write_value,
                plc_write_datatype=constants.PLCTYPE_UDINT,
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Check the value received by the server
        received_value = struct.unpack("<I", requests[0].ams_header.data[16:])[0]
        self.assertEqual(write_value, received_value)
        # Check nothing was to be read
        read_size = struct.unpack("<I", requests[0].ams_header.data[8:12])[0]
        self.assertEqual(read_size, 0)
        # Check return value
        self.assertIsNone(read_value)

    def test_read_write_write_none(self):
        with self.plc:
            read_value = self.plc.read_write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_read_datatype=constants.PLCTYPE_UDINT,
                value=None,
                plc_write_datatype=None,
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Check nothing was to be written
        write_size = struct.unpack("<I", requests[0].ams_header.data[12:16])[0]
        self.assertEqual(write_size, 0)

        # Check read value returned by server:
        # Test server just returns repeated bytes of 0x0F terminated with 0x00
        expected_result = struct.unpack("<I", "\x0F\x0F\x0F\x00".encode("utf-8"))[0]
        self.assertEqual(read_value, expected_result)

    def test_read_write_array(self):
        write_value = tuple(range(5))
        with self.plc:
            self.plc.read_write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_read_datatype=constants.PLCTYPE_UDINT,
                value=write_value,
                plc_write_datatype=constants.PLCTYPE_UDINT * 5,
            )
            # Retrieve list of received requests from server
            requests = self.test_server.request_history
            # Check the value received by the server
            received_value = struct.unpack("<IIIII", requests[0].ams_header.data[16:])
            self.assertEqual(write_value, received_value)

    def test_read_write_struct(self):
        write_value = _Struct(-123, 456)
        with self.plc:
            self.plc.read_write(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_read_datatype=_Struct,
                value=write_value,
                plc_write_datatype=_Struct,
            )
            # Retrieve list of received requests from server
            requests = self.test_server.request_history
            # Check the value received by the server
            received_value = _Struct.from_buffer_copy(requests[0].ams_header.data[16:])
            self.assertEqual(write_value.x, received_value.x)
            self.assertEqual(write_value.y, received_value.y)

    def test_read_by_name(self):
        handle_name = "TestHandle"

        with self.plc:
            read_value = self.plc.read_by_name(handle_name, constants.PLCTYPE_BYTE)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 3 requests
        self.assertEqual(len(requests), 3)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        # Assert that the server received the handle by name
        received_value = requests[0].ams_header.data[16:]
        sent_value = (handle_name + "\x00").encode("utf-8")
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

    def test_read_by_name_with_handle(self):
        # type: () -> None
        """Test read_by_name method with handle passed in"""
        handle_name = "TestHandle"
        with self.plc:
            handle = self.plc.get_handle(handle_name)
            read_value = self.plc.read_by_name(
                "", constants.PLCTYPE_BYTE, handle=handle
            )

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 2 requests
        self.assertEqual(len(requests), 2)

        # Assert that the server received the handle by name
        received_value = requests[0].ams_header.data[16:]
        sent_value = (handle_name + "\x00").encode("utf-8")
        self.assertEqual(sent_value, received_value)

        # Assert that next, the Read command was used to get the value
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READ)

        # Check read value returned by server:
        # Test server just returns repeated bytes of 0x0F terminated with 0x00
        # But because the read value is only 1-byte long, we just get 0x00
        expected_result = 0
        self.assertEqual(read_value, expected_result)

        with self.plc:
            self.plc.release_handle(handle)

    def test_read_structure_by_name(self):
        # type: () -> None
        """Test read by structure method"""
        # TODO may need testserver.py changes to increase test usefulness

        handle_name = "TestHandle"

        structure_def = (("xVar", pyads.PLCTYPE_BYTE, 1),)

        # test with no structure size passed in
        with self.plc:
            read_value = self.plc.read_structure_by_name(handle_name, structure_def)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 3 requests
        self.assertEqual(len(requests), 3)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        # Assert that the server received the handle by name
        received_value = requests[0].ams_header.data[16:]
        sent_value = (handle_name + "\x00").encode("utf-8")
        self.assertEqual(sent_value, received_value)

        # Assert that next, the Read command was used to get the value
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READ)

        # Assert that Write was used to release the handle
        self.assert_command_id(requests[2], constants.ADSCOMMAND_WRITE)

        # Check read value returned by server:
        # Test server just returns repeated bytes of 0x0F terminated with 0x00
        # But because the read value is only 1-byte long, we just get 0x00
        expected_result = OrderedDict([("xVar", 0)])
        self.assertEqual(read_value, expected_result)

        # Test with structure size passed in
        structure_size = pyads.size_of_structure(structure_def)
        with self.plc:
            read_value = self.plc.read_structure_by_name(
                handle_name, structure_def, structure_size=structure_size
            )
        self.assertEqual(read_value, expected_result)

        # Test with handle passed in
        with self.plc:
            handle = self.plc.get_handle(handle_name)
            read_value = self.plc.read_structure_by_name(
                "", structure_def, handle=handle
            )
        self.assertEqual(read_value, expected_result)
        with self.plc:
            self.plc.release_handle(handle)

    def test_write_by_name(self):
        handle_name = "TestHandle"
        value = "Test Value"

        with self.plc:
            self.plc.write_by_name(handle_name, value, constants.PLCTYPE_STRING)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 3 requests
        self.assertEqual(len(requests), 3)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)

        # Assert that Write command was used to write the value
        self.assert_command_id(requests[1], constants.ADSCOMMAND_WRITE)
        # Check the value written matches our value
        received_value = requests[1].ams_header.data[12:].decode("utf-8").rstrip("\x00")
        self.assertEqual(value, received_value)

        # Assert that Write was used to release the handle
        self.assert_command_id(requests[2], constants.ADSCOMMAND_WRITE)

    def test_write_by_name_with_handle(self):
        # type: () -> None
        """Test write_by_name method with handle passed in"""
        handle_name = "TestHandle"
        value = "Test Value"

        with self.plc:
            handle = self.plc.get_handle(handle_name)
            self.plc.write_by_name("", value, constants.PLCTYPE_STRING, handle=handle)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 2 requests
        self.assertEqual(len(requests), 2)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)

        # Assert that Write command was used to write the value
        self.assert_command_id(requests[1], constants.ADSCOMMAND_WRITE)
        # Check the value written matches our value
        received_value = requests[1].ams_header.data[12:].decode("utf-8").rstrip("\x00")
        self.assertEqual(value, received_value)

        with self.plc:
            self.plc.release_handle(handle)

    def test_device_notification(self):
        def callback(notification, data):
            pass

        handle_name = "test"
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

    def test_device_notification_by_name(self):
        def callback(notification, data):
            pass

        handle_name = "TestHandle"
        attr = NotificationAttrib(length=4)
        requests = self.test_server.request_history

        with self.plc:
            notification, user = self.plc.add_device_notification(handle_name, attr, callback)
            # Assert that Read/Write command was used to get the handle by name
            self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
            # Assert that ADDDEVICENOTIFICATION was used to add device notification
            self.assert_command_id(requests[1], constants.ADSCOMMAND_ADDDEVICENOTE)

            self.plc.del_device_notification(notification, user)

        # Assert that ADDDEVICENOTIFICATION was used to add device notification
        self.assert_command_id(requests[2], constants.ADSCOMMAND_DELDEVICENOTE)

    def test_device_notification_by_tuple(self):
        def callback(notification, data):
            pass

        n_index_group = 1
        n_index_offset = 0
        attr = NotificationAttrib(length=4)
        requests = self.test_server.request_history
    
        with self.plc:
            notification, user_hnl = self.plc.add_device_notification(
                    (n_index_group, n_index_offset), attr, callback
            )

            # Assert that ADDDEVICENOTIFICATION was used to add device notification
            self.assert_command_id(requests[0], constants.ADSCOMMAND_ADDDEVICENOTE)
            # Delete notification without user-handle
            self.plc.del_device_notification(notification, None)

            # Create notification with user_handle
            notification, new_user_hnl = self.plc.add_device_notification(
                (n_index_group, n_index_offset), attr, callback, user_handle=user_hnl
            )
            self.assertEqual(new_user_hnl, user_hnl)

            # Assert that ADDDEVICENOTIFICATION was used to add device notification
            self.assert_command_id(requests[1], constants.ADSCOMMAND_DELDEVICENOTE)
            self.plc.del_device_notification(notification, None)

    def test_device_notification_data_error(self):
        def callback(notification, data):
            pass

        attr = NotificationAttrib(length=4)

        with self.plc:
            with self.assertRaises(TypeError):
                self.plc.add_device_notification(0, attr, callback)

            with self.assertRaises(TypeError):
                self.plc.add_device_notification(None, attr, callback)

    def test_decorated_device_notification(self):

        plc = pyads.Connection(TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT)

        @plc.notification(pyads.PLCTYPE_INT)
        def callback(handle, name, timestamp, value):
            print (handle, name, timestamp, value)

        with plc:
            handles = plc.add_device_notification("a", pyads.NotificationAttrib(20), callback)
            plc.write_by_name("a", 1, pyads.PLCTYPE_INT)
            plc.del_device_notification(*handles)


    def create_notification_struct(self, payload):
        # type: (bytes) -> structs.SAdsNotificationHeader
        buf = b"\x00" * 12  # hNotification, nTimeStamp
        buf += struct.pack("<i", len(payload))
        buf += payload
        notification = structs.SAdsNotificationHeader()
        resize(notification, len(buf))
        memmove(
            pointer(notification),
            (ctypes.c_ubyte * len(buf)).from_buffer_copy(buf),
            sizeof(notification),
        )
        return notification

    def test_notification_decorator(self):
        # type: () -> None
        """Test decoding of header by notification decorator"""

        @self.plc.notification()
        def callback(handle, name, timestamp, value):
            self.assertEqual(handle, 1234)
            self.assertEqual(name, "TestName")
            self.assertEqual(timestamp, datetime.datetime(2020, 1, 1))
            self.assertEqual(value, bytearray((5,)))

        notification = structs.SAdsNotificationHeader()
        notification.hNotification = 1234
        notification.nTimeStamp = 132223104000000000
        notification.cbSampleSize = 1
        notification.data = 5
        callback(pointer(notification), "TestName")

    def test_notification_decorator_filetime(self):
        # type: () -> None
        """Test passthrough of FILETIME value by notification decorator"""

        @self.plc.notification(timestamp_as_filetime=True)
        def callback(handle, name, timestamp, value):
            self.assertEqual(timestamp, 132223104000000000)

        notification = structs.SAdsNotificationHeader()
        notification.nTimeStamp = 132223104000000000
        notification.cbSampleSize = 1
        notification.data = 5
        callback(pointer(notification), "TestName")

    def test_notification_decorator_string(self):
        # type: () -> None
        """Test decoding of STRING value by notification decorator"""

        @self.plc.notification(constants.PLCTYPE_STRING)
        def callback(handle, name, timestamp, value):
            self.assertEqual(value, "Hello world!")

        notification = self.create_notification_struct(b"Hello world!\x00\x00\x00\x00")
        callback(pointer(notification), "")

    def test_notification_decorator_lreal(self):
        # type: () -> None
        """Test decoding of LREAL value by notification decorator"""

        @self.plc.notification(constants.PLCTYPE_LREAL)
        def callback(handle, name, timestamp, value):
            self.assertEqual(value, 1234.56789012345)

        notification = self.create_notification_struct(
            struct.pack("<d", 1234.56789012345)
        )
        callback(pointer(notification), "")

    def test_notification_decorator_struct(self):
        # type: () -> None
        """Test decoding of structure value by notification decorator"""

        @self.plc.notification(structs.SAdsVersion)
        def callback(handle, name, timestamp, value):
            self.assertEqual(value.version, 3)
            self.assertEqual(value.revision, 1)
            self.assertEqual(value.build, 3040)

        notification = self.create_notification_struct(
            bytes(structs.SAdsVersion(version=3, revision=1, build=3040))
        )
        callback(pointer(notification), "")

    def test_notification_decorator_array(self):
        # type: () -> None
        """Test decoding of array value by notification decorator"""

        @self.plc.notification(constants.PLCTYPE_ARR_INT(5))
        def callback(handle, name, timestamp, value):
            self.assertEqual(value, [0, 1, 2, 3, 4])

        notification = self.create_notification_struct(
            b"\x00\x00\x01\x00\x02\x00\x03\x00\x04\x00"
        )
        callback(pointer(notification), "")

    def test_notification_decorator_struct_array(self):
        # type: () -> None
        """Test decoding of array of structs value by notification decorator"""

        arr_type = structs.SAdsVersion * 4

        @self.plc.notification(arr_type)
        def callback(handle, name, timestamp, value):
            self.assertEqual(len(value), 4)
            for i in range(4):
                self.assertEqual(value[i].version, i)
                self.assertEqual(value[i].revision, 1)
                self.assertEqual(value[i].build, 3040)

        data = b""
        for i in range(4):
            data += bytes(structs.SAdsVersion(version=i, revision=1, build=3040))
        notification = self.create_notification_struct(data)
        callback(pointer(notification), "")

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
            self.plc.write_by_name(handle_name, value, constants.PLCTYPE_STRING)
        self.assertFalse(self.plc.is_open)
        with self.plc:
            self.assertTrue(self.plc.is_open)
            self.plc.read_by_name(handle_name, constants.PLCTYPE_STRING)
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

        plc = pyads.Connection("127.0.0.1.1.1", 851)
        self.assertIsNone(plc.get_local_address())
        self.assertIsNone(plc.read_state())
        self.assertIsNone(plc.read_device_info())
        self.assertIsNone(plc.read_write(1, 2, pyads.PLCTYPE_INT, 1, pyads.PLCTYPE_INT))
        self.assertIsNone(plc.read(1, 2, pyads.PLCTYPE_INT))
        self.assertIsNone(plc.read_by_name("hello", pyads.PLCTYPE_INT))
        self.assertIsNone(plc.get_handle("hello"))
        self.assertIsNone(
            plc.read_structure_by_name(
                "hello", (("", pyads.PLCTYPE_BOOL, 1), ("", pyads.PLCTYPE_BOOL, 1))
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

    def test_get_and_release_handle(self):
        # type: () -> None
        """Test get_handle and release_handle methods"""
        handle_name = "TestHandle"
        with self.plc:
            handle = self.plc.get_handle(handle_name)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received a single request
        self.assertEqual(len(requests), 1)

        # Assert that Read/Write command was used to get the handle by name
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        # Assert that the server received the handle by name
        received_value = requests[0].ams_header.data[16:]
        sent_value = (handle_name + "\x00").encode("utf-8")
        self.assertEqual(sent_value, received_value)

        with self.plc:
            self.plc.release_handle(handle)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server history now has 2 requests
        self.assertEqual(len(requests), 2)

        # Assert that Write was used to release the handle
        self.assert_command_id(requests[1], constants.ADSCOMMAND_WRITE)


class AdsApiTestCaseAdvanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start dummy ADS Endpoint
        cls.test_server = AdsTestServer(AdvancedHandler(), logging=False)
        cls.test_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.test_server.stop()

        # wait a bit for server to shutdown
        time.sleep(1)

    def setUp(self):
        # Clear request history before each test
        self.test_server.request_history = []
        self.test_server.handler.reset()
        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT, TEST_SERVER_IP_ADDRESS
        )


    def test_read_check_length(self):
        # Write data shorter than what should be read
        with self.plc:
            self.plc.write(
                value=1,
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_datatype=constants.PLCTYPE_USINT,

            )

            with self.assertRaises(RuntimeError):
                # Since the length is checked, this must give an error
                self.plc.read(
                    index_group=constants.INDEXGROUP_DATA,
                    index_offset=1,
                    plc_datatype=constants.PLCTYPE_UINT,
                    check_length=True,
                )

            # If the length is not checked, no error should be raised
            value = self.plc.read(
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1,
                plc_datatype=constants.PLCTYPE_UINT,
                check_length=False,
            )
            self.assertEqual(value, 1)


if __name__ == "__main__":
    unittest.main()
    if __name__ == "__main__":
        unittest.main()
