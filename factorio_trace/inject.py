"""Inject a policy Action into the OS — the 'cut the wires' path."""

from __future__ import annotations

from factorio_trace.actions import Action
from factorio_trace.coords import WindowBounds


class Injector:
    def __init__(self) -> None:
        from pynput.keyboard import Controller as KeyController
        from pynput.mouse import Button, Controller as MouseController

        self.mouse = MouseController()
        self.keys = KeyController()
        self._Button = Button
        self._held_keys: set[str] = set()
        self._held_buttons: set[str] = set()

    def apply(self, action: Action, bounds: WindowBounds) -> None:
        if action.x is not None and action.y is not None and bounds.width > 0:
            sx = bounds.x + float(action.x) * bounds.width
            sy = bounds.y + float(action.y) * bounds.height
            self.mouse.position = (sx, sy)
        wanted_buttons = set(action.buttons)
        for name in self._held_buttons - wanted_buttons:
            self.mouse.release(self._button(name))
        for name in wanted_buttons - self._held_buttons:
            self.mouse.press(self._button(name))
        self._held_buttons = wanted_buttons

        wanted_keys = set(action.keys)
        for name in self._held_keys - wanted_keys:
            self.keys.release(name)
        for name in wanted_keys - self._held_keys:
            self.keys.press(name)
        self._held_keys = wanted_keys

    def release_all(self) -> None:
        for name in list(self._held_buttons):
            self.mouse.release(self._button(name))
        for name in list(self._held_keys):
            try:
                self.keys.release(name)
            except Exception:
                pass
        self._held_buttons.clear()
        self._held_keys.clear()

    def _button(self, name: str):
        return getattr(self._Button, name, self._Button.left)
