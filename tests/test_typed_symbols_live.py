import json
import os
from pathlib import Path
from typing import Any, Mapping

import pytest

import pyads


CONFIG_PATH = Path(__file__).with_name("live_ads_config.json")


def _live_enabled():
    return os.environ.get("PYADS_RUN_LIVE", "").lower() in {"1", "true", "yes", "on"}


def _load_live_config():
    file_config = {}
    if CONFIG_PATH.exists():
        file_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    return {
        "device": os.environ.get("PYADS_LIVE_DEVICE", file_config.get("device", "")),
        "ams_net_id": os.environ.get(
            "PYADS_LIVE_AMS", file_config.get("ams_net_id", "")
        ),
        "ams_port": int(
            os.environ.get("PYADS_LIVE_PORT", file_config.get("ams_port", 851))
        ),
        "ip_address": os.environ.get(
            "PYADS_LIVE_IP", file_config.get("ip_address", "")
        ),
        "root_symbol": os.environ.get(
            "PYADS_LIVE_ROOT", file_config.get("root_symbol", "MAIN.heizung")
        ),
    }


def _find_leaf_path(value: Any, prefix: str = "") -> str:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).startswith("__"):
                continue
            child_prefix = "{}.{}".format(prefix, key) if prefix else str(key)
            leaf = _find_leaf_path(item, child_prefix)
            if leaf:
                return leaf
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        child_prefix = "{}[0]".format(prefix) if prefix else "[0]"
        return _find_leaf_path(value[0], child_prefix)
    return prefix


pytestmark = pytest.mark.skipif(
    not _live_enabled(),
    reason="live ADS tests require PYADS_RUN_LIVE=1",
)


def test_live_type_system_upload_and_root_decode():
    config = _load_live_config()
    assert config["ams_net_id"], "ams_net_id missing"
    assert config["ip_address"], "ip_address missing"

    with pyads.Connection(
        config["ams_net_id"],
        config["ams_port"],
        config["ip_address"],
    ) as plc:
        type_system = plc.get_type_system(refresh=True, debug=True)

        assert len(type_system.symbols) > 0
        assert len(type_system.datatypes) > 0

        root = config["root_symbol"]
        root_symbol = type_system.get_symbol(root)
        assert root_symbol is not None
        assert root_symbol.size > 0

        decoded = type_system.read_tree(plc, root)
        assert decoded is not None


def test_live_batch_read_root_and_leaf():
    config = _load_live_config()
    root = config["root_symbol"]

    with pyads.Connection(
        config["ams_net_id"],
        config["ams_port"],
        config["ip_address"],
    ) as plc:
        type_system = plc.get_type_system(refresh=True)
        decoded_root = type_system.read_tree(plc, root)
        rel_leaf = _find_leaf_path(decoded_root)
        if not rel_leaf:
            pytest.skip("no leaf path found under live root symbol")

        if rel_leaf.startswith("["):
            leaf = root + rel_leaf
        else:
            leaf = root + "." + rel_leaf

        values = type_system.read_values(plc, [root, leaf], batch=True)

        assert root in values
        assert leaf in values
        assert values[leaf] == type_system._extract_decoded_path(decoded_root, rel_leaf)
