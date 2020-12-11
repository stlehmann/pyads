"""Test AdsSymbol class.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2020-11-16

"""
import time
import unittest
import pyads
from pyads.testserver import AdsTestServer, AmsPacket, AdvancedHandler, \
    PLCVariable
from pyads import constants, AdsSymbol

# These are pretty arbitrary
TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
TEST_SERVER_IP_ADDRESS = "127.0.0.1"
TEST_SERVER_AMS_PORT = pyads.PORT_SPS1


class AdsSymbolTestCase(unittest.TestCase):
    """Testcase for ADS symbol class"""

    @classmethod
    def setUpClass(cls):
        # type: () -> None
        """Setup the ADS testserver."""
        cls.handler = AdvancedHandler()
        cls.test_server = AdsTestServer(handler=cls.handler, logging=False)
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

        # Clear test server and handler
        self.test_server.request_history = []
        self.handler.reset()

        # Create PLC variable that is added by default
        self.test_var = PLCVariable(
            'TestDouble', ads_type=constants.ADST_REAL64, type_name='LREAL')
        self.handler.add_variable(self.test_var)

        self.plc = pyads.Connection(
            TEST_SERVER_AMS_NET_ID, TEST_SERVER_AMS_PORT,
            TEST_SERVER_IP_ADDRESS
        )

    def assertAdsRequestsCount(self, expected):
        real = len(self.test_server.request_history)
        self.assertEqual(
            expected,
            real,
            msg='Expected {} requests, but {} have been made'.format(
                expected, real)
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
        self.assertEqual(self.test_var.type_name, symbol.type_name)

        self.assertAdsRequestsCount(1)  # Only a single READWRITE must have
        # been made

    def test_type_resolve(self):
        """Test if PLCTYPE is resolved correctly"""
        with self.plc:

            symbol1 = AdsSymbol(self.plc, 'NonExistentVar', 123, 0,
                                constants.PLCTYPE_UDINT)
            self.assertEqual(constants.PLCTYPE_UDINT, symbol1.plc_type)
            # Human-readable cannot be found:
            self.assertEqual('PyCSimpleType', symbol1.type_name)

            symbol2 = AdsSymbol(self.plc, 'NonExistentVar', 123, 0,
                                constants.ADST_UINT32)
            self.assertEqual(constants.PLCTYPE_UDINT, symbol2.plc_type)
            # Human-readable cannot be found:
            self.assertEqual('PyCSimpleType', symbol2.type_name)

            symbol3 = AdsSymbol(self.plc, 'NonExistentVar', 123, 0,
                                'UDINT')
            self.assertEqual(constants.PLCTYPE_UDINT, symbol3.plc_type)
            self.assertEqual('UDINT', symbol3.type_name)

        self.assertAdsRequestsCount(0)  # No requests

    def test_init_manual(self):
        """Test symbol without lookup"""
        with self.plc:

            # Create symbol while providing everything:
            symbol = AdsSymbol(self.plc,
                               name=self.test_var.name,
                               index_group=self.test_var.index_group,
                               index_offset=self.test_var.index_offset,
                               type_hint=self.test_var.plc_type)

            self.assertAdsRequestsCount(0)  # No requests yet

            self.plc.write(
                self.test_var.index_group, self.test_var.index_offset, 12.3,
                self.test_var.plc_type)

            self.assertEqual(12.3, symbol.value)

        self.assertAdsRequestsCount(2)  # Only a WRITE followed by a READ

    def test_read(self):
        """Test symbol value reading"""

        with self.plc:

            self.plc.write(
                self.test_var.index_group, self.test_var.index_offset, 420.0,
                self.test_var.plc_type)

            symbol = AdsSymbol(self.plc, name=self.test_var.name)

            self.assertEqual(420.0, symbol.value)

        self.assertAdsRequestsCount(3)  # WRITE, READWRITE for info and
        # final read

    def test_write(self):
        """Test symbol value writing"""
        with self.plc:

            symbol = AdsSymbol(self.plc, name=self.test_var.name)

            symbol.value = 3.14  # Write

            r_value = self.plc.read(
                self.test_var.index_group, self.test_var.index_offset,
                self.test_var.plc_type)

            self.assertEqual(3.14, r_value)

        self.assertAdsRequestsCount(3)  # READWRITE for info, WRITE and
        # test read

    def test_get_symbol(self):
        """Test symbol by Connection method"""
        with self.plc:
            symbol = self.plc.get_symbol(self.test_var.name)

        # Verify looked up info
        self.assertEqual(self.test_var.name, symbol.name)

        self.assertAdsRequestsCount(1)  # Only a single READWRITE must have
        # been made


if __name__ == "__main__":
    unittest.main()

