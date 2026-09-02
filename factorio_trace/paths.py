"""Standard directories for Factorio and for local traces."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def home() -> Path:
    return Path.home()


def data_root() -> Path:
    override = os.environ.get("FACTORIO_TRACE_HOME")
    if override:
        return Path(override).expanduser()
    return home() / ".factorio-trace"


def sessions_dir() -> Path:
    return data_root() / "sessions"


def factorio_user_dir() -> Path | None:
    if sys.platform == "darwin":
        path = home() / "Library" / "Application Support" / "factorio"
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        path = Path(appdata) / "Factorio" if appdata else home() / "AppData" / "Roaming" / "Factorio"
    else:
        path = home() / ".factorio"
    return path if path.exists() else path


def factorio_mods_dir() -> Path:
    return factorio_user_dir() / "mods"


def factorio_script_output() -> Path:
    return factorio_user_dir() / "script-output" / "factorio-trace"
