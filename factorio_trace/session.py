"""Write a Factorio Trace session directory."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from factorio_trace import SCHEMA_VERSION, __version__
from factorio_trace.coords import WindowBounds


def new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


class SessionWriter:
    def __init__(
        self,
        root: Path,
        *,
        contributor: str = "",
        fps: int = 30,
    ):
        self.id = new_session_id()
        self.dir = Path(root) / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.contributor = contributor
        self.t0_ns = time.time_ns()
        self.input_path = self.dir / "input.jsonl"
        self.frames_path = self.dir / "frames.jsonl"
        self.anchors_path = self.dir / "anchors.jsonl"
        self._input = self.input_path.open("a", encoding="utf-8")
        self._frames = self.frames_path.open("a", encoding="utf-8")
        self._anchors = self.anchors_path.open("a", encoding="utf-8")
        self.n_input = 0
        self.n_frames = 0
        self.n_pauses = 0
        self.active_ms = 0
        self._last_resume_ms: int | None = None
        self.bounds: WindowBounds | None = None
        self.focused = False

    def now_ms(self) -> int:
        return int((time.time_ns() - self.t0_ns) / 1_000_000)

    def event(self, payload: dict) -> None:
        payload.setdefault("t_ms", self.now_ms())
        self._input.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.n_input += 1
        if self.n_input % 50 == 0:
            self._input.flush()

    def frame(self, video_index: int) -> None:
        line = {"i": video_index, "t_ms": self.now_ms()}
        self._frames.write(json.dumps(line, separators=(",", ":")) + "\n")
        self.n_frames += 1

    def anchor(self, game_tick: int) -> None:
        line = {"t_ms": self.now_ms(), "game_tick": int(game_tick)}
        self._anchors.write(json.dumps(line, separators=(",", ":")) + "\n")

    def resume(self, app: str, bounds: WindowBounds) -> None:
        self.bounds = bounds
        if self.focused:
            return
        self.focused = True
        self._last_resume_ms = self.now_ms()
        self.event(
            {
                "type": "resume",
                "app": app,
                "bounds": bounds.as_dict(),
            }
        )

    def pause(self, reason: str) -> None:
        if not self.focused:
            return
        now = self.now_ms()
        if self._last_resume_ms is not None:
            self.active_ms += now - self._last_resume_ms
            self._last_resume_ms = None
        self.focused = False
        self.n_pauses += 1
        self.event({"type": "pause", "reason": reason})

    def write_manifest(self, extra: dict | None = None) -> None:
        if self.focused and self._last_resume_ms is not None:
            self.active_ms += self.now_ms() - self._last_resume_ms
            self._last_resume_ms = self.now_ms()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "recorder": "factorio-trace",
            "recorder_version": __version__,
            "contributor": self.contributor,
            "started_unix_ns": self.t0_ns,
            "fps": self.fps,
            "input_events": self.n_input,
            "video_frames": self.n_frames,
            "pauses": self.n_pauses,
            "active_ms": self.active_ms,
            "duration_ms": self.now_ms(),
            "license": "CC-BY-4.0",
            "capture": {
                "pixels": "factorio-window",
                "input": "os-hid-gated-on-factorio-focus",
                "game_state": "factorio-mod-optional",
            },
        }
        if extra:
            manifest.update(extra)
        path = self.dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def close(self) -> None:
        self.pause("session_stop")
        for fh in (self._input, self._frames, self._anchors):
            try:
                fh.flush()
                fh.close()
            except OSError:
                pass
        self.write_manifest()
