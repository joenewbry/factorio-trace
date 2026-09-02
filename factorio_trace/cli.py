"""factorio-trace command line."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from factorio_trace import DEFAULT_UPLOAD_TOKEN, DEFAULT_UPLOAD_URL, __version__
from factorio_trace.actions import CLOSED_LOOP, RECORD, SHADOW
from factorio_trace.detect import factorio_window, frontmost_app
from factorio_trace.drift import score_session
from factorio_trace.mod_install import doctor as mod_doctor
from factorio_trace.mod_install import install_mod
from factorio_trace.paths import sessions_dir
from factorio_trace.policy import load_policy
from factorio_trace.recorder import Recorder
from factorio_trace.upload import upload_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="factorio-trace",
        description="Record Factorio play (screen + mouse + keys) for the open dataset.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="you play; we record (joystick connected)")
    _add_common_record_args(rec)

    sh = sub.add_parser("shadow", help="you play; policy predicts; drift scored; nothing injected")
    _add_common_record_args(sh)
    sh.add_argument("--policy", default="hold", help="none|hold|replay")
    sh.add_argument("--from", dest="replay_from", type=Path, default=None)

    play = sub.add_parser("play", help="wires cut: policy drives Factorio")
    _add_common_record_args(play)
    play.add_argument("--policy", default="replay", help="hold|replay")
    play.add_argument("--from", dest="replay_from", type=Path, default=None)
    play.add_argument(
        "--cut-wires",
        action="store_true",
        help="required. injects mouse/keys. your HID is intent-only.",
    )

    sc = sub.add_parser("score", help="summarize drift on a shadow/play session")
    sc.add_argument("session", type=Path)

    up = sub.add_parser("upload", help="upload an existing session directory")
    up.add_argument("session", type=Path)
    up.add_argument("--url", default=os.environ.get("FACTORIO_TRACE_URL", DEFAULT_UPLOAD_URL))
    up.add_argument("--token", default=os.environ.get("FACTORIO_TRACE_TOKEN", DEFAULT_UPLOAD_TOKEN))

    sub.add_parser("install-mod", help="copy the Lua sidecar into Factorio/mods")
    sub.add_parser("doctor", help="check Factorio paths, focus detection, encoder")
    sub.add_parser("status", help="print the current frontmost app and Factorio window")

    args = parser.parse_args(argv)
    if args.cmd == "record":
        return cmd_loop(args, RECORD, policy_kind="none")
    if args.cmd == "shadow":
        return cmd_loop(args, SHADOW, policy_kind=args.policy)
    if args.cmd == "play":
        if not args.cut_wires:
            print("refusing to inject input without --cut-wires")
            return 2
        return cmd_loop(args, CLOSED_LOOP, policy_kind=args.policy)
    if args.cmd == "score":
        return cmd_score(args)
    if args.cmd == "upload":
        return cmd_upload(args)
    if args.cmd == "install-mod":
        dest = install_mod()
        print(f"installed {dest}")
        print("restart Factorio (or reload mods) so the sidecar starts writing game.jsonl")
        return 0
    if args.cmd == "doctor":
        return cmd_doctor()
    if args.cmd == "status":
        return cmd_status()
    return 2


def _add_common_record_args(p) -> None:
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--contributor", default=os.environ.get("FACTORIO_TRACE_CONTRIBUTOR", ""))
    p.add_argument("--upload", action="store_true", help="upload when the session ends")
    p.add_argument("--yes", action="store_true", help="skip the upload confirmation prompt")
    p.add_argument("--url", default=os.environ.get("FACTORIO_TRACE_URL", DEFAULT_UPLOAD_URL))
    p.add_argument("--token", default=os.environ.get("FACTORIO_TRACE_TOKEN", DEFAULT_UPLOAD_TOKEN))


def cmd_loop(args, mode: str, policy_kind: str) -> int:
    out = args.out or sessions_dir()
    out.mkdir(parents=True, exist_ok=True)
    replay_from = getattr(args, "replay_from", None)
    try:
        policy = load_policy(policy_kind, replay_from)
    except ValueError as exc:
        print(exc)
        return 2
    rec = Recorder(out, fps=args.fps, contributor=args.contributor, mode=mode, policy=policy)
    session = rec.run()
    if args.upload:
        if not args.yes:
            ans = input("upload this session to the public dataset? [y/N] ").strip().lower()
            if ans not in {"y", "yes"}:
                print("kept local only")
                return 0
        info = upload_session(session, url=args.url, token=args.token)
        print("uploaded", info)
    return 0


def cmd_score(args) -> int:
    summary = score_session(args.session)
    print(summary)
    return 0


def cmd_upload(args) -> int:
    info = upload_session(args.session, url=args.url, token=args.token)
    print("uploaded", info)
    return 0


def cmd_doctor() -> int:
    print(f"factorio-trace {__version__}")
    for line in mod_doctor():
        print(" ", line)
    try:
        import imageio_ffmpeg

        print("  ffmpeg:", imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as exc:
        print("  ffmpeg: missing", exc)
    app = frontmost_app()
    if app:
        print(f"  frontmost: {app.name!r} bundle={app.bundle_id!r} factorio={app.is_factorio()}")
    else:
        print("  frontmost: unknown")
    bounds = factorio_window()
    if bounds:
        print(f"  factorio window: {bounds.width:.0f}x{bounds.height:.0f} at {bounds.x:.0f},{bounds.y:.0f}")
    else:
        print("  factorio window: not found")
    if sys.platform == "darwin":
        print("  macOS permissions needed: Screen Recording + Accessibility / Input Monitoring")
        print("    System Settings → Privacy & Security → grant them to Terminal (or iTerm).")
    elif sys.platform.startswith("win"):
        print("  Windows: run from a normal (not-as-admin) PowerShell unless Factorio itself is admin.")
        print("    If capture is a black frame, use borderless windowed Factorio, not exclusive fullscreen.")
    return 0


def cmd_status() -> int:
    app = frontmost_app()
    print("frontmost:", None if app is None else app)
    print("window:", factorio_window())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
