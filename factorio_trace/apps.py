"""How we decide the frontmost process is Factorio."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


FACTORIO_PROCESS_NAMES = frozenset(
    {
        "factorio",
        "factorio.exe",
        "factorio.app",
    }
)

FACTORIO_BUNDLE_IDS = frozenset(
    {
        "com.factorio",
        "com.wube.factorio",
        "factorio",
    }
)

_TITLE_RE = re.compile(r"\bfactorio\b", re.IGNORECASE)


@dataclass(frozen=True)
class FrontmostApp:
    name: str
    bundle_id: str = ""
    pid: int = 0
    exe: str = ""
    window_title: str = ""

    def is_factorio(self) -> bool:
        return is_factorio_app(
            name=self.name,
            bundle_id=self.bundle_id,
            exe=self.exe,
            window_title=self.window_title,
        )


def is_factorio_app(
    name: str = "",
    bundle_id: str = "",
    exe: str = "",
    window_title: str = "",
) -> bool:
    """Return True if this looks like the Factorio game client.

    Matches the game, not a browser tab titled Factorio, not the website,
    not VS Code with a factorio-trace repo focused.
    """
    bundle = (bundle_id or "").strip().lower()
    if bundle and bundle in FACTORIO_BUNDLE_IDS:
        return True

    exe_base = os.path.basename(exe or "").strip().lower()
    if exe_base in FACTORIO_PROCESS_NAMES:
        return True

    proc = (name or "").strip().lower()
    # Exact process name, not a substring of "factorio-trace" or "Factorio Wiki".
    if proc in FACTORIO_PROCESS_NAMES:
        return True
    if proc.endswith(".exe") and proc[:-4] == "factorio":
        return True

    # Window title like "Factorio" or "Factorio 2.0.72" — but not "factorio-trace"
    # and not a browser. Title match is only used together with a process name
    # that is already the game, so we do not treat titles alone as sufficient.
    return False


def title_looks_like_factorio(title: str) -> bool:
    if not title:
        return False
    if "factorio-trace" in title.lower():
        return False
    return bool(_TITLE_RE.search(title))
