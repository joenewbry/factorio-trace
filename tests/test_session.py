import json
from pathlib import Path

from factorio_trace.coords import WindowBounds
from factorio_trace.session import SessionWriter
from factorio_trace.upload import pack_session, validate_manifest


def test_pause_drops_out_of_focus_and_manifest_roundtrips(tmp_path: Path):
    w = SessionWriter(tmp_path, contributor="tester", fps=30)
    bounds = WindowBounds(0, 0, 1920, 1080)
    w.resume("Factorio", bounds)
    w.event({"type": "key_down", "key": "w"})
    w.pause("focus_lost:Safari")
    w.event({"type": "key_down", "key": "should-not-matter-if-caller-gates"})
    w.close()

    man = validate_manifest(w.dir / "manifest.json")
    assert man["id"] == w.id
    assert man["contributor"] == "tester"
    assert man["pauses"] >= 1
    assert man["capture"]["input"] == "os-hid-gated-on-factorio-focus"

    events = [json.loads(line) for line in (w.dir / "input.jsonl").read_text().splitlines()]
    types = [e["type"] for e in events]
    assert types[0] == "resume"
    assert "pause" in types
    assert types.count("key_down") == 2  # writer itself does not gate; recorder does

    blob = pack_session(w.dir)
    assert blob[:2] == b"PK"
