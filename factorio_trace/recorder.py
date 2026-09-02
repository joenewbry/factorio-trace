"""Main record loop: Factorio-focus gated screen + HID."""

from __future__ import annotations

import time
from pathlib import Path

from factorio_trace.coords import WindowBounds
from factorio_trace.detect import factorio_window, frontmost_app
from factorio_trace.grab import grab_window
from factorio_trace.inputlog import InputTap
from factorio_trace.modsync import copy_mod_sidecar, read_active_tick
from factorio_trace.session import SessionWriter
from factorio_trace.video import VideoWriter


class Recorder:
    def __init__(self, out_dir: Path, *, fps: int = 30, contributor: str = ""):
        self.session = SessionWriter(out_dir, contributor=contributor, fps=fps)
        self.fps = fps
        self.video: VideoWriter | None = None
        self._bounds: WindowBounds | None = None
        self._running = True
        self._tap = InputTap(
            emit=self._on_input,
            bounds=lambda: self._bounds,
            focused=lambda: self.session.focused,
        )

    def stop(self) -> None:
        self._running = False

    def run(self) -> Path:
        print(f"session {self.session.id}")
        print("waiting for Factorio to be the active application…")
        print("input is discarded unless Factorio is frontmost.")
        print("Ctrl+C to stop.\n")
        self._tap.start()
        frame_dt = 1.0 / max(1, self.fps)
        last_anchor = 0.0
        try:
            while self._running:
                t0 = time.monotonic()
                self._tick()
                now = time.monotonic()
                if now - last_anchor >= 1.0:
                    tick = read_active_tick()
                    if tick is not None and self.session.focused:
                        self.session.anchor(tick)
                    last_anchor = now
                elapsed = time.monotonic() - t0
                time.sleep(max(0.0, frame_dt - elapsed))
        except KeyboardInterrupt:
            print("\nstopping…")
        finally:
            self._tap.stop()
            if self.video is not None:
                self.video.close()
            sidecar = copy_mod_sidecar(self.session.dir)
            extra = {
                "mod_sidecar": sidecar,
                "video": "video.mp4" if (self.session.dir / "video.mp4").exists() else None,
            }
            self.session.close()
            self.session.write_manifest(extra)
            print(f"saved {self.session.dir}")
            print(
                f"  frames={self.session.n_frames}  "
                f"events={self.session.n_input}  "
                f"active_s={self.session.active_ms/1000:.1f}  "
                f"mod_events={sidecar.get('events', 0)}"
            )
        return self.session.dir

    def _on_input(self, payload: dict) -> None:
        if not self.session.focused:
            return
        self.session.event(payload)

    def _tick(self) -> None:
        app = frontmost_app()
        if app is None or not app.is_factorio():
            if self.session.focused:
                reason = "focus_lost"
                if app is not None:
                    reason = f"focus_lost:{app.name}"
                self.session.pause(reason)
                print(f"paused — {reason}")
            return
        bounds = factorio_window()
        if bounds is None:
            self.session.pause("no_window")
            return
        self._bounds = bounds
        if not self.session.focused:
            self.session.resume(app.name, bounds)
            print(f"recording — {app.name} {int(bounds.width)}x{int(bounds.height)}")
        shot = grab_window(bounds)
        if shot is None:
            return
        bgra, w, h = shot
        if w < 2 or h < 2:
            return
        if self.video is None:
            self.video = VideoWriter(self.session.dir / "video.mp4", w, h, self.fps)
        try:
            self.video.write(bgra, w, h)
        except RuntimeError as exc:
            print(f"encoder: {exc}")
            return
        self.session.frame(self.video.frames - 1)
