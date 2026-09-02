"""Zip a session and POST it to the public dataset."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import httpx

from factorio_trace import DEFAULT_UPLOAD_TOKEN, DEFAULT_UPLOAD_URL

SKIP_SUFFIXES = {".tmp", ".lock"}


def pack_session(session_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(session_dir.rglob("*")):
            if path.is_dir():
                continue
            if path.suffix in SKIP_SUFFIXES:
                continue
            zf.write(path, path.relative_to(session_dir).as_posix())
    return buf.getvalue()


def upload_session(
    session_dir: Path,
    *,
    url: str = DEFAULT_UPLOAD_URL,
    token: str = DEFAULT_UPLOAD_TOKEN,
    timeout: float = 600.0,
) -> dict:
    session_dir = Path(session_dir)
    manifest_path = session_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest.json in {session_dir}")
    payload = pack_session(session_dir)
    endpoint = url.rstrip("/") + "/api/sessions"
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (session_dir.name + ".zip", payload, "application/zip")}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(endpoint, headers=headers, files=files)
        resp.raise_for_status()
        return resp.json()


def validate_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("schema_version", "id", "recorder"):
        if key not in data:
            raise ValueError(f"manifest missing {key}")
    if data.get("recorder") != "factorio-trace":
        raise ValueError("manifest.recorder must be factorio-trace")
    return data
