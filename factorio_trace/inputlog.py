"""HID listener. Events are only committed while Factorio is focused."""

from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard, mouse

from factorio_trace.coords import WindowBounds, normalize_mouse


class InputTap:
    def __init__(
        self,
        emit: Callable[[dict], None],
        bounds: Callable[[], WindowBounds | None],
        focused: Callable[[], bool],
    ):
        self._emit = emit
        self._bounds = bounds
        self._focused = focused
        self._mouse: mouse.Listener | None = None
        self._keys: keyboard.Listener | None = None
        self._last_move_ms = 0.0
        self._lock = threading.Lock()

    def start(self) -> None:
        self._mouse = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._keys = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._mouse.start()
        self._keys.start()

    def stop(self) -> None:
        for listener in (self._mouse, self._keys):
            if listener is not None:
                listener.stop()

    def _gate(self) -> WindowBounds | None:
        if not self._focused():
            return None
        return self._bounds()

    def _on_move(self, x: float, y: float) -> None:
        import time

        now = time.monotonic()
        if now - self._last_move_ms < 0.02:
            return
        bounds = self._gate()
        if bounds is None:
            return
        xy = normalize_mouse(x, y, bounds)
        if xy is None:
            return
        self._last_move_ms = now
        self._emit({"type": "mouse_move", "x": round(xy[0], 5), "y": round(xy[1], 5)})

    def _on_click(self, x: float, y: float, button, pressed: bool) -> None:
        bounds = self._gate()
        if bounds is None:
            return
        xy = normalize_mouse(x, y, bounds)
        if xy is None:
            return
        self._emit(
            {
                "type": "mouse_down" if pressed else "mouse_up",
                "button": str(button).replace("Button.", ""),
                "x": round(xy[0], 5),
                "y": round(xy[1], 5),
            }
        )

    def _on_scroll(self, x: float, y: float, dx: float, dy: float) -> None:
        bounds = self._gate()
        if bounds is None:
            return
        xy = normalize_mouse(x, y, bounds)
        if xy is None:
            return
        self._emit(
            {
                "type": "mouse_scroll",
                "dx": dx,
                "dy": dy,
                "x": round(xy[0], 5),
                "y": round(xy[1], 5),
            }
        )

    def _on_press(self, key) -> None:
        if self._gate() is None:
            return
        self._emit({"type": "key_down", **_key_fields(key)})

    def _on_release(self, key) -> None:
        if self._gate() is None:
            return
        self._emit({"type": "key_up", **_key_fields(key)})


def _key_fields(key) -> dict:
    name = None
    code = None
    char = None
    try:
        name = key.char
        char = key.char
    except AttributeError:
        name = str(key).replace("Key.", "")
    try:
        if hasattr(key, "vk") and key.vk is not None:
            code = int(key.vk)
        elif hasattr(key, "value") and hasattr(key.value, "vk"):
            code = int(key.value.vk)
    except Exception:
        code = None
    out = {"key": name or "unknown"}
    if char:
        out["char"] = char
    if code is not None:
        out["vk"] = code
    return out
