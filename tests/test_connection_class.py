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
from pyads.testserver import AdsTestServer, AmsPacket, AdvancedHandler, PLCVariable
from pyads.structs import NotificationAttrib
from pyads import constants, structs, PLC_DEFAULT_STRING_SIZE
from collections import OrderedDict

# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


def create_notification_struct(payload: bytes) -> \
        structs.SAdsNotificationHeader:
    """Create notification callback structure"""
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


class _Struct(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


class AdsConnectionClassTestCase(unittest.TestCase):
    """Testcase for ADS connection class."""

    @classmethod
    def setUpClass(cls):
        # type: () -> None
        """Setup the ADS testserver."""
        cls.test_server = AdsTestServer(logging=False)
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

        with self.assertRaises(TypeError):
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

        # return None if connection is closed
        self.assertIsNone(self.plc.write_by_name("test_var", 1, pyads.PLCTYPE_INT))

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

    def test_write_structure_by_name(self):
        # type: () -> None
        """Test write by structure method"""

        handle_name = "TestHandle"
        struct_to_write = OrderedDict([("sVar", "Test Value")])
        value = "Test Value"

        structure_def = (("sVar", pyads.PLCTYPE_STRING, 1),)

        # test with no structure size passed in
        with self.plc:
            self.plc.write_structure_by_name(
                handle_name, struct_to_write, structure_def
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
        received_value = requests[1].ams_header.data[12:].decode("utf-8").rstrip("\x00")
        self.assertEqual(value, received_value)

        # Assert that Write was used to release the handle
        self.assert_command_id(requests[2], constants.ADSCOMMAND_WRITE)

        # Test with structure size passed in
        structure_size = pyads.size_of_structure(structure_def)
        with self.plc:
            self.plc.write_structure_by_name(
                handle_name,
                struct_to_write,
                structure_def,
                structure_size=structure_size,
            )

        requests = self.test_server.request_history
        received_value = requests[1].ams_header.data[12:].decode("utf-8").rstrip("\x00")
        self.assertEqual(value, received_value)

        # Test with handle passed in
        with self.plc:
            handle = self.plc.get_handle(handle_name)
            self.plc.write_structure_by_name(
                "", struct_to_write, structure_def, handle=handle
            )

        requests = self.test_server.request_history
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
            print(handle, name, timestamp, value)

        with plc:
            handles = plc.add_device_notification(
                "a", pyads.NotificationAttrib(20), callback
            )
            plc.write_by_name("a", 1, pyads.PLCTYPE_INT)
            plc.del_device_notification(*handles)

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

        notification = create_notification_struct(b"Hello world!\x00\x00\x00\x00")
        callback(pointer(notification), "")

    def test_notification_decorator_lreal(self):
        # type: () -> None
        """Test decoding of LREAL value by notification decorator"""

        @self.plc.notification(constants.PLCTYPE_LREAL)
        def callback(handle, name, timestamp, value):
            self.assertEqual(value, 1234.56789012345)

        notification = create_notification_struct(
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

        notification = create_notification_struct(
            bytes(structs.SAdsVersion(version=3, revision=1, build=3040))
        )
        callback(pointer(notification), "")

    def test_notification_decorator_array(self):
        # type: () -> None
        """Test decoding of array value by notification decorator"""

        @self.plc.notification(constants.PLCTYPE_ARR_INT(5))
        def callback(handle, name, timestamp, value):
            self.assertEqual(value, [0, 1, 2, 3, 4])

        notification = create_notification_struct(
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
        notification = create_notification_struct(data)
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

    def test_read_list(self):
        variables = ["i1", "i2", "i3", "str_test"]

        # Read twice to show caching
        with self.plc:
            read_values = self.plc.read_list_by_name(variables)
            read_values2 = self.plc.read_list_by_name(variables)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received - 4x symbol info, 1x sum read, 1x sum read (second)
        self.assertEqual(len(requests), 6)

        # Assert that all commands are read write
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[2], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[3], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[4], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[5], constants.ADSCOMMAND_READWRITE)

        # Expected result
        expected_result = {
            "i1": 1,
            "i2": 2,
            "i3": 3,
            "str_test": "test",
        }
        self.assertEqual(read_values, expected_result)
        self.assertEqual(read_values2, expected_result)

    def test_read_list_without_cache(self):

        # Repeat the test without cache
        variables = ["i1", "i2", "i3", "str_test"]

        with self.plc:
            read_values = self.plc.read_list_by_name(variables, cache_symbol_info=False)
            read_values2 = self.plc.read_list_by_name(variables)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received - 4x symbol info, 1x sum read, 4x symbol info (as no cache), 1 x sum read
        self.assertEqual(len(requests), 10)

        # Assert that all commands are read write
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[2], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[3], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[4], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[5], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[6], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[7], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[8], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[9], constants.ADSCOMMAND_READWRITE)

        # Expected result
        expected_result = {
            "i1": 1,
            "i2": 2,
            "i3": 3,
            "str_test": "test",
        }
        self.assertEqual(read_values, expected_result)
        self.assertEqual(read_values2, expected_result)

    def test_read_list_ads_sub_commands(self):
        variables = ["TestVar1", "TestVar2", "str_TestVar3", "TestVar4"]

        with self.plc:
            read_values = self.plc.read_list_by_name(variables, ads_sub_commands=2)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received - 4x symbol info, 2x sum read (as sub commands split request into two reads)
        self.assertEqual(len(requests), 6)

        # Assert that all commands are read write
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[2], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[3], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[4], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[5], constants.ADSCOMMAND_READWRITE)

        # Expected result
        expected_result = {
            "TestVar1": 1,
            "TestVar2": 2,
            "str_TestVar3": "test",
            "TestVar4": 2,
        }
        self.assertEqual(read_values, expected_result)

    def test_write_list_without_cache(self):
        variables = {
            "i1": 1,
            "i2": 2,
            "i3": 3,
            "str_test": "test",
        }

        with self.plc:
            errors = self.plc.write_list_by_name(variables, cache_symbol_info=False)
            errors2 = self.plc.write_list_by_name(variables)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received - 4x symbol info, 1x sum write, 4x symbol info (as no cache), 1x sum write
        self.assertEqual(len(requests), 10)

        # Assert that all commands are read write
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[2], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[3], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[4], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[5], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[6], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[7], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[8], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[9], constants.ADSCOMMAND_READWRITE)

        # Expected result
        expected_result = {
            "i1": "no error",
            "i2": "no error",
            "i3": "no error",
            "str_test": "no error",
        }
        self.assertEqual(errors, expected_result)
        self.assertEqual(errors2, expected_result)

    def test_read_structure_list(self):
        variables = ["TestStructure", "TestVar"]
        structure_defs = {"TestStructure": (("xVar", pyads.PLCTYPE_BYTE, 1),)}

        with self.plc:
            actual_result = self.plc.read_list_by_name(variables, cache_symbol_info=False,
                                                       structure_defs=structure_defs)

        requests = self.test_server.request_history
        self.assertEqual(len(requests), 3)

        # Assert that all commands are read write - 2x symbol info, 1x sum write
        for request in requests:
            self.assert_command_id(request, constants.ADSCOMMAND_READWRITE)

        expected_result = {
            "TestStructure": {"xVar": 1},
            "TestVar": 2,
        }
        self.assertEqual(actual_result, expected_result)

    def test_write_list(self):
        variables = {
            "i1": 1,
            "i2": 2,
            "i3": 3,
            "str_test": "test",
        }

        with self.plc:
            errors = self.plc.write_list_by_name(variables)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 5 requests 4x symbol info, 1x sum write
        self.assertEqual(len(requests), 5)

        # Assert that all commands are read write
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[2], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[3], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[4], constants.ADSCOMMAND_READWRITE)

        # Expected result
        expected_result = {
            "i1": "no error",
            "i2": "no error",
            "i3": "no error",
            "str_test": "no error",
        }
        self.assertEqual(errors, expected_result)

    def test_write_list_ads_sub_commands(self):
        variables = {
            "TestVar1": 1,
            "TestVar2": 2,
            "str_TestVar3": "test",
            "TestVar4": 3,
        }

        with self.plc:
            errors = self.plc.write_list_by_name(variables, ads_sub_commands=2)

        # Retrieve list of received requests from server
        requests = self.test_server.request_history

        # Assert that the server received 6 requests - 4x symbol info, 2x write as split by subcommands
        self.assertEqual(len(requests), 6)

        # Assert that all commands are read write
        self.assert_command_id(requests[0], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[1], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[2], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[3], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[4], constants.ADSCOMMAND_READWRITE)
        self.assert_command_id(requests[5], constants.ADSCOMMAND_READWRITE)

        # Expected result
        expected_result = {
            "TestVar1": "no error",
            "TestVar2": "no error",
            "str_TestVar3": "no error",
            "TestVar4": "no error",
        }
        self.assertEqual(errors, expected_result)

    def test_ads_symbol_entry(self):
        symbol_name = "Test_Symbol"
        symbol_type = "UINT8"
        comment = "Test Comment"

        t_byte_buffer = ctypes.c_ubyte * 768
        Buf = t_byte_buffer()

        struct.pack_into(
            str(len(symbol_name)) + "s", Buf, 0, symbol_name.encode("utf-8")
        )
        struct.pack_into(
            str(len(symbol_type)) + "s",
            Buf,
            len(symbol_name) + 1,
            symbol_type.encode("utf-8"),
        )
        struct.pack_into(
            str(len(comment)) + "s",
            Buf,
            len(symbol_name) + len(symbol_type) + 2,
            comment.encode("utf-8"),
        )

        test_struct = structs.SAdsSymbolEntry(
            0, 0, 0, 0, 0, 0, len(symbol_name), len(symbol_type), len(comment), Buf
        )

        self.assertEqual(symbol_name, test_struct.name)
        self.assertEqual(symbol_type, test_struct.symbol_type)
        self.assertEqual(comment, test_struct.comment)


class AdsApiTestCaseAdvanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start dummy ADS Endpoint
        cls.handler = AdvancedHandler()
        cls.test_server = AdsTestServer(handler=cls.handler, logging=False)
        cls.test_server.start()

        # wait a bit otherwise error might occur
        time.sleep(1)

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

    def assert_command_id(self, request: AmsPacket, target_id: int) -> None:
        """Assert command_id and target_id."""
        # Check the request code received by the server
        command_id = request.ams_header.command_id
        command_id = struct.unpack("<H", command_id)[0]
        self.assertEqual(command_id, target_id)

    def test_read_check_length(self):
        # Write data shorter than what should be read
        self.handler.add_variable(
            PLCVariable("i", 1, constants.ADST_UINT8, symbol_type="USINT",
                        index_group=constants.INDEXGROUP_DATA,
                        index_offset=1))
        with self.plc:
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

    def test_get_all_symbols_empty(self):
        with self.plc:
            self.assertEqual(len(self.plc.get_all_symbols()), 0)

    def test_get_all_symbols_single(self):
        self.handler.add_variable(
            PLCVariable("i", 1, constants.ADST_INT16, symbol_type="INT", index_group=123, index_offset=0))
        with self.plc:
            symbols = self.plc.get_all_symbols()
            self.assertEqual(len(symbols), 1)
            self.assertEqual(symbols[0].index_group, 123)

    def test_read_by_name_without_datatype(self) -> None:
        """Test read by name without passing the datatype."""
        # create variable on testserver
        self.handler.add_variable(PLCVariable("test_var", 42, constants.ADST_INT16, "INT"))
        with self.plc:
            # read twice to show caching
            read_value = self.plc.read_by_name("test_var")
            read_value2 = self.plc.read_by_name("test_var")
            self.assertEqual(read_value, 42)
            self.assertEqual(read_value2, 42)

            # read without caching
            read_value = self.plc.read_by_name("test_var", cache_symbol_info=False)
            self.assertEqual(read_value, 42)

    def test_write_by_name_without_datatype(self) -> None:
        """Test read by name without passing the datatype."""
        # create variable on testserver
        self.handler.add_variable(PLCVariable("test_var", 0, constants.ADST_INT16, "INT"))
        with self.plc:
            # write twice to show caching
            self.plc.write_by_name("test_var", 42)
            self.plc.write_by_name("test_var", 42)
            read_value = self.plc.read_by_name("test_var")
            self.assertEqual(read_value, 42)

            # write without caching
            self.plc.write_by_name("test_var", 43, cache_symbol_info=False)
            read_value = self.plc.read_by_name("test_var")
            self.assertEqual(read_value, 43)

    def test_write_list_by_name_with_structure(self):
        """Test write_list_by_name with structure definition"""
        self.handler.add_variable(
            PLCVariable("TestStructure", b"\x01\x00", constants.ADST_INT16, symbol_type="TestStructure"))
        self.handler.add_variable(PLCVariable("TestVar", 0, constants.ADST_UINT8, "USINT"))
        variables = ["TestStructure", "TestVar"]
        structure_defs = {"TestStructure": (("xVar", pyads.PLCTYPE_INT, 1),)}
        data = {
            "TestStructure": {"xVar": 11},
            "TestVar": 22,
        }

        with self.plc:
            errors = self.plc.write_list_by_name(data, cache_symbol_info=False, structure_defs=structure_defs)

        requests = self.test_server.request_history
        self.assertEqual(len(requests), 3)

        # Assert that all commands are read write - 2x symbol info, 1x sum write
        for request in requests:
            self.assert_command_id(request, constants.ADSCOMMAND_READWRITE)

        self.assertEqual(errors, {v: "no error" for v in variables})

        with self.plc:
            written_data = self.plc.read_list_by_name(variables, cache_symbol_info=False,
                                                      structure_defs=structure_defs)
        self.assertEqual(data, written_data)

    def test_read_device_info(self):
        """Test read_device_info for AdvancedHandler."""
        with self.plc:
            name, version = self.plc.read_device_info()
            self.assertEqual(name, "TestServer")
            self.assertEqual(version.build, 3)

    def test_read_state(self):
        """Test read_state for AdvancedHandler."""
        with self.plc:
            state = self.plc.read_state()
            self.assertEqual(state[0], constants.ADSSTATE_RUN)

    def test_write_control(self):
        """Test write_control for AdvancedHandler."""
        with self.plc:
            self.plc.write_control(constants.ADSSTATE_IDLE, 0, 0, constants.PLCTYPE_INT)

    def test_read_wstring(self):
        """Test for proper WSTRING handling"""
        # add WSTRING variable containing 'Überraschung'
        expected1 = "Überraschung"
        expected2 = "hello world"

        var = PLCVariable(
            "wstr",
            expected1.encode("utf-16-le") + b"\x00\x00",
            constants.ADST_WSTRING, f"WSTRING({len(expected1)})"
        )
        self.handler.add_variable(var)

        with self.plc:
            # simple read by name
            self.assertEqual(self.plc.read_by_name("wstr"), expected1)
            # read list by name
            self.assertEqual(self.plc.read_list_by_name(["wstr"])["wstr"], expected1)
            # write by name
            self.plc.write_by_name("wstr", expected2)
            self.assertEqual(self.plc.read_by_name("wstr"), expected2)
            # write list by name
            self.plc.write_list_by_name({"wstr": expected1})
            self.assertEqual(self.plc.read_by_name("wstr"), expected1)

            # read/write
            self.assertEqual(
                self.plc.read_write(
                    var.index_group, var.index_offset, pyads.PLCTYPE_WSTRING, expected2, pyads.PLCTYPE_WSTRING
                ), expected1
            )
            self.assertEqual(self.plc.read_by_name("wstr"), expected2)

    def test_read_write_list_wstr_array(self):

        expected_string_array = ["hello", "world", "", ""]

        # Set up the WString array
        w_string_char_size = 20
        w_string_element_size = (w_string_char_size * 2) + 2
        w_string_bytes = len(expected_string_array)*(w_string_element_size*[0])
        for i, element in enumerate(expected_string_array):
            current_offset = w_string_element_size * i
            w_string_bytes[current_offset: ((2*len(element)) + 2)] = element.encode("utf-16-le") + b"\x00\x00"

        # Add to test plc
        self.handler.add_variable(PLCVariable(
            name = "wstr_test_array", 
            value = bytes(w_string_bytes), 
            ads_type = constants.ADST_WSTRING, 
            symbol_type = f"WSTRING({w_string_char_size})"))


        # Read variable
        with self.plc:
            read_values = self.plc.read_list_by_name(["wstr_test_array"])

        # Expected result
        expected_result = {
            "wstr_test_array": expected_string_array
        }

        self.assertEqual(read_values, expected_result)

        # Modify the value
        expected_string_array[0] = "howdy"

        # Write variable
        with self.plc:
            self.plc.write_list_by_name({"wstr_test_array": expected_string_array})

        # Read variable again
        with self.plc:
            read_values = self.plc.read_list_by_name(["wstr_test_array"])

        # Expected result
        expected_result = {
            "wstr_test_array": expected_string_array
        }

        self.assertEqual(read_values, expected_result)


    def test_read_write_list_str_array(self):

        expected_string_array = ["hello", "world", "", ""]

        # Set up the WString array
        string_char_size = 20
        string_element_size = string_char_size + 1
        string_bytes = len(expected_string_array)*(string_element_size*[0])
        for i, element in enumerate(expected_string_array):
            current_offset = string_element_size * i
            string_bytes[current_offset: ((len(element)) + 1)] = element.encode("utf-8") + b"\x00"

        # Add to test plc
        self.handler.add_variable(PLCVariable(
            name = "str_test_array", 
            value = bytes(string_bytes), 
            ads_type = constants.ADST_STRING, 
            symbol_type = f"STRING({string_char_size})"))


        # Read variable
        with self.plc:
            read_values = self.plc.read_list_by_name(["str_test_array"])

        # Expected result
        expected_result = {
            "str_test_array": expected_string_array
        }

        self.assertEqual(read_values, expected_result)

        # Modify the value
        expected_string_array[0] = "howdy"

        # Write variable
        with self.plc:
            self.plc.write_list_by_name({"str_test_array": expected_string_array})

        # Read variable again
        with self.plc:
            read_values = self.plc.read_list_by_name(["str_test_array"])

        # Expected result
        expected_result = {
            "str_test_array": expected_string_array
        }

        self.assertEqual(read_values, expected_result)


    def test_read_write_list_int_array(self):
        expected_int_array = [123, 456, 789]

        int_array_bytes = bytearray(ctypes.sizeof(constants.PLCTYPE_INT) * len(expected_int_array))

        struct.pack_into(
            "<" + "h" * len(expected_int_array),
            int_array_bytes,
            0,
            *expected_int_array,
        )


        # Add to test plc
        self.handler.add_variable(PLCVariable(
            name = "int_test_array", 
            value = bytes(int_array_bytes), 
            ads_type = constants.ADST_INT16, 
            symbol_type = f"INT"))


        # Read variable
        with self.plc:
            read_values = self.plc.read_list_by_name(["int_test_array"])

        # Expected result
        expected_result = {
            "int_test_array": expected_int_array
        }

        self.assertEqual(expected_result, read_values)

        # Modify the value
        expected_int_array[0] = 321

        # Write variable
        with self.plc:
            self.plc.write_list_by_name({"int_test_array": expected_int_array})

        # Read variable again
        with self.plc:
            read_values = self.plc.read_list_by_name(["int_test_array"])

        # Expected result
        expected_result = {
            "int_test_array": expected_int_array
        }

        self.assertEqual(read_values, expected_result)


    def test_read_write_list_real_array(self):
        expected_real_array = [123.4, 456.7, 789.1]

        real_array_bytes = bytearray(ctypes.sizeof(constants.PLCTYPE_REAL) * len(expected_real_array))

        print(ctypes.sizeof(constants.PLCTYPE_REAL))

        struct.pack_into(
            "<" + "f" * len(expected_real_array),
            real_array_bytes,
            0,
            *expected_real_array,
        )

        # Add to test plc
        self.handler.add_variable(PLCVariable(
            name = "real_test_array", 
            value = bytes(real_array_bytes), 
            ads_type = constants.ADST_REAL32, 
            symbol_type = f"REAL"))


        # Read variable
        with self.plc:
            read_values = self.plc.read_list_by_name(["real_test_array"])

        # Verify result to 1dp 
        for i, value in enumerate(read_values["real_test_array"]):
            self.assertEqual(expected_real_array[i], round(value, 1))


        # Modify the value
        expected_real_array[0] = 432.1

        # Write variable
        with self.plc:
            self.plc.write_list_by_name({"real_test_array": expected_real_array})

        # Read variable again
        with self.plc:
            read_values = self.plc.read_list_by_name(["real_test_array"])

        # Verify result to 1dp 
        for i, value in enumerate(read_values["real_test_array"]):
            self.assertEqual(expected_real_array[i], round(value, 1))

    def test_wstring_struct(self):
        wstring_structure_def = (
            ("name", pyads.PLCTYPE_WSTRING, 1),
            ("value", pyads.PLCTYPE_INT, 1),
        )

        wstring_array_structure_def = (
            ("name", pyads.PLCTYPE_WSTRING, 2),
            ("value", pyads.PLCTYPE_INT, 1),
        )

        wstring_values = OrderedDict([
            ("name", "foo bar"),
            ("value", 24),
        ])

        wstring_array_values = OrderedDict([
            ("name", ["foo bar", "Klaus Günter"]),
            ("value", 24),
        ])

        # build structure value
        data = "hällo world".encode("utf-16-le") + 2 * b"\x00"
        byte_list = list(data) + (2 * (PLC_DEFAULT_STRING_SIZE + 1) - len(data)) * [0]
        byte_list += [10, 0]

        wstring_var = PLCVariable(
            "wstring_struct",
            value=bytes(byte_list),
            ads_type=None,
            symbol_type="S_WSTRING"
        )
        self.handler.add_variable(wstring_var)

        data = "hällo world".encode("utf-16-le") + 2 * b"\x00"
        byte_list = list(data) + (2 * (PLC_DEFAULT_STRING_SIZE + 1) - len(data)) * [0]
        data = "foo bar".encode("utf-16-le") + 2 * b"\x00"
        byte_list += list(data) + (2 * (PLC_DEFAULT_STRING_SIZE + 1) - len(data)) * [0]
        byte_list += [10, 0]
        wstring_array_var = PLCVariable(
            "wstring_array_struct",
            value=bytes(byte_list),
            ads_type=None,
            symbol_type="S_WSTRING_ARRAY"
        )
        self.handler.add_variable(wstring_array_var)

        with self.plc:
            # read WSTRING struct
            val = self.plc.read_structure_by_name("wstring_struct", wstring_structure_def)
            self.assertEqual({"name": "hällo world", "value": 10}, val)

            # write WSTRING struct
            self.plc.write_structure_by_name("wstring_struct", wstring_values, wstring_structure_def)
            val = self.plc.read_structure_by_name("wstring_struct", wstring_structure_def)
            self.assertEqual(wstring_values, val)

            # read struct with WSTRING array
            val = self.plc.read_structure_by_name("wstring_array_struct", wstring_array_structure_def)
            self.assertEqual({"name": ["hällo world", "foo bar"], "value": 10}, val)

            # write struct with WSTRING array
            self.plc.write_structure_by_name("wstring_array_struct", wstring_array_values, wstring_array_structure_def)
            val = self.plc.read_structure_by_name("wstring_array_struct", wstring_array_structure_def)
            self.assertEqual(wstring_array_values, val)


if __name__ == "__main__":
    unittest.main()
