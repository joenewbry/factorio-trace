"""Frontmost-app and Factorio window detection (macOS, Windows, Linux)."""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

from factorio_trace.apps import FrontmostApp, is_factorio_app
from factorio_trace.coords import WindowBounds


def frontmost_app() -> Optional[FrontmostApp]:
    if sys.platform == "darwin":
        return _frontmost_macos()
    if sys.platform.startswith("win"):
        return _frontmost_windows()
    return _frontmost_linux()


def factorio_window() -> Optional[WindowBounds]:
    if sys.platform == "darwin":
        return _window_macos()
    if sys.platform.startswith("win"):
        return _window_windows()
    return _window_linux()


def _frontmost_macos() -> Optional[FrontmostApp]:
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        name = str(app.localizedName() or "")
        bundle = str(app.bundleIdentifier() or "")
        pid = int(app.processIdentifier() or 0)
        return FrontmostApp(name=name, bundle_id=bundle, pid=pid)
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first application process whose frontmost is true',
            ],
            timeout=1,
            text=True,
        ).strip()
        if out:
            return FrontmostApp(name=out)
    except Exception:
        return None
    return None


def _window_macos() -> Optional[WindowBounds]:
    try:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListOptionOnScreenOnly,
        )
    except Exception:
        return None
    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    if not windows:
        return None
    for info in windows:
        owner = str(info.get("kCGWindowOwnerName") or "")
        layer = int(info.get("kCGWindowLayer") or 0)
        if layer != 0:
            continue
        if not is_factorio_app(name=owner):
            continue
        bounds = info.get("kCGWindowBounds") or {}
        w = float(bounds.get("Width") or 0)
        h = float(bounds.get("Height") or 0)
        if w < 64 or h < 64:
            continue
        return WindowBounds(
            x=float(bounds.get("X") or 0),
            y=float(bounds.get("Y") or 0),
            width=w,
            height=h,
        )
    return None


def _frontmost_windows() -> Optional[FrontmostApp]:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        exe = ""
        if handle:
            try:
                size = wintypes.DWORD(32768)
                exe_buf = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(handle, 0, exe_buf, ctypes.byref(size)):
                    exe = exe_buf.value
            finally:
                kernel32.CloseHandle(handle)
        exe_base = exe.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] if exe else ""
        return FrontmostApp(
            name=exe_base or buf.value,
            pid=int(pid.value),
            exe=exe,
            window_title=buf.value,
        )
    except Exception:
        return None


def _window_windows() -> Optional[WindowBounds]:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        app = _frontmost_windows()
        if app is None or not app.is_factorio():
            return None
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return WindowBounds(
            x=float(rect.left),
            y=float(rect.top),
            width=float(rect.right - rect.left),
            height=float(rect.bottom - rect.top),
        )
    except Exception:
        return None


def _frontmost_linux() -> Optional[FrontmostApp]:
    try:
        out = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowname"],
            timeout=1,
            text=True,
        ).strip()
        pid_s = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowpid"],
            timeout=1,
            text=True,
        ).strip()
        exe = ""
        if pid_s.isdigit():
            proc = f"/proc/{pid_s}/comm"
            try:
                exe = open(proc, encoding="utf-8").read().strip()
            except OSError:
                exe = ""
        return FrontmostApp(
            name=exe or out,
            pid=int(pid_s) if pid_s.isdigit() else 0,
            exe=exe,
            window_title=out,
        )
    except Exception:
        return None


def _window_linux() -> Optional[WindowBounds]:
    try:
        geom = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowgeometry", "--shell"],
            timeout=1,
            text=True,
        )
        vals = {}
        for line in geom.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k] = v
        app = _frontmost_linux()
        if app is None or not app.is_factorio():
            return None
        return WindowBounds(
            x=float(vals.get("X", 0)),
            y=float(vals.get("Y", 0)),
            width=float(vals.get("WIDTH", 0)),
            height=float(vals.get("HEIGHT", 0)),
        )
    except Exception:
        return None
