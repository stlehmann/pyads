"""Test ADS module.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:58
:last modified by: Stefan Lehmann
:last modified time: 2018-07-19 09:42:16

"""
import pyads
from pyads import AmsAddr
from pyads.utils import platform_is_linux
import unittest


class AdsTest(unittest.TestCase):
    """Unittests for ADS module."""

    def test_AmsAddr(self):
        # type: () -> None
        """Test ams address - related functions."""
        netid = "5.33.160.54.1.1"
        port = 851

        # test default init values
        adr = AmsAddr()
        self.assertEqual(adr.netid, "0.0.0.0.0.0")
        self.assertEqual(adr.port, 0)

        # test given init values
        adr = AmsAddr(netid, port)
        self.assertEqual(adr.netid, netid)
        self.assertEqual(adr.port, port)

        # check if ams addr struct has been changed
        ams_addr_numbers = [x for x in adr._ams_addr.netId.b]
        netid_numbers = [int(x) for x in netid.split(".")]
        self.assertEqual(len(ams_addr_numbers), len(netid_numbers))
        for i in range(len(ams_addr_numbers)):
            self.assertEqual(ams_addr_numbers[i], netid_numbers[i])
        self.assertEqual(adr.port, adr._ams_addr.port)

    def test_set_local_address(self):
        # type: () -> None
        """Test set_local_address function.

        Skip test on Windows as set_local_address is not supported for Windows.

        """
        if platform_is_linux():
            pyads.open_port()
            org_adr = pyads.get_local_address()
            self.assertIsNotNone(org_adr)
            org_netid = org_adr.netid

            # Set netid to specific value
            pyads.set_local_address("0.0.0.0.1.5")
            netid = pyads.get_local_address().netid
            self.assertEqual(netid, "0.0.0.0.1.5")

            # Change netid by String
            pyads.set_local_address("0.0.0.0.1.6")
            netid = pyads.get_local_address().netid
            self.assertEqual(netid, "0.0.0.0.1.6")

            # Change netid by Struct
            pyads.set_local_address(org_adr.netIdStruct())
            netid = pyads.get_local_address().netid
            self.assertEqual(netid, org_netid)

            # Check raised error on short netid
            with self.assertRaises(ValueError):
                pyads.ads.set_local_address("1.2.3")

            # Check raised error on invalid netid
            with self.assertRaises(ValueError):
                pyads.set_local_address("1.2.3.a")

            # Check wrong netid datatype
            with self.assertRaises(AssertionError):
                pyads.set_local_address(123)

    def test_functions_with_closed_port(self):
        # type: () -> None
        """Test pyads functions with no open port."""
        pyads.open_port()
        adr = pyads.get_local_address()
        pyads.close_port()

        self.assertIsNotNone(adr)
        self.assertIsNone(pyads.get_local_address())
        self.assertIsNone(pyads.read_state(adr))
        self.assertIsNone(pyads.read_device_info(adr))
        self.assertIsNone(
            pyads.read_write(adr, 1, 2, pyads.PLCTYPE_INT, 1, pyads.PLCTYPE_INT)
        )
        self.assertIsNone(pyads.read(adr, 1, 2, pyads.PLCTYPE_INT))
        self.assertIsNone(pyads.read_by_name(adr, "hello", pyads.PLCTYPE_INT))
        self.assertIsNone(
            pyads.add_device_notification(
                adr, "test", pyads.NotificationAttrib(4), lambda x: x
            )
        )

    def test_set_timeout(self):
        # type: () -> None
        """Test timeout function."""
        pyads.open_port()
        self.assertIsNone(pyads.set_timeout(100))
        pyads.open_port()


if __name__ == "__main__":
    unittest.main()
