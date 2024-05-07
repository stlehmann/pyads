"""Test ADS module.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on: 2018-06-11 18:15:58

"""
import pyads
from pyads import AmsAddr
from pyads.utils import platform_is_linux
from collections import OrderedDict
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

    def test_set_timeout(self):
        # type: () -> None
        """Test timeout function."""
        pyads.open_port()
        self.assertIsNone(pyads.set_timeout(100))
        pyads.open_port()

    def test_size_of_structure(self):
        # type: () -> None
        """Test size_of_structure function"""
        # known structure size with defined string
        structure_def = (
            ("rVar", pyads.PLCTYPE_LREAL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 2, 35),
            ("rVar1", pyads.PLCTYPE_REAL, 4),
            ("iVar", pyads.PLCTYPE_DINT, 5),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("ivar2", pyads.PLCTYPE_UDINT, 6),
            ("iVar3", pyads.PLCTYPE_UINT, 7),
            ("iVar4", pyads.PLCTYPE_BYTE, 1),
            ("iVar5", pyads.PLCTYPE_SINT, 1),
            ("iVar6", pyads.PLCTYPE_USINT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 4),
            ("iVar7", pyads.PLCTYPE_WORD, 1),
            ("iVar8", pyads.PLCTYPE_DWORD, 1),
        )
        self.assertEqual(pyads.size_of_structure(structure_def), 173)

        # test for PLC_DEFAULT_STRING_SIZE
        structure_def = (("sVar", pyads.PLCTYPE_STRING, 4),)
        self.assertEqual(
            pyads.size_of_structure(structure_def),
            (pyads.PLC_DEFAULT_STRING_SIZE + 1) * 4,
        )

        # tests for incorrect definitions
        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            ("rVar", 1, 1),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(RuntimeError):
            pyads.size_of_structure(structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            (pyads.PLCTYPE_REAL, 1),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(ValueError):
            pyads.size_of_structure(structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            ("rVar", pyads.PLCTYPE_REAL, ""),
            ("iVar", pyads.PLCTYPE_DINT, 1),
            ("iVar1", pyads.PLCTYPE_INT, 3),
        )
        with self.assertRaises(TypeError):
            pyads.size_of_structure(structure_def)

        # test another correct definition with array of structure
        structure_def = (
            ("bVar", pyads.PLCTYPE_BOOL, 1),
            ("rVar", pyads.PLCTYPE_LREAL, 3),
            ("sVar", pyads.PLCTYPE_STRING, 2),
            ("iVar", pyads.PLCTYPE_DINT, 10),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("bVar1", pyads.PLCTYPE_BOOL, 4),
        )
        self.assertEqual(pyads.size_of_structure(structure_def * 5), 1185)

        # test structure with WSTRING
        structure_def = (
            ("wstrVar", pyads.PLCTYPE_WSTRING, 1),
            ("iVar", pyads.PLCTYPE_INT, 1),
        )
        self.assertEqual(pyads.size_of_structure(structure_def), 164)

        # test structure with WSTRING with fixed length
        structure_def = (
            ("wstrVar", pyads.PLCTYPE_WSTRING, 1, 10),
            ("iVar", pyads.PLCTYPE_INT, 1),
        )
        self.assertEqual(pyads.size_of_structure(structure_def), 24)

        # test structure with WSTRING array
        structure_def = (
            ("wstrVar", pyads.PLCTYPE_WSTRING, 2),
            ("iVar", pyads.PLCTYPE_INT, 1),
        )
        self.assertEqual(pyads.size_of_structure(structure_def), 326)

        # test structure with WSTRING array with fixed length
        structure_def = (
            ("wstrVar", pyads.PLCTYPE_WSTRING, 2, 10),
            ("iVar", pyads.PLCTYPE_INT, 1),
        )
        self.assertEqual(pyads.size_of_structure(structure_def), 46)

        # known structure size with defined string
        substructure_def = (
            ("rVar", pyads.PLCTYPE_LREAL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 2, 35),
            ("rVar1", pyads.PLCTYPE_REAL, 4),
            ("iVar", pyads.PLCTYPE_DINT, 5),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("ivar2", pyads.PLCTYPE_UDINT, 6),
            ("iVar3", pyads.PLCTYPE_UINT, 7),
            ("iVar4", pyads.PLCTYPE_BYTE, 1),
            ("iVar5", pyads.PLCTYPE_SINT, 1),
            ("iVar6", pyads.PLCTYPE_USINT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 4),
            ("iVar7", pyads.PLCTYPE_WORD, 1),
            ("iVar8", pyads.PLCTYPE_DWORD, 1),
        )

        # test structure with array of nested structure
        structure_def = (
            ('iVar9', pyads.PLCTYPE_USINT, 1),
            ('structVar', substructure_def, 100),
        )        
        self.assertEqual(pyads.size_of_structure(structure_def), 17301)

    def test_dict_from_bytes(self):
        # type: () -> None
        """Test dict_from_bytes function"""
        # tests for known values
        structure_def = (
            ("rVar", pyads.PLCTYPE_LREAL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 2, 35),
            ("wsVar", pyads.PLCTYPE_WSTRING, 2, 10),
            ("rVar1", pyads.PLCTYPE_REAL, 4),
            ("iVar", pyads.PLCTYPE_DINT, 5),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("ivar2", pyads.PLCTYPE_UDINT, 6),
            ("iVar3", pyads.PLCTYPE_UINT, 7),
            ("iVar4", pyads.PLCTYPE_BYTE, 1),
            ("iVar5", pyads.PLCTYPE_SINT, 1),
            ("iVar6", pyads.PLCTYPE_USINT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 4),
            ("iVar7", pyads.PLCTYPE_WORD, 1),
            ("iVar8", pyads.PLCTYPE_DWORD, 1),
        )
        values = OrderedDict(
            [
                ("rVar", 1.11),
                ("sVar", ["Hello", "World"]),
                ("wsVar", ["foo", "bar"]),
                ("rVar1", [2.25, 2.25, 2.5, 2.75]),
                ("iVar", [3, 4, 5, 6, 7]),
                ("iVar1", [8, 9, 10]),
                ("ivar2", [11, 12, 13, 14, 15, 16]),
                ("iVar3", [17, 18, 19, 20, 21, 22, 23]),
                ("iVar4", 24),
                ("iVar5", 25),
                ("iVar6", 26),
                ("bVar", [True, False, True, False]),
                ("iVar7", 27),
                ("iVar8", 28),
            ]
        )
        # fmt: off
        bytes_list = [195, 245, 40, 92, 143, 194, 241, 63, 72, 101, 108, 108, 111,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 87, 111, 114, 108, 100, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 102, 0, 111, 0, 111, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 98, 0, 97, 0, 114,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16,
                      64, 0, 0, 16, 64, 0, 0, 32, 64, 0, 0, 48, 64, 3, 0, 0, 0, 4,
                      0, 0, 0, 5, 0, 0, 0, 6, 0, 0, 0, 7, 0, 0, 0, 8, 0, 9, 0, 10,
                      0, 11, 0, 0, 0, 12, 0, 0, 0, 13, 0, 0, 0, 14, 0, 0, 0, 15, 0,
                      0, 0, 16, 0, 0, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0,
                      23, 0, 24, 25, 26, 1, 0, 1, 0, 27, 0, 28, 0, 0, 0]
        # fmt: on
        self.assertEqual(values, pyads.dict_from_bytes(bytes_list, structure_def))

        values = OrderedDict(
            [
                ("rVar", 780245.5678),
                ("sVar", ["TwinCat works", "with Python using pyads"]),
                ("wsVar", ["hällo", "world"]),
                ("rVar1", [65.5, 89.75, 999.5, 55555.0]),
                ("iVar", [24567, -5678988, 12, -393, 0]),
                ("iVar1", [-20563, 32765, -1]),
                ("ivar2", [100001, 1234567890, 76, 582, 94034536, 2167]),
                ("iVar3", [2167, 987, 63000, 5648, 678, 2734, 43768]),
                ("iVar4", 200),
                ("iVar5", 127),
                ("iVar6", 255),
                ("bVar", [True, False, True, False]),
                ("iVar7", 45367),
                ("iVar8", 256000000),
            ]
        )
        # fmt: off
        bytes_list = [125, 174, 182, 34, 171, 207, 39, 65, 84, 119, 105, 110, 67,
                      97, 116, 32, 119, 111, 114, 107, 115, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 119, 105,
                      116, 104, 32, 80, 121, 116, 104, 111, 110, 32, 117, 115, 105,
                      110, 103, 32, 112, 121, 97, 100, 115, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 104, 0, 228, 0, 108, 0, 108, 0, 111, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 119, 0, 111, 0, 114, 0, 108, 0,
                      100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 131, 66, 0,
                      128, 179, 66, 0, 224, 121, 68, 0, 3, 89, 71, 247, 95, 0, 0, 116,
                      88, 169, 255, 12, 0, 0, 0, 119, 254, 255, 255, 0, 0, 0, 0, 173,
                      175, 253, 127, 255, 255, 161, 134, 1, 0, 210, 2, 150, 73, 76, 0,
                      0, 0, 70, 2, 0, 0, 104, 218, 154, 5, 119, 8, 0, 0, 119, 8, 219,
                      3, 24, 246, 16, 22, 166, 2, 174, 10, 248, 170, 200, 127, 255, 1,
                      0, 1, 0, 55, 177, 0, 64, 66, 15]
        # fmt: on
        self.assertEqual(values, pyads.dict_from_bytes(bytes_list, structure_def))

        # test for PLC_DEFAULT_STRING_SIZE
        structure_def = (
            ("iVar", pyads.PLCTYPE_INT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 1),
            ("wsVar", pyads.PLCTYPE_WSTRING, 1),
            ("iVar2", pyads.PLCTYPE_DINT, 1),
        )
        values = OrderedDict(
            [
                ("iVar", 32767),
                ("bVar", True),
                ("sVar", "Testing the default string size of 80"),
                ("wsVar", "Default WSTRING size is 160, it uses 2 Bytes a char"),
                ("iVar2", -25600000),
            ]
        )
        # fmt: off
        bytes_list = [255, 127, 1, 84, 101, 115, 116, 105, 110, 103, 32, 116, 104,
                      101, 32, 100, 101, 102, 97, 117, 108, 116, 32, 115, 116, 114,
                      105, 110, 103, 32, 115, 105, 122, 101, 32, 111, 102, 32, 56,
                      48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 68, 0, 101, 0, 102, 0, 97, 0, 117, 0, 108, 0, 116,
                      0, 32, 0, 87, 0, 83, 0, 84, 0, 82, 0, 73, 0, 78, 0, 71, 0, 32,
                      0, 115, 0, 105, 0, 122, 0, 101, 0, 32, 0, 105, 0, 115, 0, 32,
                      0, 49, 0, 54, 0, 48, 0, 44, 0, 32, 0, 105, 0, 116, 0, 32, 0,
                      117, 0, 115, 0, 101, 0, 115, 0, 32, 0, 50, 0, 32, 0, 66, 0, 121,
                      0, 116, 0, 101, 0, 115, 0, 32, 0, 97, 0, 32, 0, 99, 0, 104, 0,
                      97, 0, 114, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 96, 121, 254]
        # fmt: on
        self.assertEqual(values, pyads.dict_from_bytes(bytes_list, structure_def))

        # test another correct definition with array of structure
        values_list = [
            OrderedDict(
                [
                    ("iVar", 32767),
                    ("bVar", True),
                    ("sVar", "Testing the default string size of 80"),
                    ("wsVar", "Testing the default string size of 80"),
                    ("iVar2", -25600000),
                ]
            ),
            OrderedDict(
                [
                    ("iVar", -32768),
                    ("bVar", True),
                    ("sVar", "Another Test using the default string size of 80"),
                    ("wsVar", "Another Test using the default string size of 80"),
                    ("iVar2", -25600000),
                ]
            ),
            OrderedDict(
                [
                    ("iVar", 0),
                    ("bVar", False),
                    ("sVar", "Last Test String of Array"),
                    ("wsVar", "Last Test String of Array"),
                    ("iVar2", 1234567890),
                ]
            ),
        ]
        # fmt: off
        bytes_list = [255, 127, 1, 84, 101, 115, 116, 105, 110, 103, 32, 116,
                      104, 101, 32, 100, 101, 102, 97, 117, 108, 116, 32, 115,
                      116, 114, 105, 110, 103, 32, 115, 105, 122, 101, 32, 111,
                      102, 32, 56, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 84, 0, 101, 0, 115, 0,
                      116, 0, 105, 0, 110, 0, 103, 0, 32, 0, 116, 0, 104, 0,
                      101, 0, 32, 0, 100, 0, 101, 0, 102, 0, 97, 0, 117, 0, 108,
                      0, 116, 0, 32, 0, 115, 0, 116, 0, 114, 0, 105, 0, 110, 0,
                      103, 0, 32, 0, 115, 0, 105, 0, 122, 0, 101, 0, 32, 0, 111,
                      0, 102, 0, 32, 0, 56, 0, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 96, 121, 254, 0, 128, 1, 65, 110, 111, 116,
                      104, 101, 114, 32, 84, 101, 115, 116, 32, 117, 115, 105,
                      110, 103, 32, 116, 104, 101, 32, 100, 101, 102, 97, 117,
                      108, 116, 32, 115, 116, 114, 105, 110, 103, 32, 115, 105,
                      122, 101, 32, 111, 102, 32, 56, 48, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 65, 0, 110, 0, 111, 0, 116, 0, 104,
                      0, 101, 0, 114, 0, 32, 0, 84, 0, 101, 0, 115, 0, 116, 0,
                      32, 0, 117, 0, 115, 0, 105, 0, 110, 0, 103, 0, 32, 0, 116,
                      0, 104, 0, 101, 0, 32, 0, 100, 0, 101, 0, 102, 0, 97, 0,
                      117, 0, 108, 0, 116, 0, 32, 0, 115, 0, 116, 0, 114, 0,
                      105, 0, 110, 0, 103, 0, 32, 0, 115, 0, 105, 0, 122, 0,
                      101, 0, 32, 0, 111, 0, 102, 0, 32, 0, 56, 0, 48, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 96, 121, 254, 0, 0, 0, 76, 97,
                      115, 116, 32, 84, 101, 115, 116, 32, 83, 116, 114, 105,
                      110, 103, 32, 111, 102, 32, 65, 114, 114, 97, 121, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 76, 0, 97,
                      0, 115, 0, 116, 0, 32, 0, 84, 0, 101, 0, 115, 0, 116, 0,
                      32, 0, 83, 0, 116, 0, 114, 0, 105, 0, 110, 0, 103, 0, 32,
                      0, 111, 0, 102, 0, 32, 0, 65, 0, 114, 0, 114, 0, 97, 0,
                      121, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      210, 2, 150, 73]

        # fmt: on
        self.assertEqual(
            values_list, pyads.dict_from_bytes(bytes_list, structure_def, array_size=3)
        )

        # test for not default string and array of LREALs
        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 1, 20),
            ("rVar", pyads.PLCTYPE_LREAL, 4),
        )
        values = OrderedDict([("sVar", "pyads"), ("rVar", [1.11, 2.22, 3.33, 4.44])])
        # fmt: off
        bytes_list = [112, 121, 97, 100, 115, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 195, 245, 40, 92, 143, 194, 241, 63, 195, 245,
                      40, 92, 143, 194, 1, 64, 164, 112, 61, 10, 215, 163, 10, 64,
                      195, 245, 40, 92, 143, 194, 17, 64]
        # fmt: on
        self.assertEqual(values, pyads.dict_from_bytes(bytes_list, structure_def))

        # tests for incorrect definitions
        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            ("rVar", 1, 1),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(RuntimeError):
            pyads.dict_from_bytes([], structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            ("rVar", 1, 2),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(RuntimeError):
            pyads.dict_from_bytes([], structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            (pyads.PLCTYPE_REAL, 1),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(ValueError):
            pyads.dict_from_bytes([], structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 4),
            ("rVar", pyads.PLCTYPE_REAL, ""),
            ("iVar", pyads.PLCTYPE_DINT, 1),
            ("iVar1", pyads.PLCTYPE_INT, 3),
        )
        with self.assertRaises(TypeError):
            pyads.dict_from_bytes([], structure_def)

        # tests for known values
        substructure_def = (
            ("rVar", pyads.PLCTYPE_LREAL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 2, 35),
            ("wsVar", pyads.PLCTYPE_WSTRING, 2, 10),
            ("rVar1", pyads.PLCTYPE_REAL, 4),
            ("iVar", pyads.PLCTYPE_DINT, 5),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("ivar2", pyads.PLCTYPE_UDINT, 6),
            ("iVar3", pyads.PLCTYPE_UINT, 7),
            ("iVar4", pyads.PLCTYPE_BYTE, 1),
            ("iVar5", pyads.PLCTYPE_SINT, 1),
            ("iVar6", pyads.PLCTYPE_USINT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 4),
            ("iVar7", pyads.PLCTYPE_WORD, 1),
            ("iVar8", pyads.PLCTYPE_DWORD, 1),
        )
        subvalues = OrderedDict(
            [
                ("rVar", 1.11),
                ("sVar", ["Hello", "World"]),
                ("wsVar", ["foo", "bar"]),
                ("rVar1", [2.25, 2.25, 2.5, 2.75]),
                ("iVar", [3, 4, 5, 6, 7]),
                ("iVar1", [8, 9, 10]),
                ("ivar2", [11, 12, 13, 14, 15, 16]),
                ("iVar3", [17, 18, 19, 20, 21, 22, 23]),
                ("iVar4", 24),
                ("iVar5", 25),
                ("iVar6", 26),
                ("bVar", [True, False, True, False]),
                ("iVar7", 27),
                ("iVar8", 28),
            ]
        )
        # fmt: off
        subbytes_list = [195, 245, 40, 92, 143, 194, 241, 63, 72, 101, 108, 108, 111,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 87, 111, 114, 108, 100, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 102, 0, 111, 0, 111, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 98, 0, 97, 0, 114,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16,
                      64, 0, 0, 16, 64, 0, 0, 32, 64, 0, 0, 48, 64, 3, 0, 0, 0, 4,
                      0, 0, 0, 5, 0, 0, 0, 6, 0, 0, 0, 7, 0, 0, 0, 8, 0, 9, 0, 10,
                      0, 11, 0, 0, 0, 12, 0, 0, 0, 13, 0, 0, 0, 14, 0, 0, 0, 15, 0,
                      0, 0, 16, 0, 0, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0,
                      23, 0, 24, 25, 26, 1, 0, 1, 0, 27, 0, 28, 0, 0, 0]
        
        # test structure with array of nested structure
        structure_def = (
            ('iVar9', pyads.PLCTYPE_USINT, 1),
            ('structVar', substructure_def, 2),
        )
        values = OrderedDict(
            [
                ("iVar9", 29),
                ("structVar", [subvalues, subvalues,]),
            ]
        )
        # fmt: off
        bytes_list = [29] + subbytes_list + subbytes_list
        
        # fmt: on
        self.assertEqual(values, pyads.dict_from_bytes(bytes_list, structure_def))

    def test_bytes_from_dict(self) -> None:
        """Test bytes_from_dict function"""
        # tests for known values
        structure_def = (
            ("rVar", pyads.PLCTYPE_LREAL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 2, 35),
            ("wsVar", pyads.PLCTYPE_WSTRING, 2, 10),
            ("rVar1", pyads.PLCTYPE_REAL, 4),
            ("iVar", pyads.PLCTYPE_DINT, 5),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("ivar2", pyads.PLCTYPE_UDINT, 6),
            ("iVar3", pyads.PLCTYPE_UINT, 7),
            ("iVar4", pyads.PLCTYPE_BYTE, 1),
            ("iVar5", pyads.PLCTYPE_SINT, 1),
            ("iVar6", pyads.PLCTYPE_USINT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 4),
            ("iVar7", pyads.PLCTYPE_WORD, 1),
            ("iVar8", pyads.PLCTYPE_DWORD, 1),
        )
        values = OrderedDict(
            [
                ("rVar", 1.11),
                ("sVar", ["Hello", "World"]),
                ("wsVar", ["foo", "bar"]),
                ("rVar1", [2.25, 2.25, 2.5, 2.75]),
                ("iVar", [3, 4, 5, 6, 7]),
                ("iVar1", [8, 9, 10]),
                ("ivar2", [11, 12, 13, 14, 15, 16]),
                ("iVar3", [17, 18, 19, 20, 21, 22, 23]),
                ("iVar4", 24),
                ("iVar5", 25),
                ("iVar6", 26),
                ("bVar", [True, False, True, False]),
                ("iVar7", 27),
                ("iVar8", 28),
            ]
        )
        # fmt: off
        bytes_list = [195, 245, 40, 92, 143, 194, 241, 63, 72, 101, 108, 108, 111,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 87, 111, 114, 108, 100, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 102, 0, 111, 0, 111, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 98, 0, 97, 0, 114,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16,
                      64, 0, 0, 16, 64, 0, 0, 32, 64, 0, 0, 48, 64, 3, 0, 0, 0, 4,
                      0, 0, 0, 5, 0, 0, 0, 6, 0, 0, 0, 7, 0, 0, 0, 8, 0, 9, 0, 10,
                      0, 11, 0, 0, 0, 12, 0, 0, 0, 13, 0, 0, 0, 14, 0, 0, 0, 15, 0,
                      0, 0, 16, 0, 0, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0,
                      23, 0, 24, 25, 26, 1, 0, 1, 0, 27, 0, 28, 0, 0, 0]
        # fmt: on
        self.assertEqual(bytes_list, pyads.bytes_from_dict(values, structure_def))

        values = OrderedDict(
            [
                ("rVar", 780245.5678),
                ("sVar", ["TwinCat works", "with Python using pyads"]),
                ("wsVar", ["hällo", "world"]),
                ("rVar1", [65.5, 89.75, 999.5, 55555.0]),
                ("iVar", [24567, -5678988, 12, -393, 0]),
                ("iVar1", [-20563, 32765, -1]),
                ("ivar2", [100001, 1234567890, 76, 582, 94034536, 2167]),
                ("iVar3", [2167, 987, 63000, 5648, 678, 2734, 43768]),
                ("iVar4", 200),
                ("iVar5", 127),
                ("iVar6", 255),
                ("bVar", [True, False, True, False]),
                ("iVar7", 45367),
                ("iVar8", 256000000),
            ]
        )
        # fmt: off
        bytes_list = [125, 174, 182, 34, 171, 207, 39, 65, 84, 119, 105, 110, 67,
                      97, 116, 32, 119, 111, 114, 107, 115, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 119, 105,
                      116, 104, 32, 80, 121, 116, 104, 111, 110, 32, 117, 115, 105,
                      110, 103, 32, 112, 121, 97, 100, 115, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 104, 0, 228, 0, 108, 0, 108, 0, 111, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 119, 0, 111, 0, 114, 0, 108, 0,
                      100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 131, 66, 0,
                      128, 179, 66, 0, 224, 121, 68, 0, 3, 89, 71, 247, 95, 0, 0, 116,
                      88, 169, 255, 12, 0, 0, 0, 119, 254, 255, 255, 0, 0, 0, 0, 173,
                      175, 253, 127, 255, 255, 161, 134, 1, 0, 210, 2, 150, 73, 76, 0,
                      0, 0, 70, 2, 0, 0, 104, 218, 154, 5, 119, 8, 0, 0, 119, 8, 219,
                      3, 24, 246, 16, 22, 166, 2, 174, 10, 248, 170, 200, 127, 255, 1,
                      0, 1, 0, 55, 177, 0, 64, 66, 15]
        # fmt: on
        self.assertEqual(bytes_list, pyads.bytes_from_dict(values, structure_def))

        # test for PLC_DEFAULT_STRING_SIZE
        structure_def = (
            ("iVar", pyads.PLCTYPE_INT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 1),
            ("wsVar", pyads.PLCTYPE_WSTRING, 1),
            ("iVar2", pyads.PLCTYPE_DINT, 1),
        )
        values = OrderedDict(
            [
                ("iVar", 32767),
                ("bVar", True),
                ("sVar", "Testing the default string size of 80"),
                ("wsVar", "Default WSTRING size is 160, it uses 2 Bytes a char"),
                ("iVar2", -25600000),
            ]
        )
        # fmt: off
        bytes_list = [255, 127, 1, 84, 101, 115, 116, 105, 110, 103, 32, 116, 104,
                      101, 32, 100, 101, 102, 97, 117, 108, 116, 32, 115, 116, 114,
                      105, 110, 103, 32, 115, 105, 122, 101, 32, 111, 102, 32, 56,
                      48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 68, 0, 101, 0, 102, 0, 97, 0, 117, 0, 108, 0, 116,
                      0, 32, 0, 87, 0, 83, 0, 84, 0, 82, 0, 73, 0, 78, 0, 71, 0, 32,
                      0, 115, 0, 105, 0, 122, 0, 101, 0, 32, 0, 105, 0, 115, 0, 32,
                      0, 49, 0, 54, 0, 48, 0, 44, 0, 32, 0, 105, 0, 116, 0, 32, 0,
                      117, 0, 115, 0, 101, 0, 115, 0, 32, 0, 50, 0, 32, 0, 66, 0, 121,
                      0, 116, 0, 101, 0, 115, 0, 32, 0, 97, 0, 32, 0, 99, 0, 104, 0,
                      97, 0, 114, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 96, 121, 254]
        # fmt: on
        self.assertEqual(bytes_list, pyads.bytes_from_dict(values, structure_def))

        # test another correct definition with array of structure
        values_list = [
            OrderedDict(
                [
                    ("iVar", 32767),
                    ("bVar", True),
                    ("sVar", "Testing the default string size of 80"),
                    ("wsVar", "Testing the default string size of 80"),
                    ("iVar2", -25600000),
                ]
            ),
            OrderedDict(
                [
                    ("iVar", -32768),
                    ("bVar", True),
                    ("sVar", "Another Test using the default string size of 80"),
                    ("wsVar", "Another Test using the default string size of 80"),
                    ("iVar2", -25600000),
                ]
            ),
            OrderedDict(
                [
                    ("iVar", 0),
                    ("bVar", False),
                    ("sVar", "Last Test String of Array"),
                    ("wsVar", "Last Test String of Array"),
                    ("iVar2", 1234567890),
                ]
            ),
        ]
        # fmt: off
        bytes_list = [255, 127, 1, 84, 101, 115, 116, 105, 110, 103, 32, 116,
                      104, 101, 32, 100, 101, 102, 97, 117, 108, 116, 32, 115,
                      116, 114, 105, 110, 103, 32, 115, 105, 122, 101, 32, 111,
                      102, 32, 56, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 84, 0, 101, 0, 115, 0,
                      116, 0, 105, 0, 110, 0, 103, 0, 32, 0, 116, 0, 104, 0,
                      101, 0, 32, 0, 100, 0, 101, 0, 102, 0, 97, 0, 117, 0, 108,
                      0, 116, 0, 32, 0, 115, 0, 116, 0, 114, 0, 105, 0, 110, 0,
                      103, 0, 32, 0, 115, 0, 105, 0, 122, 0, 101, 0, 32, 0, 111,
                      0, 102, 0, 32, 0, 56, 0, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 96, 121, 254, 0, 128, 1, 65, 110, 111, 116,
                      104, 101, 114, 32, 84, 101, 115, 116, 32, 117, 115, 105,
                      110, 103, 32, 116, 104, 101, 32, 100, 101, 102, 97, 117,
                      108, 116, 32, 115, 116, 114, 105, 110, 103, 32, 115, 105,
                      122, 101, 32, 111, 102, 32, 56, 48, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 65, 0, 110, 0, 111, 0, 116, 0, 104,
                      0, 101, 0, 114, 0, 32, 0, 84, 0, 101, 0, 115, 0, 116, 0,
                      32, 0, 117, 0, 115, 0, 105, 0, 110, 0, 103, 0, 32, 0, 116,
                      0, 104, 0, 101, 0, 32, 0, 100, 0, 101, 0, 102, 0, 97, 0,
                      117, 0, 108, 0, 116, 0, 32, 0, 115, 0, 116, 0, 114, 0,
                      105, 0, 110, 0, 103, 0, 32, 0, 115, 0, 105, 0, 122, 0,
                      101, 0, 32, 0, 111, 0, 102, 0, 32, 0, 56, 0, 48, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 96, 121, 254, 0, 0, 0, 76, 97,
                      115, 116, 32, 84, 101, 115, 116, 32, 83, 116, 114, 105,
                      110, 103, 32, 111, 102, 32, 65, 114, 114, 97, 121, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 76, 0, 97,
                      0, 115, 0, 116, 0, 32, 0, 84, 0, 101, 0, 115, 0, 116, 0,
                      32, 0, 83, 0, 116, 0, 114, 0, 105, 0, 110, 0, 103, 0, 32,
                      0, 111, 0, 102, 0, 32, 0, 65, 0, 114, 0, 114, 0, 97, 0,
                      121, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      210, 2, 150, 73]
        # fmt: on
        self.assertEqual(
            bytes_list, pyads.bytes_from_dict(values_list, structure_def)
        )

        # test for not default string and array of LREALs
        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 1, 20),
            ("rVar", pyads.PLCTYPE_LREAL, 4),
        )
        values = OrderedDict([("sVar", "pyads"), ("rVar", [1.11, 2.22, 3.33, 4.44])])
        # fmt: off
        bytes_list = [112, 121, 97, 100, 115, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 195, 245, 40, 92, 143, 194, 241, 63, 195, 245,
                      40, 92, 143, 194, 1, 64, 164, 112, 61, 10, 215, 163, 10, 64,
                      195, 245, 40, 92, 143, 194, 17, 64]
        # fmt: on
        self.assertEqual(bytes_list, pyads.bytes_from_dict(values, structure_def))

        # tests for incorrect definitions
        values = OrderedDict([("sVar", "hi"), ("rVar", 12.3), ("iVar", 5)])
        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 1),
            ("rVar", 1, 1),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(RuntimeError):
            pyads.bytes_from_dict(values, structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 1),
            (pyads.PLCTYPE_REAL, 1),
            ("iVar", pyads.PLCTYPE_DINT, 1),
        )
        with self.assertRaises(ValueError):
            pyads.bytes_from_dict(values, structure_def)

        structure_def = (
            ("sVar", pyads.PLCTYPE_STRING, 1),
            ("rVar", pyads.PLCTYPE_REAL, ""),
            ("iVar", pyads.PLCTYPE_DINT, 1),
            ("iVar1", pyads.PLCTYPE_INT, 3),
        )
        with self.assertRaises(TypeError):
            pyads.bytes_from_dict(values, structure_def)

        # test for incorrect dict
        with self.assertRaises(KeyError):
            pyads.bytes_from_dict(OrderedDict(), structure_def)

                # tests for known values
        substructure_def = (
            ("rVar", pyads.PLCTYPE_LREAL, 1),
            ("sVar", pyads.PLCTYPE_STRING, 2, 35),
            ("wsVar", pyads.PLCTYPE_WSTRING, 2, 10),
            ("rVar1", pyads.PLCTYPE_REAL, 4),
            ("iVar", pyads.PLCTYPE_DINT, 5),
            ("iVar1", pyads.PLCTYPE_INT, 3),
            ("ivar2", pyads.PLCTYPE_UDINT, 6),
            ("iVar3", pyads.PLCTYPE_UINT, 7),
            ("iVar4", pyads.PLCTYPE_BYTE, 1),
            ("iVar5", pyads.PLCTYPE_SINT, 1),
            ("iVar6", pyads.PLCTYPE_USINT, 1),
            ("bVar", pyads.PLCTYPE_BOOL, 4),
            ("iVar7", pyads.PLCTYPE_WORD, 1),
            ("iVar8", pyads.PLCTYPE_DWORD, 1),
        )
        subvalues = OrderedDict(
            [
                ("rVar", 1.11),
                ("sVar", ["Hello", "World"]),
                ("wsVar", ["foo", "bar"]),
                ("rVar1", [2.25, 2.25, 2.5, 2.75]),
                ("iVar", [3, 4, 5, 6, 7]),
                ("iVar1", [8, 9, 10]),
                ("ivar2", [11, 12, 13, 14, 15, 16]),
                ("iVar3", [17, 18, 19, 20, 21, 22, 23]),
                ("iVar4", 24),
                ("iVar5", 25),
                ("iVar6", 26),
                ("bVar", [True, False, True, False]),
                ("iVar7", 27),
                ("iVar8", 28),
            ]
        )
        # fmt: off
        subbytes_list = [195, 245, 40, 92, 143, 194, 241, 63, 72, 101, 108, 108, 111,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 87, 111, 114, 108, 100, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 102, 0, 111, 0, 111, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 98, 0, 97, 0, 114,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16,
                      64, 0, 0, 16, 64, 0, 0, 32, 64, 0, 0, 48, 64, 3, 0, 0, 0, 4,
                      0, 0, 0, 5, 0, 0, 0, 6, 0, 0, 0, 7, 0, 0, 0, 8, 0, 9, 0, 10,
                      0, 11, 0, 0, 0, 12, 0, 0, 0, 13, 0, 0, 0, 14, 0, 0, 0, 15, 0,
                      0, 0, 16, 0, 0, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0,
                      23, 0, 24, 25, 26, 1, 0, 1, 0, 27, 0, 28, 0, 0, 0]
        
        # test structure with array of nested structure
        structure_def = (
            ('iVar9', pyads.PLCTYPE_USINT, 1),
            ('structVar', substructure_def, 2),
        )
        values = OrderedDict(
            [
                ("iVar9", 29),
                ("structVar", [subvalues, subvalues,]),
            ]
        )
        # fmt: off
        bytes_list = [29] + subbytes_list + subbytes_list
    
        # fmt: on
        self.assertEqual(bytes_list, pyads.bytes_from_dict(values, structure_def))

    def test_dict_slice_generator(self):
        """test _dict_slice_generator function."""
        test_dict = {
            "hi": 11,
            "how": 12,
            "are": 13,
            "you": 14,
            "doing": 15,
            "today": 16,
        }
        # split in three
        split_list = []
        for i in pyads.ads._dict_slice_generator(test_dict, 3):
            split_list.append(i)
        expected = [
            {"hi": 11, "how": 12, "are": 13},
            {"you": 14, "doing": 15, "today": 16},
        ]
        self.assertEqual(split_list, expected)
        split_list.clear()

        for i in pyads.ads._dict_slice_generator(test_dict, 2):
            split_list.append(i)
        expected = [
            {"hi": 11, "how": 12},
            {"are": 13, "you": 14,},
            {"doing": 15, "today": 16},
        ]
        self.assertEqual(split_list, expected)
        split_list.clear()

    def test_list_slice_generator(self):
        """test _list_slice_generator function."""
        test_list = ["hi", "how", "are", "you", "doing", "today"]
        # split in three
        split_list = []
        for i in pyads.ads._list_slice_generator(test_list, 3):
            split_list.append(i)
        expected = [
            ["hi", "how", "are"],
            ["you", "doing", "today"],
        ]
        self.assertEqual(split_list, expected)
        split_list.clear()

        for i in pyads.ads._list_slice_generator(test_list, 2):
            split_list.append(i)
        expected = [
            ["hi", "how"],
            ["are", "you"],
            ["doing", "today"],
        ]
        self.assertEqual(split_list, expected)
        split_list.clear()


if __name__ == "__main__":
    unittest.main()
