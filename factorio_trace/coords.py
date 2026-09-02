"""Map screen-space mouse coordinates onto the Factorio window."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowBounds:
    x: float
    y: float
    width: float
    height: float

    def as_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


def normalize_mouse(
    x: float,
    y: float,
    bounds: WindowBounds,
    *,
    margin: float = 0.0,
) -> tuple[float, float] | None:
    """Return (nx, ny) in 0..1 relative to the Factorio window, or None if outside.

    Mouse events that miss the window are dropped so Slack/menu-bar activity
    never lands in the dataset even if a race slips past the focus gate.
    """
    if bounds.width <= 0 or bounds.height <= 0:
        return None
    nx = (x - bounds.x) / bounds.width
    ny = (y - bounds.y) / bounds.height
    lo, hi = -margin, 1.0 + margin
    if nx < lo or nx > hi or ny < lo or ny > hi:
        return None
    return (min(1.0, max(0.0, nx)), min(1.0, max(0.0, ny)))
