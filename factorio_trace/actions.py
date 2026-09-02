"""Shared action / human-intent types for record, shadow, and closed-loop."""

from __future__ import annotations

from dataclasses import dataclass, field


RECORD = "record"
SHADOW = "shadow"
CLOSED_LOOP = "closed_loop"

MODES = (RECORD, SHADOW, CLOSED_LOOP)


@dataclass
class Action:
    x: float | None = None
    y: float | None = None
    buttons: tuple[str, ...] = ()
    keys: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        out: dict = {}
        if self.x is not None:
            out["x"] = round(float(self.x), 5)
        if self.y is not None:
            out["y"] = round(float(self.y), 5)
        if self.buttons:
            out["buttons"] = list(self.buttons)
        if self.keys:
            out["keys"] = list(self.keys)
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        buttons = data.get("buttons") or ()
        keys = data.get("keys") or ()
        if data.get("type") == "mouse_down":
            buttons = (data.get("button") or "left",)
        return cls(
            x=data.get("x"),
            y=data.get("y"),
            buttons=tuple(buttons),
            keys=tuple(keys),
        )


@dataclass
class HumanState:
    x: float | None = None
    y: float | None = None
    buttons: set[str] = field(default_factory=set)
    keys: set[str] = field(default_factory=set)

    def apply(self, event: dict) -> None:
        kind = event.get("type")
        if kind in {"mouse_move", "mouse_down", "mouse_up", "mouse_scroll"}:
            if "x" in event:
                self.x = event["x"]
            if "y" in event:
                self.y = event["y"]
        if kind == "mouse_down":
            self.buttons.add(str(event.get("button") or "left"))
        elif kind == "mouse_up":
            self.buttons.discard(str(event.get("button") or "left"))
        elif kind == "key_down":
            self.keys.add(str(event.get("key")))
        elif kind == "key_up":
            self.keys.discard(str(event.get("key")))

    def snapshot(self) -> Action:
        return Action(
            x=self.x,
            y=self.y,
            buttons=tuple(sorted(self.buttons)),
            keys=tuple(sorted(k for k in self.keys if k and k != "unknown")),
        )
