"""Tests for decoded notification subscriptions (Connection.subscribe)."""
import ctypes
import unittest

from pyads import constants
from pyads.subscription import resolve_notification_type


class ResolverTestCase(unittest.TestCase):
    """Type resolution from symbol info (no server needed).

    Rows mirror symbol entries observed on a real TwinCAT PLC.
    """

    def assertResolves(self, symbol_type, data_type, size, expected_type, expected_size):
        plc_type, n = resolve_notification_type("X", symbol_type, data_type, size)
        self.assertIs(plc_type, expected_type)
        self.assertEqual(n, expected_size)

    def assertUnresolvable(self, symbol_type, data_type, size):
        with self.assertRaises(TypeError) as ctx:
            resolve_notification_type("GVL.x", symbol_type, data_type, size)
        self.assertIn("GVL.x", str(ctx.exception))
        self.assertIn("plc_datatype=", str(ctx.exception))

    def test_base_type(self):
        self.assertResolves("INT", constants.ADST_INT16, 2, constants.PLCTYPE_INT, 2)

    def test_bool(self):
        self.assertResolves("BOOL", constants.ADST_BIT, 1, constants.PLCTYPE_BOOL, 1)

    def test_enum_int16(self):
        self.assertResolves(
            "Tc3_BACnetRev14.E_BACnet_Priority", constants.ADST_INT16, 2,
            constants.PLCTYPE_INT, 2,
        )

    def test_enum_uint8(self):
        plc_type, n = resolve_notification_type(
            "X", "Tc3_BA2_Common.E_BA_PIDMode", constants.ADST_UINT8, 1
        )
        self.assertEqual(ctypes.sizeof(plc_type), 1)
        self.assertEqual(n, 1)

    def test_subrange(self):
        self.assertResolves("INT (2..100)", constants.ADST_INT16, 2, constants.PLCTYPE_INT, 2)

    def test_time_of_day(self):
        self.assertResolves("TIME_OF_DAY", constants.ADST_UINT32, 4, constants.PLCTYPE_UDINT, 4)

    def test_string_alias(self):
        self.assertResolves(
            "Tc3_XBA.T_BA_MedString", constants.ADST_STRING, 65, constants.PLCTYPE_STRING, 65
        )

    def test_sized_string(self):
        self.assertResolves("STRING(80)", constants.ADST_STRING, 81, constants.PLCTYPE_STRING, 81)

    def test_sized_wstring(self):
        self.assertResolves(
            "WSTRING(10)", constants.ADST_WSTRING, 22, constants.PLCTYPE_WSTRING, 22
        )

    def test_array_of_base_type(self):
        plc_type, n = resolve_notification_type(
            "X", "ARRAY [0..9] OF INT", constants.ADST_INT16, 20
        )
        self.assertTrue(issubclass(plc_type, ctypes.Array))
        self.assertIs(plc_type._type_, constants.PLCTYPE_INT)
        self.assertEqual(plc_type._length_, 10)
        self.assertEqual(n, 20)

    def test_alias_to_array_size_mismatch(self):
        self.assertUnresolvable("T_Arr", constants.ADST_INT16, 20)

    def test_array_of_strings(self):
        self.assertUnresolvable("ARRAY [0..11] OF STRING(80)", constants.ADST_STRING, 972)

    def test_multi_dimensional_array(self):
        self.assertUnresolvable("ARRAY [0..1,0..2] OF INT", constants.ADST_INT16, 12)

    def test_nested_array(self):
        self.assertUnresolvable("ARRAY [1..3] OF ARRAY [0..1] OF INT", constants.ADST_INT16, 12)

    def test_array_of_wstrings(self):
        self.assertUnresolvable("ARRAY [0..3] OF WSTRING(10)", constants.ADST_WSTRING, 88)

    def test_structure(self):
        self.assertUnresolvable("ST_HA_Bath", constants.ADST_BIGTYPE, 64)

    def test_string_without_size(self):
        self.assertUnresolvable("STRING(80)", constants.ADST_STRING, 0)


if __name__ == "__main__":
    unittest.main()
