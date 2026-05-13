import struct
import time
import unittest

import pyads
from pyads import constants
from pyads.testserver import AdsTestServer, AdvancedHandler, PLCVariable
from pyads.typed_symbols import DataTypeEntry, SymbolEntry, TypeSystem


def _pack_len_string(value: str) -> bytes:
    return value.encode("windows-1252") + b"\x00"


def _pack_symbol_entry(
    name: str,
    type_name: str,
    index_group: int,
    index_offset: int,
    size: int,
    data_type: int,
    flags: int = 0,
    comment: str = "",
) -> bytes:
    name_b = name.encode("windows-1252")
    type_b = type_name.encode("windows-1252")
    comment_b = comment.encode("windows-1252")
    entry_length = 30 + len(name_b) + 1 + len(type_b) + 1 + len(comment_b) + 1
    return (
        struct.pack(
            "<IIIIIIHHH",
            entry_length,
            index_group,
            index_offset,
            size,
            data_type,
            flags,
            len(name_b),
            len(type_b),
            len(comment_b),
        )
        + _pack_len_string(name)
        + _pack_len_string(type_name)
        + _pack_len_string(comment)
    )


def _pack_datatype_entry(
    *,
    name: str,
    type_name: str,
    size: int,
    offset: int = 0,
    data_type: int = constants.ADST_BIGTYPE,
    flags: int = 0,
    comment: str = "",
    subitems: list[bytes] | None = None,
    array_info: list[tuple[int, int]] | None = None,
) -> bytes:
    subitems = subitems or []
    array_info = array_info or []

    name_b = name.encode("windows-1252")
    type_b = type_name.encode("windows-1252")
    comment_b = comment.encode("windows-1252")

    header = struct.pack(
        "<IIIIIIIIHHHHH",
        0,  # entry length placeholder
        1,  # version
        0,  # hash
        0,  # type hash
        size,
        offset,
        data_type,
        flags,
        len(name_b),
        len(type_b),
        len(comment_b),
        len(array_info),
        len(subitems),
    )

    body = _pack_len_string(name) + _pack_len_string(type_name) + _pack_len_string(comment)
    for lower_bound, elements in array_info:
        body += struct.pack("<II", lower_bound, elements)
    body += b"".join(subitems)

    entry = header + body
    return struct.pack("<I", len(entry)) + entry[4:]


def _build_test_blobs() -> tuple[bytes, bytes]:
    sensor_type = _pack_datatype_entry(
        name="TECH_TempSensor",
        type_name="TECH_TempSensor",
        size=36,
        subitems=[
            _pack_datatype_entry(
                name="temperature",
                type_name="REAL",
                size=4,
                offset=0,
                data_type=constants.ADST_REAL32,
            ),
            _pack_datatype_entry(
                name="valid",
                type_name="BOOL",
                size=1,
                offset=4,
                data_type=constants.ADST_BIT,
            ),
        ],
    )
    sensor_pointer_decl = _pack_datatype_entry(
        name="POINTER TO TECH_TempSensor",
        type_name="POINTER TO TECH_TempSensor",
        size=4,
        data_type=constants.ADST_UINT32,
        flags=0x00800000,
    )
    heizung_type = _pack_datatype_entry(
        name="FB_Heizung",
        type_name="FB_Heizung",
        size=8,
        subitems=[
            _pack_datatype_entry(
                name="Enable",
                type_name="BOOL",
                size=1,
                offset=0,
                data_type=constants.ADST_BIT,
            ),
            _pack_datatype_entry(
                name="Sollwert",
                type_name="REAL",
                size=4,
                offset=4,
                data_type=constants.ADST_REAL32,
            ),
        ],
    )

    datatype_blob = sensor_type + sensor_pointer_decl + heizung_type
    symbol_blob = (
        _pack_symbol_entry(
            name="MAIN.heizung",
            type_name="FB_Heizung",
            index_group=constants.INDEXGROUP_DATA,
            index_offset=1000,
            size=8,
            data_type=constants.ADST_BIGTYPE,
        )
        + _pack_symbol_entry(
            name="MAIN.tempSensorPtr",
            type_name="POINTER TO TECH_TempSensor",
            index_group=constants.INDEXGROUP_DATA,
            index_offset=1010,
            size=4,
            data_type=constants.ADST_UINT32,
        )
    )
    return symbol_blob, datatype_blob


def _load_fixture_type_system():
    symbol_blob, datatype_blob = _build_test_blobs()
    return TypeSystem.from_blobs(symbol_blob, datatype_blob)


class TestTypedSymbolsFixtures(unittest.TestCase):
    def test_fixture_symbol_and_datatype_counts(self):
        ts = _load_fixture_type_system()

        self.assertEqual(len(ts.symbols), 2)
        self.assertEqual(len(ts.datatypes), 3)

    def test_fixture_main_heizung_type(self):
        ts = _load_fixture_type_system()

        symbol = ts.get_symbol("MAIN.heizung")
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.type_name, "FB_Heizung")
        self.assertEqual(symbol.size, 8)

        datatype = ts.get_type("FB_Heizung")
        self.assertIsNotNone(datatype)
        self.assertEqual(datatype.size, 8)
        self.assertEqual(len(datatype.subitems), 2)

    def test_pointer_declarations_do_not_override_concrete_type(self):
        ts = _load_fixture_type_system()

        datatype = ts.get_type("TECH_TempSensor")
        self.assertIsNotNone(datatype)
        self.assertEqual(datatype.name, "TECH_TempSensor")
        self.assertEqual(datatype.size, 36)
        self.assertGreater(len(datatype.subitems), 0)


class TestTypedSymbolsDecoder(unittest.TestCase):
    def test_decode_scalar_and_string_values(self):
        ts = TypeSystem([], [])

        self.assertEqual(ts.decode_value("INT", struct.pack("<h", -12)), -12)
        self.assertAlmostEqual(
            ts.decode_value("REAL", struct.pack("<f", 12.5)),
            12.5,
        )
        self.assertEqual(ts.decode_value("STRING(10)", b"hello\x00xxxxx"), "hello")
        self.assertEqual(
            ts.decode_value("WSTRING(10)", "abc".encode("utf-16-le") + b"\x00\x00"),
            "abc",
        )

    def test_decode_struct_from_subitem_offsets(self):
        datatype = DataTypeEntry(
            entry_length=0,
            version=0,
            hash_value=0,
            type_hash_value=0,
            size=8,
            offset=0,
            data_type=65,
            flags=0,
            name="SampleStruct",
            type_name="",
            comment="",
            subitems=[
                DataTypeEntry(
                    entry_length=0,
                    version=0,
                    hash_value=0,
                    type_hash_value=0,
                    size=2,
                    offset=0,
                    data_type=2,
                    flags=0,
                    name="counter",
                    type_name="INT",
                    comment="",
                ),
                DataTypeEntry(
                    entry_length=0,
                    version=0,
                    hash_value=0,
                    type_hash_value=0,
                    size=4,
                    offset=4,
                    data_type=4,
                    flags=0,
                    name="value",
                    type_name="REAL",
                    comment="",
                ),
            ],
        )
        ts = TypeSystem([], [datatype])
        raw = struct.pack("<hxxf", 7, 3.25)

        decoded = ts.decode_value("SampleStruct", raw)

        self.assertEqual(decoded["counter"], 7)
        self.assertAlmostEqual(decoded["value"], 3.25)

    def test_decode_array_values(self):
        datatype = DataTypeEntry(
            entry_length=0,
            version=0,
            hash_value=0,
            type_hash_value=0,
            size=6,
            offset=0,
            data_type=2,
            flags=0,
            name="ARRAY [1..3] OF INT",
            type_name="INT",
            comment="",
            array_info=[(1, 3)],
        )
        ts = TypeSystem([], [datatype])
        raw = struct.pack("<hhh", 1, 2, 3)

        self.assertEqual(ts.decode_value("ARRAY [1..3] OF INT", raw), [1, 2, 3])

    def test_decode_pointer_as_opaque_address(self):
        ts = TypeSystem([], [])
        decoded = ts.decode_value("POINTER TO INT", struct.pack("<I", 0x12345678))

        self.assertEqual(decoded["__address__"], 0x12345678)
        self.assertEqual(decoded["__reason__"], "pointer_or_reference")


class FakePlc:
    _port = None

    def __init__(self, values):
        self.values = values
        self.reads = []

    def read(self, index_group, index_offset, plc_datatype, **_kwargs):
        self.reads.append((index_group, index_offset))
        payload = self.values[(index_group, index_offset)]
        return plc_datatype(*payload)


class TestTypedSymbolsBatchRead(unittest.TestCase):
    def test_read_values_reads_direct_symbols(self):
        symbols = [
            SymbolEntry("a", "INT", "", 1, 0, 2, 2, 0),
            SymbolEntry("b", "INT", "", 1, 2, 2, 2, 0),
        ]
        plc = FakePlc({(1, 0): struct.pack("<h", 10), (1, 2): struct.pack("<h", 20)})
        ts = TypeSystem(symbols, [])

        self.assertEqual(ts.read_values(plc, ["a", "b"]), {"a": 10, "b": 20})
        self.assertEqual(plc.reads, [(1, 0), (1, 2)])

    def test_read_values_groups_subpaths_by_root_symbol(self):
        symbol = SymbolEntry("Root", "SampleStruct", "", 1, 0, 8, 65, 0)
        datatype = DataTypeEntry(
            entry_length=0,
            version=0,
            hash_value=0,
            type_hash_value=0,
            size=8,
            offset=0,
            data_type=65,
            flags=0,
            name="SampleStruct",
            type_name="",
            comment="",
            subitems=[
                DataTypeEntry(
                    entry_length=0,
                    version=0,
                    hash_value=0,
                    type_hash_value=0,
                    size=2,
                    offset=0,
                    data_type=2,
                    flags=0,
                    name="counter",
                    type_name="INT",
                    comment="",
                ),
                DataTypeEntry(
                    entry_length=0,
                    version=0,
                    hash_value=0,
                    type_hash_value=0,
                    size=4,
                    offset=4,
                    data_type=4,
                    flags=0,
                    name="value",
                    type_name="REAL",
                    comment="",
                ),
            ],
        )
        plc = FakePlc({(1, 0): struct.pack("<hxxf", 7, 3.25)})
        ts = TypeSystem([symbol], [datatype])

        result = ts.read_values(plc, ["Root.counter", "Root.value"])

        self.assertEqual(result["Root.counter"], 7)
        self.assertAlmostEqual(result["Root.value"], 3.25)
        self.assertEqual(plc.reads, [(1, 0)])


class TestTypedSymbolsWithTestserver(unittest.TestCase):
    TEST_SERVER_AMS_NET_ID = "127.0.0.1.1.1"
    TEST_SERVER_IP_ADDRESS = "127.0.0.1"
    TEST_SERVER_AMS_PORT = pyads.PORT_SPS1

    @classmethod
    def setUpClass(cls):
        cls.handler = AdvancedHandler()
        symbol_blob, datatype_blob = _build_test_blobs()
        cls.handler.configure_symbol_upload(symbol_blob, datatype_blob)

        cls.handler.add_variable(
            PLCVariable(
                "MAIN.heizung",
                b"\x01\x00\x00\x00" + struct.pack("<f", 21.5),
                constants.ADST_BIGTYPE,
                "FB_Heizung",
                index_group=constants.INDEXGROUP_DATA,
                index_offset=1000,
            )
        )

        try:
            cls.test_server = AdsTestServer(handler=cls.handler, logging=False)
        except OSError as exc:
            raise unittest.SkipTest(str(exc))
        cls.test_server.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_server"):
            cls.test_server.stop()
            time.sleep(0.2)

    def test_get_type_system_from_testserver_fixtures(self):
        with pyads.Connection(
            self.TEST_SERVER_AMS_NET_ID,
            self.TEST_SERVER_AMS_PORT,
            self.TEST_SERVER_IP_ADDRESS,
        ) as plc:
            ts = plc.get_type_system(refresh=True)

            self.assertEqual(len(ts.symbols), 2)
            self.assertEqual(len(ts.datatypes), 3)
            self.assertEqual(ts.get_symbol("MAIN.heizung").type_name, "FB_Heizung")

    def test_read_tree_from_testserver_fixture_symbol(self):
        with pyads.Connection(
            self.TEST_SERVER_AMS_NET_ID,
            self.TEST_SERVER_AMS_PORT,
            self.TEST_SERVER_IP_ADDRESS,
        ) as plc:
            ts = plc.get_type_system(refresh=True)
            decoded = ts.read_tree(plc, "MAIN.heizung")

            self.assertIsInstance(decoded, dict)
            self.assertEqual(decoded["Enable"], True)


if __name__ == "__main__":
    unittest.main()
