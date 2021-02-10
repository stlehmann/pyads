"""Test AdsSymbol class.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2020-11-16

"""
import time
import struct
from ctypes import sizeof, pointer
import unittest
import pyads
from pyads.testserver import AdsTestServer, AdvancedHandler, PLCVariable
from pyads import constants, AdsSymbol

from tests.test_connection_class import create_notification_struct

# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class AdsSymbolTestCase(unittest.TestCase):
    """Testcase for ADS symbol class"""

    @classmethod
    def setUpClass(cls):
        # type: () -> None
        """Setup the ADS test server."""
        cls.handler = AdvancedHandler()
        cls.test_server = AdsTestServer(handler=cls.handler, logging=False)
        cls.test_server.start()

        # wait a bit otherwise error might occur
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        # type: () -> None
        """Tear down the test server."""
        cls.test_server.stop()

        # wait a bit for server to shutdown
        time.sleep(1)

    def setUp(self):
        # type: () -> None
        """Establish connection to the test server."""

        # Clear test server and handler
        self.test_server.request_history = []
        self.handler.reset()

        # Create PLC variable that is added by default
        self.test_var = PLCVariable(
            "TestDouble", ads_type=constants.ADST_REAL64, symbol_type="LREAL"
        )
        self.test_var.comment = "Some variable of type double"
        self.handler.add_variable(self.test_var)

        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT, TEST_SERVER_IP_ADDRESS
        )

    def assertAdsRequestsCount(self, expected):
        real = len(self.test_server.request_history)
        self.assertEqual(
            expected,
            real,
            msg="Expected {} requests, but {} have been made".format(expected, real),
        )

    def test_init_by_name(self):
        """Test symbol creation by name"""
        with self.plc:
            symbol = AdsSymbol(self.plc, name=self.test_var.name)

        # Verify looked up info
        self.assertEqual(self.test_var.name, symbol.name)
        self.assertEqual(self.test_var.index_group, symbol.index_group)
        self.assertEqual(self.test_var.index_offset, symbol.index_offset)
        self.assertEqual(self.test_var.plc_type, symbol.plc_type)
        self.assertEqual(self.test_var.symbol_type, symbol.symbol_type)
        self.assertEqual(self.test_var.comment, symbol.comment)

        self.assertAdsRequestsCount(1)  # Only a single READWRITE must have
        # been made

    def test_init_by_name_array(self):
        """Test symbol creation when it's an array"""

        var = PLCVariable(
            "ArrayVar",
            ads_type=constants.ADST_INT16,  # dataType does not represent
            # array unfortunately
            symbol_type="ARRAY [1..5] OF INT",  # Array looks like this in PLC
        )
        var.plc_type = constants.PLCTYPE_ARR_INT(5)  # Have to do this
        # manually
        self.handler.add_variable(var)

        self.plc.open()

        symbol = AdsSymbol(self.plc, name=var.name)

        # Verify looked up info
        self.assertEqual(var.name, symbol.name)
        self.assertEqual(var.index_group, symbol.index_group)
        self.assertEqual(var.index_offset, symbol.index_offset)
        self.assertEqual(var.plc_type, symbol.plc_type)
        self.assertEqual(var.symbol_type, symbol.symbol_type)
        self.assertIsNone(symbol.comment)

        my_list = symbol.read()

        self.assertIsInstance(my_list, list)
        self.assertEqual(5, len(my_list))

        my_list[4] = 420

        symbol.write(my_list)  # Modify array

        my_list2 = symbol.read()  # Read again

        self.assertEqual(my_list, my_list2)

        self.assertAdsRequestsCount(4)  # A READWRITE (for info), READ,
        # WRITE AND a READ again

    def test_init_by_name_matrix_style(self):
        """Test symbol creation when it's an array denoted as matrix

        This is how an array originating from Simulink could look like.
        """

        var = PLCVariable(
            "ArrayVar",
            ads_type=0,
            symbol_type="matrix_21_int8_T",  # Simulink array looks like this
        )
        var.plc_type = constants.PLCTYPE_ARR_SINT(21)  # Have to do this
        # manually
        var.index_group = 123
        var.index_offset = 100
        self.handler.add_variable(var)

        self.plc.open()

        symbol = AdsSymbol(
            self.plc,
            name=var.name,
            index_group=var.index_group,
            index_offset=var.index_offset,
            symbol_type=var.symbol_type,
        )  # No lookup

        # Verify looked up info
        self.assertEqual(var.plc_type, symbol.plc_type)
        self.assertEqual(var.symbol_type, symbol.symbol_type)

        self.assertAdsRequestsCount(0)  # No requests

    def test_init_missing_datatype(self):
        """Test symbol creation when integer datatype is missing"""

        # Modify variable type
        self.test_var.ads_type = 0
        self.test_var.plc_type = constants.PLCTYPE_SINT
        self.test_var.symbol_type = "SINT"
        # Variable is reference to database entry, so no saving required

        with self.plc:
            symbol = AdsSymbol(self.plc, name=self.test_var.name)

        # Verify looked up info
        self.assertEqual(self.test_var.plc_type, symbol.plc_type)
        self.assertEqual(self.test_var.symbol_type, symbol.symbol_type)

        self.assertAdsRequestsCount(1)  # Only a single READWRITE must have
        # been made

    def test_init_invalid(self):
        """Test symbol creation with missing info"""
        with self.plc:

            with self.assertRaises(ValueError):
                AdsSymbol(
                    self.plc,
                    index_group=self.test_var.index_group,
                    index_offset=self.test_var.index_offset,
                )

    def test_repr(self):
        """Test debug string"""
        with self.plc:
            symbol = AdsSymbol(self.plc, name=self.test_var.name)
            text = str(symbol)
            self.assertIn(self.test_var.name, text)
            self.assertIn(self.test_var.symbol_type, text)  # Make sure name
            # and type are printed

    def test_type_resolve(self):
        """Test if PLCTYPE is resolved correctly"""
        with self.plc:

            symbol_str = AdsSymbol(self.plc, "NonExistentVar", 123, 0, "UDINT")
            self.assertEqual(constants.PLCTYPE_UDINT, symbol_str.plc_type)
            self.assertEqual("UDINT", symbol_str.symbol_type)

            symbol_missing = AdsSymbol(
                self.plc, "NonExistentVar", 123, 0, "INCORRECT_TYPE"
            )
            self.assertIsNone(symbol_missing.plc_type)

        self.assertAdsRequestsCount(0)  # No requests

    def test_init_manual(self):
        """Test symbol without lookup"""
        with self.plc:

            # Create symbol while providing everything:
            symbol = AdsSymbol(
                self.plc,
                name=self.test_var.name,
                index_group=self.test_var.index_group,
                index_offset=self.test_var.index_offset,
                symbol_type=self.test_var.symbol_type,
            )

            self.assertAdsRequestsCount(0)  # No requests yet

            self.plc.write(
                self.test_var.index_group,
                self.test_var.index_offset,
                12.3,
                self.test_var.plc_type,
            )

            self.assertEqual(12.3, symbol.read())

        self.assertAdsRequestsCount(2)  # Only a WRITE followed by a READ

    def test_init_invalid_type(self):
        """Test symbol lookup when type cannot be found

        There was a read/write check that verifies the plc_typ was not None,
        but this was removed.
        """

        var = PLCVariable(
            name="UnknownType", ads_type=0, symbol_type="non_existent_type"
        )
        var.index_group = 123
        var.index_offset = 100
        var.plc_type = constants.PLCTYPE_BYTE  # Set to something real

        self.handler.add_variable(var)

        with self.plc:

            # Create symbol while providing everything:
            symbol = AdsSymbol(self.plc, name=var.name)

            self.assertEqual(var.symbol_type, symbol.symbol_type)
            self.assertIsNone(symbol.plc_type)

            # with self.assertRaises(ValueError) as cm:
            #     # Without type specified, it cannot read
            #     symbol.read()
            # self.assertIn('Cannot read or write', str(cm.exception))

            with self.assertRaises(TypeError) as cm:
                # Error is thrown inside pyads_ex
                symbol.read()
            self.assertIn("NoneType", str(cm.exception))

        self.assertAdsRequestsCount(1)  # Only a WRITE followed by a READ

    def test_read_write_errors(self):
        """Test read/write on invalid AdsSymbol

        There was a read/write check that verifies the plc_typ was not None,
        but this was removed.
        """

        symbol = AdsSymbol(self.plc, "MySymbol", 123, 0, "BYTE")

        with self.assertRaises(ValueError) as cm:
            symbol.read()  # Cannot read with unopened Connection
        self.assertIn("missing or closed Connection", str(cm.exception))

        self.plc.open()

        symbol.index_offset = None  # Set index to something invalid

        # with self.assertRaises(ValueError) as cm:
        #     symbol.read()  # Cannot read with invalid index
        # self.assertIn('invalid values for', str(cm.exception))

        with self.assertRaises(TypeError) as cm:
            symbol.read()  # Catch error inside pyads_ex
        self.assertIn("integer is required", str(cm.exception))

    def test_read(self):
        """Test symbol value reading"""

        with self.plc:

            self.plc.write(
                self.test_var.index_group,
                self.test_var.index_offset,
                420.0,
                self.test_var.plc_type,
            )

            symbol = AdsSymbol(self.plc, name=self.test_var.name)

            self.assertEqual(420.0, symbol.read())

        self.assertAdsRequestsCount(3)  # WRITE, READWRITE for info and
        # final read

    def test_write(self):
        """Test symbol value writing"""
        with self.plc:

            symbol = AdsSymbol(self.plc, name=self.test_var.name)

            symbol.write(3.14)  # Write

            r_value = self.plc.read(
                self.test_var.index_group,
                self.test_var.index_offset,
                self.test_var.plc_type,
            )

            self.assertEqual(3.14, r_value)

        self.assertAdsRequestsCount(3)  # READWRITE for info, WRITE and
        # test read

    def test_value(self):
        """Test the buffer property"""

        with self.plc:
            symbol = AdsSymbol(self.plc, name=self.test_var.name)

            symbol.value = 420.0  # Shouldn't change anything yet

            self.assertAdsRequestsCount(1)  # Only a READWRITE for info

            symbol.write()

            self.assertAdsRequestsCount(2)  # Written from buffer

            symbol.read()

            for i in range(10):
                custom_buffer = symbol.value

            self.assertEqual(420.0, symbol.value)

            self.assertAdsRequestsCount(3)  # Read only once

    def test_get_symbol(self):
        """Test symbol by Connection method"""
        with self.plc:
            symbol = self.plc.get_symbol(self.test_var.name)

        # Verify looked up info
        self.assertEqual(self.test_var.name, symbol.name)

        self.assertAdsRequestsCount(1)  # Only a single READWRITE must have
        # been made

    def test_add_notification(self):
        """Test notification registering"""

        def my_callback(*_):
            return

        with self.plc:

            symbol = self.plc.get_symbol(self.test_var.name)

            handles = symbol.add_device_notification(my_callback)
            symbol.del_device_notification(handles)

        self.assertAdsRequestsCount(3)  # READWRITE, ADDNOTE and DELNOTE

    def test_add_notification_delete(self):
        """Test notification registering"""

        def my_callback(*_):
            return

        self.plc.open()

        symbol = self.plc.get_symbol(self.test_var.name)

        symbol.add_device_notification(my_callback)
        # with `self.plc: ... ` without del_device_notification causes a
        # socket write error

        del symbol  # Force variable deletion

        self.assertAdsRequestsCount(3)  # READWRITE, ADDNOTE and DELNOTE

    def test_auto_update(self):
        """Test auto-update feature"""
        self.plc.open()

        symbol = self.plc.get_symbol(self.test_var.name)
        self.assertIsNone(symbol._auto_update_handle)

        symbol.auto_update = True
        self.assertIsNotNone(symbol._auto_update_handle)
        self.assertEqual(symbol.auto_update, True)

        # Simulate value callback
        notification = create_notification_struct(struct.pack("<d", 5334.1545))
        symbol._value_callback(
            pointer(notification),
            (self.test_var.index_group, self.test_var.index_offset),
        )
        self.assertEqual(symbol.value, 5334.1545)

        # test immediate writing to plc if auto_update is True
        symbol.value = 123.456
        r_value = self.plc.read(
            symbol.index_group,
            symbol.index_offset,
            symbol.plc_type,
        )
        self.assertEqual(symbol.value, r_value)

        symbol.auto_update = False
        self.assertIsNone(symbol._auto_update_handle)
        symbol.value = 0.0
        r_value = self.plc.read(
            symbol.index_group,
            symbol.index_offset,
            symbol.plc_type,
        )
        self.assertEqual(r_value, 123.456)



class TypesTestCase(unittest.TestCase):
    """Basic test to cover the PLCTYPE_ARR_* functions"""

    def assertSizeOf(self, target, num_bytes):
        self.assertEqual(
            sizeof(target),
            num_bytes,
            "The size in bytes ({}), is not "
            "like expected: {}".format(sizeof(target), num_bytes),
        )

    def test_arrays(self):
        n = 7
        self.assertSizeOf(constants.PLCTYPE_ARR_REAL(n), 4 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_LREAL(n), 8 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_BOOL(n), 1 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_INT(n), 2 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_UINT(n), 2 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_SHORT(n), 2 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_USHORT(n), 2 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_DINT(n), 4 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_UDINT(n), 4 * n)
        self.assertSizeOf(constants.PLCTYPE_ARR_USINT(n), 1 * n)


if __name__ == "__main__":
    unittest.main()
