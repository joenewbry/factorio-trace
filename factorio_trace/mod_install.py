"""Install the Factorio Trace Lua mod into the local Factorio mods folder."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from factorio_trace.paths import factorio_mods_dir, factorio_user_dir

MOD_NAME = "factorio-trace"
MOD_VERSION = "0.1.0"


def packaged_mod_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "mod" / "factorio-trace"


def install_mod() -> Path:
    src = packaged_mod_dir()
    if not (src / "info.json").exists():
        raise FileNotFoundError(f"mod sources missing at {src}")
    mods = factorio_mods_dir()
    mods.mkdir(parents=True, exist_ok=True)
    dest = mods / f"{MOD_NAME}_{MOD_VERSION}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    _enable_mod_list(mods)
    return dest


def _enable_mod_list(mods: Path) -> None:
    path = mods / "mod-list.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"mods": [{"name": "base", "enabled": True}]}
    mods_list = data.setdefault("mods", [])
    for entry in mods_list:
        if entry.get("name") == MOD_NAME:
            entry["enabled"] = True
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            return
    mods_list.append({"name": MOD_NAME, "enabled": True})
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def doctor() -> list[str]:
    notes = []
    user = factorio_user_dir()
    if not user.exists():
        notes.append(f"Factorio user dir not found yet ({user}). Launch Factorio once.")
    else:
        notes.append(f"Factorio user dir: {user}")
    mods = factorio_mods_dir()
    dest = mods / f"{MOD_NAME}_{MOD_VERSION}"
    if dest.exists():
        notes.append(f"mod installed: {dest}")
    else:
        notes.append("mod not installed. Run: factorio-trace install-mod")
    return notes
