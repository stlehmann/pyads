"""Test the curated public API surface of the pyads package.

:license: MIT, see license file or https://opensource.org/licenses/MIT

"""
import unittest

import pyads
from pyads import constants


EXPECTED_ADSIGRP = [
    "ADSIGRP_SYMTAB",
    "ADSIGRP_SYMNAME",
    "ADSIGRP_SYMVAL",
    "ADSIGRP_SYM_HNDBYNAME",
    "ADSIGRP_SYM_VALBYNAME",
    "ADSIGRP_SYM_VALBYHND",
    "ADSIGRP_SYM_RELEASEHND",
    "ADSIGRP_SYM_INFOBYNAME",
    "ADSIGRP_SYM_VERSION",
    "ADSIGRP_SYM_INFOBYNAMEEX",
    "ADSIGRP_SYM_DOWNLOAD",
    "ADSIGRP_SYM_UPLOAD",
    "ADSIGRP_SYM_UPLOADINFO",
    "ADSIGRP_SYM_DOWNLOAD2",
    "ADSIGRP_SYM_DT_UPLOAD",
    "ADSIGRP_SYM_UPLOADINFO2",
    "ADSIGRP_SYMNOTE",
    "ADSIGRP_SYM_FB_PROP_CALL",
    "ADSIGRP_IOIMAGE_RWIB",
    "ADSIGRP_IOIMAGE_RWIX",
    "ADSIGRP_IOIMAGE_RWOB",
    "ADSIGRP_IOIMAGE_RWOX",
    "ADSIGRP_IOIMAGE_CLEARI",
    "ADSIGRP_IOIMAGE_CLEARO",
    "ADSIGRP_SUMUP_READ",
    "ADSIGRP_SUMUP_WRITE",
    "ADSIGRP_DEVICE_DATA",
]

EXPECTED_ADSIOFFS = [
    "ADSIOFFS_DEVDATA_ADSSTATE",
    "ADSIOFFS_DEVDATA_DEVSTATE",
]

EXPECTED_ADSSYMBOLFLAG = [
    "ADSSYMBOLFLAG_PERSISTENT",
    "ADSSYMBOLFLAG_BITVALUE",
    "ADSSYMBOLFLAG_REFERENCETO",
    "ADSSYMBOLFLAG_TYPEGUID",
    "ADSSYMBOLFLAG_TCCOMIFACEPTR",
    "ADSSYMBOLFLAG_READONLY",
    "ADSSYMBOLFLAG_CONTEXTMASK",
]

# Wire-protocol internals (AMS header command ids / state flags). Deliberately
# kept out of the top-level namespace; still reachable via pyads.constants.
UNEXPORTED_PREFIXES = ["ADSCOMMAND_", "ADSSTATEFLAG_"]


def _names(module, prefix):
    return {name for name in dir(module) if name.startswith(prefix)}


class PublicConstantsTestCase(unittest.TestCase):
    """Guard the explicitly re-exported constant groups against drift."""

    def _check_prefix(self, prefix, expected):
        expected_set = set(expected)
        self.assertEqual(len(expected_set), len(expected), "duplicate in expected list")
        # every constant defined in pyads.constants is listed here ...
        self.assertEqual(_names(constants, prefix), expected_set)
        # ... and every one of them is exported from the top-level package
        self.assertEqual(_names(pyads, prefix), expected_set)
        for name in expected:
            self.assertIs(getattr(pyads, name), getattr(constants, name))

    def test_adsigrp_exported(self):
        self._check_prefix("ADSIGRP_", EXPECTED_ADSIGRP)
        self.assertEqual(pyads.ADSIGRP_SYM_VALBYHND, 0xF005)

    def test_adsioffs_exported(self):
        self._check_prefix("ADSIOFFS_", EXPECTED_ADSIOFFS)

    def test_adssymbolflag_exported(self):
        self._check_prefix("ADSSYMBOLFLAG_", EXPECTED_ADSSYMBOLFLAG)
        self.assertEqual(pyads.ADSSYMBOLFLAG_READONLY, 0x20)

    def test_wire_protocol_constants_not_exported(self):
        for prefix in UNEXPORTED_PREFIXES:
            self.assertTrue(_names(constants, prefix), prefix)
            self.assertEqual(_names(pyads, prefix), set(), prefix)


if __name__ == "__main__":
    unittest.main()
