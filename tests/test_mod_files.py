import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mod_info_is_factorio_2():
    info = json.loads((ROOT / "mod" / "factorio-trace" / "info.json").read_text())
    assert info["name"] == "factorio-trace"
    assert info["factorio_version"] == "2.0"
    assert (ROOT / "mod" / "factorio-trace" / "control.lua").exists()
    assert (ROOT / "mod" / "factorio-trace" / "data.lua").exists()
