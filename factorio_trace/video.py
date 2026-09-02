"""Encode Factorio-window frames to H.264 via ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg


class VideoWriter:
    def __init__(self, path: Path, width: int, height: int, fps: int):
        self.path = Path(path)
        self.width = int(width)
        self.height = int(height)
        if self.width % 2:
            self.width -= 1
        if self.height % 2:
            self.height -= 1
        self.fps = fps
        self.frames = 0
        ffmpeg = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgra",
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            str(self.path),
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, bgra: bytes, src_width: int, src_height: int) -> None:
        if self.proc.poll() is not None or self.proc.stdin is None:
            raise RuntimeError("ffmpeg exited while encoding")
        frame = _fit_bgra(bgra, src_width, src_height, self.width, self.height)
        self.proc.stdin.write(frame)
        self.frames += 1

    def close(self) -> None:
        if self.proc.stdin:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        self.proc.wait(timeout=30)


def _fit_bgra(buf: bytes, src_w: int, src_h: int, dst_w: int, dst_h: int) -> bytes:
    expected = src_w * src_h * 4
    if len(buf) < expected:
        buf = buf + bytes(expected - len(buf))
    if src_w == dst_w and src_h == dst_h:
        return buf[:expected]
    # Crop top-left to even encoder size. Avoid a numpy dependency.
    out = bytearray(dst_w * dst_h * 4)
    row_src = src_w * 4
    row_dst = dst_w * 4
    copy_w = min(src_w, dst_w) * 4
    for y in range(min(src_h, dst_h)):
        s = y * row_src
        d = y * row_dst
        out[d : d + copy_w] = buf[s : s + copy_w]
    return bytes(out)
