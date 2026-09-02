"""Main loop: record, shadow (wires still connected), or closed-loop (wires cut)."""

from __future__ import annotations

import time
from pathlib import Path

from factorio_trace.actions import CLOSED_LOOP, RECORD, HumanState
from factorio_trace.coords import WindowBounds
from factorio_trace.detect import factorio_window, frontmost_app
from factorio_trace.drift import compute_drift, summarize_drift
from factorio_trace.grab import grab_window
from factorio_trace.inputlog import InputTap
from factorio_trace.modsync import copy_mod_sidecar, read_active_tick
from factorio_trace.policy import Policy
from factorio_trace.session import SessionWriter
from factorio_trace.video import VideoWriter


class Recorder:
    def __init__(
        self,
        out_dir: Path,
        *,
        fps: int = 30,
        contributor: str = "",
        mode: str = RECORD,
        policy: Policy | None = None,
    ):
        self.mode = mode
        self.policy = policy
        self.session = SessionWriter(
            out_dir,
            contributor=contributor,
            fps=fps,
            mode=mode,
            policy_name=policy.name if policy else "",
        )
        self.fps = fps
        self.video: VideoWriter | None = None
        self._bounds: WindowBounds | None = None
        self._running = True
        self.human = HumanState()
        self._injecting = False
        self._injector = None
        self._drift_rows: list[dict] = []
        self._hud_at = 0.0
        self._tap = InputTap(
            emit=self._on_input,
            bounds=lambda: self._bounds,
            focused=lambda: self.session.focused,
        )

    def stop(self) -> None:
        self._running = False

    def run(self) -> Path:
        print(f"session {self.session.id}  mode={self.mode}")
        if self.mode == RECORD:
            print("joystick connected — you play, we record.")
        elif self.mode == SHADOW:
            print("joystick connected — you play. policy predicts. drift is scored. nothing is injected.")
        elif self.mode == CLOSED_LOOP:
            print("wires cut — policy drives mouse/keys. your HID is logged as intent only.")
            from factorio_trace.inject import Injector

            self._injector = Injector()
        print("waiting for Factorio to be the active application…")
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
            if self._injector is not None:
                self._injector.release_all()
            if self.video is not None:
                self.video.close()
            sidecar = copy_mod_sidecar(self.session.dir)
            extra = {
                "mod_sidecar": sidecar,
                "video": "video.mp4" if (self.session.dir / "video.mp4").exists() else None,
                "drift": summarize_drift(self._drift_rows) if self._drift_rows else None,
            }
            self.session.close()
            self.session.write_manifest(extra)
            print(f"saved {self.session.dir}")
            print(
                f"  frames={self.session.n_frames}  "
                f"events={self.session.n_input}  "
                f"predicted={self.session.n_predicted}  "
                f"active_s={self.session.active_ms/1000:.1f}  "
                f"mod_events={sidecar.get('events', 0)}"
            )
            if extra["drift"]:
                d = extra["drift"]
                print(
                    f"  drift mouse_mean={d['mouse_mean']}  "
                    f"key_agree={d['key_agree_mean']}"
                )
        return self.session.dir

    def _on_input(self, payload: dict) -> None:
        if not self.session.focused:
            return
        if self._injecting:
            return
        self.human.apply(payload)
        if self.mode == CLOSED_LOOP:
            self.session.intent(payload)
        else:
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
            print(f"{self.mode} — {app.name} {int(bounds.width)}x{int(bounds.height)}")
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
        frame_i = self.video.frames - 1
        self.session.frame(frame_i)
        if self.policy is None:
            return
        pred = self.policy.predict(self.human, frame_i)
        self.session.predicted({"i": frame_i, **pred.as_dict()})
        row = compute_drift(self.human, pred)
        row["i"] = frame_i
        self.session.drift(row)
        self._drift_rows.append(row)
        if self.mode == CLOSED_LOOP and self._injector is not None:
            self._injecting = True
            try:
                self._injector.apply(pred, bounds)
            finally:
                self._injecting = False
        now = time.monotonic()
        if now - self._hud_at >= 1.0:
            self._hud_at = now
            mouse = row.get("mouse")
            mouse_s = "n/a" if mouse is None else f"{mouse:.3f}"
            print(
                f"\r{self.mode}  mouse_delta {mouse_s}  keys {row['key_agree']:.2f}  frame {frame_i}   ",
                end="",
                flush=True,
            )
