"""Runtime ADS symbol and datatype support.

This module reads the TwinCAT symbol table and datatype table, builds a
runtime type system from both blobs, and decodes read-only values without a
hand-written ``structure_def``.
"""

from __future__ import annotations

import logging
import re
import struct
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple

from .constants import (
    ADSIGRP_SYM_DT_UPLOAD,
    ADSIGRP_SYM_UPLOAD,
    ADSIGRP_SYM_UPLOADINFO,
    ADSIGRP_SYM_UPLOADINFO2,
    ADSIGRP_SYM_VALBYHND,
    ADSIOFFS_DEVDATA_ADSSTATE,
    MAX_ADS_SUB_COMMANDS,
)
from .pyads_ex import adsSumReadBytes
from .structs import ctypes

LOG = logging.getLogger(__name__)


ADS_DTFLG_DATATYPE = 0x00000001
ADS_DTFLG_DATAITEM = 0x00000002
ADS_DTFLG_REFERENCETO = 0x00000004
ADS_DTFLG_BITVALUES = 0x00000020
ADS_DTFLG_PROPITEM = 0x00000040
ADS_DTFLG_TYPEGUID = 0x00000080
ADS_DTFLG_ATTRIBUTES = 0x00001000
ADS_DTFLG_ENUMINFOS = 0x00002000
ADS_DTFLG_ALIGNED = 0x00010000
ADS_DTFLG_STATIC = 0x00020000
ADS_DTFLG_IGNOREPERSIST = 0x00080000
ADS_DTFLG_ANYSIZEARRAY = 0x00100000
ADS_DTFLG_PLCPOINTERTYPE = 0x00800000
ADS_DTFLG_HIDESUBITEMS = 0x02000000
ADS_DTFLG_INCOMPLETE = 0x04000000
ADS_DTFLG_EXTENUMINFOS = 0x20000000

MAX_ARRAY_ELEMENTS = 4096


@dataclass(frozen=True)
class SymbolEntry:
    """One entry from ``ADSIGRP_SYM_UPLOAD``."""

    name: str
    type_name: str
    comment: str
    index_group: int
    index_offset: int
    size: int
    data_type: int
    flags: int

    @property
    def typeName(self) -> str:
        """Compatibility alias used by earlier local prototypes."""

        return self.type_name

    @property
    def iGroup(self) -> int:
        """Compatibility alias used by earlier local prototypes."""

        return self.index_group

    @property
    def iOffs(self) -> int:
        """Compatibility alias used by earlier local prototypes."""

        return self.index_offset

    @property
    def dataType(self) -> int:
        """Compatibility alias used by earlier local prototypes."""

        return self.data_type


@dataclass
class TypeAttribute:
    name: str
    value: str = ""


@dataclass
class DataTypeEntry:
    """One ``AdsDatatypeEntry`` including nested subitems."""

    entry_length: int
    version: int
    hash_value: int
    type_hash_value: int
    size: int
    offset: int
    data_type: int
    flags: int
    name: str
    type_name: str
    comment: str
    array_info: List[Tuple[int, int]] = field(default_factory=list)
    subitems: List["DataTypeEntry"] = field(default_factory=list)
    attributes: List[TypeAttribute] = field(default_factory=list)

    @property
    def offs(self) -> int:
        """Compatibility alias used by earlier local prototypes."""

        return self.offset

    @property
    def dataType(self) -> int:
        """Compatibility alias used by earlier local prototypes."""

        return self.data_type

    @property
    def typeName(self) -> str:
        """Compatibility alias used by earlier local prototypes."""

        return self.type_name

    @property
    def arrayInfo(self) -> List[Tuple[int, int]]:
        """Compatibility alias used by earlier local prototypes."""

        return self.array_info

    @property
    def subItems(self) -> int:
        """Compatibility alias used by earlier local prototypes."""

        return len(self.subitems)

    @property
    def subs(self) -> List["DataTypeEntry"]:
        """Compatibility alias used by earlier local prototypes."""

        return self.subitems

    @property
    def is_array(self) -> bool:
        return bool(self.array_info)

    @property
    def is_pointer_or_reference(self) -> bool:
        decl = (self.name or "").upper()
        typ = (self.type_name or "").upper()
        return (
            "POINTER TO " in decl
            or "REFERENCE TO " in decl
            or "POINTER TO " in typ
            or "REFERENCE TO " in typ
            or bool(self.flags & (ADS_DTFLG_REFERENCETO | ADS_DTFLG_PLCPOINTERTYPE))
        )


def _le_u16(blob: bytes, offset: int) -> Tuple[int, int]:
    return struct.unpack_from("<H", blob, offset)[0], offset + 2


def _le_u32(blob: bytes, offset: int) -> Tuple[int, int]:
    return struct.unpack_from("<I", blob, offset)[0], offset + 4


def _decode_tc_string(data: bytes) -> str:
    return data.decode("windows-1252", errors="ignore")


def _read_len_string(blob: bytes, offset: int, length: int) -> Tuple[str, int]:
    data = blob[offset : offset + length]
    return _decode_tc_string(data), offset + length + 1


def _looks_text(data: bytes) -> bool:
    return bool(data) and all((32 <= c < 127) or c in (9, 10, 13) for c in data)


def _scan_attributes(tail: bytes) -> List[TypeAttribute]:
    """Best-effort parser for TwinCAT datatype attribute tails."""

    if len(tail) < 2:
        return []

    def parse_counted(start: int, width: int) -> Optional[List[TypeAttribute]]:
        if start + width > len(tail):
            return None
        count = int.from_bytes(tail[start : start + width], "little")
        if count <= 0 or count > 256:
            return None
        pos = start + width
        attrs: List[TypeAttribute] = []
        for _ in range(count):
            if pos + width > len(tail):
                return None
            name_len = int.from_bytes(tail[pos : pos + width], "little")
            pos += width
            if name_len > 4096 or pos + name_len + 1 > len(tail):
                return None
            name = tail[pos : pos + name_len]
            pos += name_len + 1

            if pos + width > len(tail):
                return None
            value_len = int.from_bytes(tail[pos : pos + width], "little")
            pos += width
            if value_len > 65535 or pos + value_len + 1 > len(tail):
                return None
            value = tail[pos : pos + value_len]
            pos += value_len + 1

            if not _looks_text(name):
                return None
            attrs.append(
                TypeAttribute(_decode_tc_string(name), _decode_tc_string(value))
            )
        return attrs

    def parse_cstrings(start: int) -> Optional[List[TypeAttribute]]:
        pos = start
        strings: List[str] = []
        while pos < len(tail):
            end = tail.find(b"\x00", pos)
            if end < 0:
                break
            raw = tail[pos:end]
            pos = end + 1
            if not raw:
                continue
            if not _looks_text(raw):
                return None
            strings.append(_decode_tc_string(raw))
        if not strings:
            return None
        attrs = []
        it = iter(strings)
        for name in it:
            attrs.append(TypeAttribute(name, next(it, "")))
        return attrs

    for start in range(min(64, len(tail))):
        for parser in (
            lambda pos: parse_counted(pos, 2),
            lambda pos: parse_counted(pos, 4),
            parse_cstrings,
        ):
            parsed = parser(start)
            if parsed:
                return parsed
    return []


def parse_symbols(blob: bytes) -> List[SymbolEntry]:
    """Parse a raw symbol table blob."""

    symbols: List[SymbolEntry] = []
    pos = 0
    end = len(blob)
    while pos + 30 <= end:
        entry_length, cursor = _le_u32(blob, pos)
        if entry_length <= 0 or entry_length > end - pos:
            break
        index_group, cursor = _le_u32(blob, cursor)
        index_offset, cursor = _le_u32(blob, cursor)
        size, cursor = _le_u32(blob, cursor)
        data_type, cursor = _le_u32(blob, cursor)
        flags, cursor = _le_u32(blob, cursor)
        name_len, cursor = _le_u16(blob, cursor)
        type_len, cursor = _le_u16(blob, cursor)
        comment_len, cursor = _le_u16(blob, cursor)

        name, cursor = _read_len_string(blob, cursor, name_len)
        type_name, cursor = _read_len_string(blob, cursor, type_len)
        comment, _ = _read_len_string(blob, cursor, comment_len)

        symbols.append(
            SymbolEntry(
                name=name,
                type_name=type_name,
                comment=comment,
                index_group=index_group,
                index_offset=index_offset,
                size=size,
                data_type=data_type,
                flags=flags,
            )
        )
        pos += entry_length
    return symbols


def _parse_datatype_entry(blob: bytes, offset: int) -> Tuple[DataTypeEntry, int]:
    start = offset
    if offset + 4 > len(blob):
        raise StopIteration
    entry_length, offset = _le_u32(blob, offset)
    if entry_length <= 0 or start + entry_length > len(blob):
        raise StopIteration

    version, offset = _le_u32(blob, offset)
    hash_value, offset = _le_u32(blob, offset)
    type_hash_value, offset = _le_u32(blob, offset)
    size, offset = _le_u32(blob, offset)
    item_offset, offset = _le_u32(blob, offset)
    data_type, offset = _le_u32(blob, offset)
    flags, offset = _le_u32(blob, offset)
    name_length, offset = _le_u16(blob, offset)
    type_length, offset = _le_u16(blob, offset)
    comment_length, offset = _le_u16(blob, offset)
    array_dim, offset = _le_u16(blob, offset)
    subitem_count, offset = _le_u16(blob, offset)

    name, offset = _read_len_string(blob, offset, name_length)
    type_name, offset = _read_len_string(blob, offset, type_length)
    comment, offset = _read_len_string(blob, offset, comment_length)

    array_info: List[Tuple[int, int]] = []
    for _ in range(array_dim):
        lower_bound, offset = _le_u32(blob, offset)
        elements, offset = _le_u32(blob, offset)
        array_info.append((lower_bound, elements))

    subitems: List[DataTypeEntry] = []
    cursor = offset
    for _ in range(subitem_count):
        subitem, cursor = _parse_datatype_entry(blob, cursor)
        subitems.append(subitem)

    end = start + entry_length
    tail = blob[cursor:end] if cursor < end else b""
    attributes = _scan_attributes(tail) if flags & ADS_DTFLG_ATTRIBUTES else []

    return (
        DataTypeEntry(
            entry_length=entry_length,
            version=version,
            hash_value=hash_value,
            type_hash_value=type_hash_value,
            size=size,
            offset=item_offset,
            data_type=data_type,
            flags=flags,
            name=name,
            type_name=type_name,
            comment=comment,
            array_info=array_info,
            subitems=subitems,
            attributes=attributes,
        ),
        end,
    )


def parse_datatypes(blob: Optional[bytes]) -> List[DataTypeEntry]:
    """Parse raw datatype table bytes into an ordered list of entries."""

    if not blob:
        return []

    def parse_from(start: int) -> List[DataTypeEntry]:
        entries: List[DataTypeEntry] = []
        offset = start
        while offset + 4 <= len(blob):
            try:
                entry, offset = _parse_datatype_entry(blob, offset)
            except StopIteration:
                break
            entries.append(entry)
        return entries

    entries = parse_from(0)
    if entries:
        return entries
    for start in range(1, min(64, len(blob))):
        entries = parse_from(start)
        if entries:
            return entries
    return []


def parse_dtypes(blob: Optional[bytes]) -> Dict[str, DataTypeEntry]:
    """Compatibility parser returning the preferred type lookup map."""

    return _build_type_maps(parse_datatypes(blob))[0]


def _is_type_declaration_key(name: str) -> bool:
    upper = (name or "").upper()
    return not (
        upper.startswith("POINTER TO ")
        or upper.startswith("REFERENCE TO ")
        or upper.startswith("ARRAY ")
    )


def _build_type_maps(
    entries: Iterable[DataTypeEntry],
) -> Tuple[Dict[str, DataTypeEntry], Dict[str, DataTypeEntry], Dict[str, DataTypeEntry]]:
    by_key: Dict[str, DataTypeEntry] = {}
    by_declaration: Dict[str, DataTypeEntry] = {}
    aliases: Dict[str, DataTypeEntry] = {}

    for entry in entries:
        if entry.name:
            by_declaration.setdefault(entry.name, entry)
            if _is_type_declaration_key(entry.name):
                by_key.setdefault(entry.name, entry)
        if entry.type_name:
            if entry.name and entry.name != entry.type_name and _is_type_declaration_key(entry.name):
                aliases.setdefault(entry.name, entry)
            if entry.name == entry.type_name:
                by_key.setdefault(entry.type_name, entry)

    for alias, entry in aliases.items():
        by_key.setdefault(alias, entry)
    return by_key, by_declaration, aliases


def _raw_value(type_name: str, data: bytes, reason: str) -> Dict[str, Any]:
    return {
        "__ads_type__": type_name,
        "__raw__": data.hex(),
        "__reason__": reason,
    }


def _decode_scalar(type_name: str, data: bytes, offset: int, size: int) -> Tuple[Any, int]:
    type_upper = (type_name or "").strip().upper()
    chunk_end = offset + max(0, size)
    try:
        if type_upper == "BOOL":
            return data[offset] != 0, offset + 1
        if type_upper in ("BYTE", "USINT"):
            return data[offset], offset + 1
        if type_upper == "SINT":
            return struct.unpack_from("<b", data, offset)[0], offset + 1
        if type_upper == "INT":
            return struct.unpack_from("<h", data, offset)[0], offset + 2
        if type_upper in ("UINT", "WORD"):
            return struct.unpack_from("<H", data, offset)[0], offset + 2
        if type_upper == "DINT":
            return struct.unpack_from("<i", data, offset)[0], offset + 4
        if type_upper in ("UDINT", "DWORD"):
            return struct.unpack_from("<I", data, offset)[0], offset + 4
        if type_upper == "LINT":
            return struct.unpack_from("<q", data, offset)[0], offset + 8
        if type_upper in ("ULINT", "LWORD"):
            return struct.unpack_from("<Q", data, offset)[0], offset + 8
        if type_upper == "REAL":
            return struct.unpack_from("<f", data, offset)[0], offset + 4
        if type_upper == "LREAL":
            return struct.unpack_from("<d", data, offset)[0], offset + 8
        if type_upper.startswith("STRING"):
            raw = data[offset:chunk_end]
            nul = raw.find(b"\x00")
            if nul >= 0:
                raw = raw[:nul]
            return _decode_tc_string(raw), chunk_end
        if type_upper.startswith("WSTRING"):
            raw = data[offset:chunk_end]
            return raw.decode("utf-16-le", errors="ignore").split("\x00", 1)[0], chunk_end
        if type_upper in (
            "TIME",
            "TIME_OF_DAY",
            "TOD",
            "DATE",
            "DT",
            "DATE_AND_TIME",
            "LTIME",
            "LTOD",
            "LDT",
        ):
            if size == 8:
                return struct.unpack_from("<Q", data, offset)[0], offset + 8
            if size == 4:
                return struct.unpack_from("<I", data, offset)[0], offset + 4
            return int.from_bytes(data[offset:chunk_end], "little"), chunk_end
    except (IndexError, struct.error):
        return None, offset
    return None, offset


def _decode_address(data: bytes, offset: int, size: int) -> int:
    end = offset + max(0, size)
    if size >= 8:
        return struct.unpack_from("<Q", data, offset)[0]
    if size >= 4:
        return struct.unpack_from("<I", data, offset)[0]
    return int.from_bytes(data[offset:end], "little")


def _product(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result *= max(0, value)
    return result


def _split_path(path: str) -> List[str]:
    return [part for part in re.split(r"\.(?![^\[]*\])", path) if part]


class TypeSystem:
    """Symbols, datatypes, schema metadata, and read-only typed decoders."""

    def __init__(
        self,
        symbols: List[SymbolEntry],
        datatypes: Optional[List[DataTypeEntry]] = None,
    ) -> None:
        self.symbols = symbols
        self.datatypes = datatypes or []
        self._symbols_by_name = {symbol.name: symbol for symbol in self.symbols}
        self.types, self.declarations, self.aliases = _build_type_maps(self.datatypes)
        self.dt_map = self.types

    @classmethod
    def from_blobs(
        cls,
        symbol_blob: bytes,
        datatype_blob: Optional[bytes] = None,
        *,
        debug: bool = False,
    ) -> "TypeSystem":
        if debug:
            LOG.setLevel(logging.DEBUG)
        return cls(parse_symbols(symbol_blob or b""), parse_datatypes(datatype_blob))

    @classmethod
    def from_connection(cls, plc: Any, *, debug: bool = False) -> "TypeSystem":
        symbol_blob, datatype_blob = upload_symbol_and_datatype_blobs(plc, debug=debug)
        return cls.from_blobs(symbol_blob, datatype_blob, debug=debug)

    def iter_symbols(self, prefix: Optional[str] = None) -> Iterator[SymbolEntry]:
        if not prefix:
            return iter(self.symbols)
        dotted_prefix = prefix + "."
        return (
            symbol
            for symbol in self.symbols
            if symbol.name == prefix or symbol.name.startswith(dotted_prefix)
        )

    def get_symbol(self, name: str) -> Optional[SymbolEntry]:
        return self._symbols_by_name.get(name)

    def get_type(self, type_name: str) -> Optional[DataTypeEntry]:
        return self.types.get(type_name) or self.declarations.get(type_name)

    def to_schema(self) -> Dict[str, Any]:
        return {
            "symbols": [self._symbol_to_schema(symbol) for symbol in self.symbols],
            "types": {
                name: self._datatype_to_schema(entry)
                for name, entry in sorted(self.types.items())
            },
            "declarations": {
                name: self._datatype_to_schema(entry)
                for name, entry in sorted(self.declarations.items())
                if name not in self.types
            },
        }

    def read_value(self, plc: Any, name: str) -> Any:
        symbol = self._require_symbol(name)
        raw = self._read_symbol_raw(plc, symbol)
        return self.decode_value(symbol.type_name, raw, 0, symbol.size)

    def read_tree(self, plc: Any, root: str) -> Any:
        return self.read_value(plc, root)

    def read_values(
        self,
        plc: Any,
        names: Iterable[str],
        *,
        batch: bool = True,
        ads_sub_commands: int = MAX_ADS_SUB_COMMANDS,
    ) -> Dict[str, Any]:
        names_list = list(names)
        if not batch:
            return {name: self._read_path(plc, name) for name in names_list}

        groups: Dict[str, List[str]] = defaultdict(list)
        direct_symbols: List[SymbolEntry] = []
        for name in names_list:
            symbol = self.get_symbol(name)
            if symbol is not None:
                direct_symbols.append(symbol)
                continue
            root = self._find_root_symbol_name(name)
            if root is None:
                raise KeyError("Symbol not found: {}".format(name))
            groups[root].append(name)

        result: Dict[str, Any] = {}
        if direct_symbols:
            raw_by_name = self._sum_read_raw(plc, direct_symbols, ads_sub_commands)
            for symbol in direct_symbols:
                result[symbol.name] = self.decode_value(
                    symbol.type_name, raw_by_name[symbol.name], 0, symbol.size
                )

        for root, requested_paths in groups.items():
            root_symbol = self._require_symbol(root)
            raw = self._read_symbol_raw(plc, root_symbol)
            decoded_root = self.decode_value(root_symbol.type_name, raw, 0, root_symbol.size)
            for requested_path in requested_paths:
                rel_path = requested_path[len(root) :].lstrip(".")
                result[requested_path] = self._extract_decoded_path(decoded_root, rel_path)
        return result

    def decode_value(
        self,
        type_name: str,
        data: bytes,
        offset: int = 0,
        size: Optional[int] = None,
        _stack: Optional[List[str]] = None,
    ) -> Any:
        total_size = len(data) - offset if size is None else max(0, size)
        raw = data[offset : offset + total_size]
        type_name = (type_name or "").strip()

        scalar, next_offset = _decode_scalar(type_name, data, offset, total_size)
        if scalar is not None or next_offset != offset:
            return scalar

        if "POINTER TO " in type_name.upper() or "REFERENCE TO " in type_name.upper():
            return {
                "__ads_type__": type_name,
                "__address__": _decode_address(data, offset, total_size),
                "__reason__": "pointer_or_reference",
            }

        datatype = self.get_type(type_name)
        if datatype is None:
            return _raw_value(type_name, raw, "unknown_type")

        return self._decode_datatype(datatype, data, offset, total_size, _stack or [])

    def _decode_datatype(
        self,
        datatype: DataTypeEntry,
        data: bytes,
        offset: int,
        size: int,
        stack: List[str],
    ) -> Any:
        key = datatype.name or datatype.type_name
        raw = data[offset : offset + size]
        if key in stack:
            return _raw_value(key, raw, "recursive_type")
        if datatype.flags & ADS_DTFLG_INCOMPLETE:
            return _raw_value(key, raw, "incomplete_type")
        if datatype.flags & ADS_DTFLG_HIDESUBITEMS:
            return _raw_value(key, raw, "hidden_subitems")
        if datatype.is_pointer_or_reference:
            return {
                "__ads_type__": datatype.name or datatype.type_name,
                "__address__": _decode_address(data, offset, size),
                "__reason__": "pointer_or_reference",
            }

        if datatype.array_info:
            return self._decode_array(datatype, data, offset, size, stack + [key])

        if datatype.subitems:
            result: "OrderedDict[str, Any]" = OrderedDict()
            for subitem in datatype.subitems:
                sub_size = subitem.size or max(0, size - subitem.offset)
                sub_offset = offset + subitem.offset
                result[subitem.name] = self._decode_subitem(
                    subitem, data, sub_offset, sub_size, stack + [key]
                )
            return result

        scalar_type = datatype.type_name or datatype.name
        scalar, next_offset = _decode_scalar(scalar_type, data, offset, size)
        if scalar is not None or next_offset != offset:
            return scalar

        if datatype.flags & (ADS_DTFLG_ENUMINFOS | ADS_DTFLG_EXTENUMINFOS | ADS_DTFLG_BITVALUES):
            return int.from_bytes(raw, "little", signed=False)

        if datatype.type_name and datatype.type_name != datatype.name:
            alias_target = self.get_type(datatype.type_name)
            if alias_target is not None and alias_target is not datatype:
                return self._decode_datatype(alias_target, data, offset, size, stack + [key])

        return _raw_value(datatype.name or datatype.type_name, raw, "opaque_type")

    def _decode_subitem(
        self,
        subitem: DataTypeEntry,
        data: bytes,
        offset: int,
        size: int,
        stack: List[str],
    ) -> Any:
        if subitem.subitems or subitem.array_info or not subitem.type_name:
            return self._decode_datatype(subitem, data, offset, size, stack)
        return self.decode_value(subitem.type_name, data, offset, size, stack)

    def _decode_array(
        self,
        datatype: DataTypeEntry,
        data: bytes,
        offset: int,
        size: int,
        stack: List[str],
    ) -> List[Any]:
        counts = [elements for _, elements in datatype.array_info]
        element_count = _product(counts)
        if element_count <= 0:
            return []
        total_size = size or datatype.size
        element_size = max(1, total_size // element_count)
        element_type = datatype.type_name
        if datatype.subitems and datatype.subitems[0].type_name:
            element_type = datatype.subitems[0].type_name

        decoded: List[Any] = []
        decode_count = min(element_count, MAX_ARRAY_ELEMENTS)
        for index in range(decode_count):
            item_offset = offset + index * element_size
            if item_offset + element_size > offset + total_size:
                break
            decoded.append(self.decode_value(element_type, data, item_offset, element_size, stack))
        if decode_count < element_count:
            decoded.append(
                _raw_value(
                    datatype.name or datatype.type_name,
                    b"",
                    "truncated_array_{}_of_{}".format(decode_count, element_count),
                )
            )
        return decoded

    def _read_path(self, plc: Any, name: str) -> Any:
        symbol = self.get_symbol(name)
        if symbol is not None:
            return self.read_value(plc, name)
        root = self._find_root_symbol_name(name)
        if root is None:
            raise KeyError("Symbol not found: {}".format(name))
        root_value = self.read_tree(plc, root)
        return self._extract_decoded_path(root_value, name[len(root) :].lstrip("."))

    def _find_root_symbol_name(self, name: str) -> Optional[str]:
        parts = _split_path(name)
        for index in range(len(parts), 0, -1):
            candidate = ".".join(parts[:index])
            if candidate in self._symbols_by_name:
                return candidate
        return None

    def _require_symbol(self, name: str) -> SymbolEntry:
        symbol = self.get_symbol(name)
        if symbol is None:
            raise KeyError("Symbol not found: {}".format(name))
        return symbol

    def _read_symbol_raw(self, plc: Any, symbol: SymbolEntry) -> bytes:
        try:
            return read_raw_block(plc, symbol.index_group, symbol.index_offset, symbol.size)
        except Exception:
            handle = plc.get_handle(symbol.name)
            try:
                raw_type = ctypes.c_ubyte * symbol.size
                return bytes(
                    plc.read(
                        ADSIGRP_SYM_VALBYHND,
                        handle,
                        raw_type,
                        return_ctypes=True,
                        check_length=False,
                    )
                )
            finally:
                plc.release_handle(handle)

    def _sum_read_raw(
        self,
        plc: Any,
        symbols: List[SymbolEntry],
        ads_sub_commands: int,
    ) -> Dict[str, bytes]:
        if not symbols:
            return {}
        if getattr(plc, "_port", None) is None:
            return {symbol.name: self._read_symbol_raw(plc, symbol) for symbol in symbols}

        result: Dict[str, bytes] = {}
        for start in range(0, len(symbols), ads_sub_commands):
            chunk = symbols[start : start + ads_sub_commands]
            requests = [
                (symbol.index_group, symbol.index_offset, symbol.size) for symbol in chunk
            ]
            response = adsSumReadBytes(plc._port, plc._adr, requests)
            payload_offset = 4 * len(chunk)
            for index, symbol in enumerate(chunk):
                error = struct.unpack_from("<I", response, index * 4)[0]
                if error:
                    raise RuntimeError(
                        "ADS SumRead failed for {} with error {}".format(
                            symbol.name, error
                        )
                    )
                result[symbol.name] = bytes(
                    response[payload_offset : payload_offset + symbol.size]
                )
                payload_offset += symbol.size
        return result

    def _extract_decoded_path(self, value: Any, rel_path: str) -> Any:
        current = value
        for part in _split_path(rel_path):
            name, indexes = self._parse_part_indexes(part)
            if name:
                if not isinstance(current, Mapping) or name not in current:
                    raise KeyError("Path component not found: {}".format(part))
                current = current[name]
            for index in indexes:
                if not isinstance(current, list):
                    raise KeyError("Path component is not an array: {}".format(part))
                current = current[index]
        return current

    @staticmethod
    def _parse_part_indexes(part: str) -> Tuple[str, List[int]]:
        match = re.match(r"^([^\[]+)((?:\[[^\]]+\])*)$", part)
        if not match:
            return part, []
        name = match.group(1)
        raw_indexes = match.group(2)
        indexes = []
        for raw in re.findall(r"\[([^\]]+)\]", raw_indexes):
            for value in raw.split(","):
                indexes.append(int(value))
        return name, indexes

    @staticmethod
    def _symbol_to_schema(symbol: SymbolEntry) -> Dict[str, Any]:
        return {
            "name": symbol.name,
            "type": symbol.type_name,
            "comment": symbol.comment,
            "index_group": symbol.index_group,
            "index_offset": symbol.index_offset,
            "size": symbol.size,
            "data_type": symbol.data_type,
            "flags": symbol.flags,
        }

    def _datatype_to_schema(self, datatype: DataTypeEntry) -> Dict[str, Any]:
        return {
            "name": datatype.name,
            "type": datatype.type_name,
            "comment": datatype.comment,
            "size": datatype.size,
            "offset": datatype.offset,
            "data_type": datatype.data_type,
            "flags": datatype.flags,
            "array_info": [
                {"lower_bound": lower, "elements": elements}
                for lower, elements in datatype.array_info
            ],
            "attributes": [
                {"name": attr.name, "value": attr.value} for attr in datatype.attributes
            ],
            "subitems": [
                self._datatype_to_schema(subitem) for subitem in datatype.subitems
            ],
        }


class TypedSymbolTable(TypeSystem):
    """Backward-compatible name for earlier local experiments."""


def build_typed_symbol_table(
    symbol_block_bytes: bytes,
    n_symbols: int = 0,
    datatype_block_bytes: Optional[bytes] = None,
    n_datatypes: int = 0,
) -> TypedSymbolTable:
    table = TypedSymbolTable(
        parse_symbols(symbol_block_bytes or b""),
        parse_datatypes(datatype_block_bytes),
    )
    if n_symbols and n_symbols != len(table.symbols):
        LOG.debug("Symbol count mismatch: upload=%s parsed=%s", n_symbols, len(table.symbols))
    if n_datatypes and n_datatypes != len(table.datatypes):
        LOG.debug(
            "Datatype count mismatch: upload=%s parsed=%s",
            n_datatypes,
            len(table.datatypes),
        )
    return table


def read_raw_block(plc: Any, index_group: int, index_offset: int, size: int) -> bytes:
    raw_type = ctypes.c_ubyte * size
    return bytes(
        plc.read(
            index_group,
            index_offset,
            raw_type,
            return_ctypes=True,
            check_length=False,
        )
    )


def _read_upload_info(plc: Any, debug: bool = False) -> Tuple[int, int, int, int]:
    raw_type = ctypes.c_ubyte * 24
    errors: List[Exception] = []
    for index_offset in (0, ADSIOFFS_DEVDATA_ADSSTATE):
        try:
            raw = bytes(
                plc.read(
                    ADSIGRP_SYM_UPLOADINFO2,
                    index_offset,
                    raw_type,
                    return_ctypes=True,
                    check_length=False,
                )
            )
            if len(raw) >= 16:
                n_symbols, symbol_size, n_datatypes, datatype_size = struct.unpack_from(
                    "<IIII", raw, 0
                )
                if debug:
                    LOG.debug(
                        "UPLOADINFO2 offset=%s symbols=%s sym_size=%s datatypes=%s dt_size=%s",
                        index_offset,
                        n_symbols,
                        symbol_size,
                        n_datatypes,
                        datatype_size,
                    )
                return n_symbols, symbol_size, n_datatypes, datatype_size
        except Exception as exc:
            errors.append(exc)

    legacy_type = ctypes.c_ubyte * 8
    for index_offset in (0, ADSIOFFS_DEVDATA_ADSSTATE):
        try:
            raw = bytes(
                plc.read(
                    ADSIGRP_SYM_UPLOADINFO,
                    index_offset,
                    legacy_type,
                    return_ctypes=True,
                    check_length=False,
                )
            )
            if len(raw) >= 8:
                n_symbols, symbol_size = struct.unpack_from("<II", raw, 0)
                return n_symbols, symbol_size, 0, 0
        except Exception as exc:
            errors.append(exc)

    if errors:
        raise RuntimeError("Could not read ADS symbol upload info") from errors[-1]
    raise RuntimeError("Could not read ADS symbol upload info")


def upload_symbol_and_datatype_blobs(
    plc: Any,
    *,
    debug: bool = False,
) -> Tuple[bytes, bytes]:
    """Upload raw symbol and datatype blobs from an open connection."""

    _n_symbols, symbol_size, _n_datatypes, datatype_size = _read_upload_info(
        plc, debug=debug
    )
    symbol_blob = _read_blob_with_offsets(plc, ADSIGRP_SYM_UPLOAD, symbol_size)
    datatype_blob = b""
    if datatype_size:
        try:
            datatype_blob = _read_blob_with_offsets(plc, ADSIGRP_SYM_DT_UPLOAD, datatype_size)
        except Exception:
            LOG.debug("Datatype upload failed", exc_info=True)
            datatype_blob = b""
    return symbol_blob, datatype_blob


def _read_blob_with_offsets(plc: Any, index_group: int, size: int) -> bytes:
    last_error: Optional[Exception] = None
    for index_offset in (0, ADSIOFFS_DEVDATA_ADSSTATE):
        try:
            return read_raw_block(plc, index_group, index_offset, size)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(
        "Could not read ADS blob index_group=0x{:X} size={}".format(index_group, size)
    ) from last_error
