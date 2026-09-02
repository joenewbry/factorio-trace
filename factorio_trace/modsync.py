"""Pull the Factorio Lua mod's JSONL sidecar into a session."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from factorio_trace.paths import factorio_script_output


def copy_mod_sidecar(session_dir: Path) -> dict:
    src_root = factorio_script_output()
    result = {"found": False, "events": 0, "last_tick": None}
    if not src_root.exists():
        return result
    active = src_root / "active.json"
    events = src_root / "events.jsonl"
    dest_events = session_dir / "game.jsonl"
    if events.exists():
        shutil.copy2(events, dest_events)
        n = 0
        last_tick = None
        with events.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                n += 1
                try:
                    last_tick = json.loads(line).get("tick", last_tick)
                except json.JSONDecodeError:
                    continue
        result.update({"found": True, "events": n, "last_tick": last_tick})
    if active.exists():
        shutil.copy2(active, session_dir / "game-active.json")
        try:
            data = json.loads(active.read_text(encoding="utf-8"))
            tick = data.get("tick")
            if tick is not None:
                result["last_tick"] = tick
                result["found"] = True
        except json.JSONDecodeError:
            pass
    return result


def read_active_tick() -> int | None:
    path = factorio_script_output() / "active.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tick = data.get("tick")
        return int(tick) if tick is not None else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
