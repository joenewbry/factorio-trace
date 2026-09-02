"""Grab pixels of the Factorio window."""

from __future__ import annotations

import sys

from factorio_trace.coords import WindowBounds


def grab_window(bounds: WindowBounds) -> tuple[bytes, int, int] | None:
    if sys.platform == "darwin":
        shot = _grab_macos_window()
        if shot is not None:
            return shot
    return _grab_mss(bounds)


def _grab_macos_window() -> tuple[bytes, int, int] | None:
    try:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            CGWindowListCreateImage,
            CGRectNull,
            kCGNullWindowID,
            kCGWindowImageBoundsIgnoreFraming,
            kCGWindowListOptionIncludingWindow,
            kCGWindowListOptionOnScreenOnly,
        )
        from factorio_trace.apps import is_factorio_app
    except Exception:
        return None
    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    if not windows:
        return None
    window_id = None
    for info in windows:
        owner = str(info.get("kCGWindowOwnerName") or "")
        layer = int(info.get("kCGWindowLayer") or 0)
        if layer != 0 or not is_factorio_app(name=owner):
            continue
        bounds = info.get("kCGWindowBounds") or {}
        if float(bounds.get("Width") or 0) < 64:
            continue
        window_id = int(info.get("kCGWindowNumber"))
        break
    if window_id is None:
        return None
    image = CGWindowListCreateImage(
        CGRectNull,
        kCGWindowListOptionIncludingWindow,
        window_id,
        kCGWindowImageBoundsIgnoreFraming,
    )
    if image is None:
        return None
    try:
        from Quartz import (
            CGImageGetDataProvider,
            CGImageGetHeight,
            CGImageGetWidth,
            CGDataProviderCopyData,
            CGImageGetBytesPerRow,
        )
    except Exception:
        return None
    width = int(CGImageGetWidth(image))
    height = int(CGImageGetHeight(image))
    provider = CGImageGetDataProvider(image)
    raw = bytes(CGDataProviderCopyData(provider))
    bpr = int(CGImageGetBytesPerRow(image))
    if bpr == width * 4:
        return raw, width, height
    tight = bytearray(width * height * 4)
    for y in range(height):
        src = y * bpr
        dst = y * width * 4
        tight[dst : dst + width * 4] = raw[src : src + width * 4]
    return bytes(tight), width, height


def _grab_mss(bounds: WindowBounds) -> tuple[bytes, int, int] | None:
    try:
        import mss
    except Exception:
        return None
    monitor = {
        "left": int(bounds.x),
        "top": int(bounds.y),
        "width": int(bounds.width),
        "height": int(bounds.height),
    }
    if monitor["width"] < 2 or monitor["height"] < 2:
        return None
    with mss.mss() as sct:
        shot = sct.grab(monitor)
    return bytes(shot.bgra), int(shot.width), int(shot.height)
