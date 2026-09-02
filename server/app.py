"""Public Factorio Trace catalog and ingest."""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

ROOT = Path(os.environ.get("FACTORIO_TRACE_DATA", Path(__file__).resolve().parent / "data"))
SESSIONS = ROOT / "sessions"
STATIC = Path(__file__).resolve().parent / "static"
TOKEN = os.environ.get("FACTORIO_TRACE_TOKEN", "nauvis-open-dataset")
MAX_BYTES = int(os.environ.get("FACTORIO_TRACE_MAX_BYTES", str(4 * 1024 * 1024 * 1024)))

SESSIONS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Factorio Trace", version="0.1.0")


def _index() -> list[dict]:
    rows = []
    for path in sorted(SESSIONS.iterdir(), reverse=True):
        man = path / "manifest.json"
        if not man.exists():
            continue
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        video = path / "video.mp4"
        rows.append(
            {
                "id": data.get("id", path.name),
                "contributor": data.get("contributor") or "anonymous",
                "duration_ms": data.get("duration_ms", 0),
                "active_ms": data.get("active_ms", 0),
                "video_frames": data.get("video_frames", 0),
                "input_events": data.get("input_events", 0),
                "has_video": video.exists(),
                "has_mod": (path / "game.jsonl").exists(),
                "bytes": _dir_size(path),
            }
        )
    return rows


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


@app.get("/api/status")
def status():
    rows = _index()
    return {
        "ok": True,
        "sessions": len(rows),
        "bytes": sum(r["bytes"] for r in rows),
        "now": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/sessions")
def list_sessions():
    return {"sessions": _index()}


@app.get("/api/sessions/{session_id}/manifest")
def get_manifest(session_id: str):
    path = SESSIONS / session_id / "manifest.json"
    if not path.exists():
        raise HTTPException(404, "unknown session")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/sessions/{session_id}/video")
def get_video(session_id: str):
    path = SESSIONS / session_id / "video.mp4"
    if not path.exists():
        raise HTTPException(404, "no video")
    return FileResponse(path, media_type="video/mp4")


@app.post("/api/sessions")
async def ingest(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    expected = f"Bearer {TOKEN}"
    if authorization != expected:
        raise HTTPException(401, "bad token")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "session too large")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "not a zip") from exc
    for name in zf.namelist():
        if name.startswith("/") or ".." in Path(name).parts:
            raise HTTPException(400, "bad zip path")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zf.extractall(tmp_path)
        manifest = tmp_path / "manifest.json"
        if not manifest.exists():
            nested = list(tmp_path.glob("*/manifest.json"))
            if len(nested) == 1:
                tmp_path = nested[0].parent
                manifest = nested[0]
            else:
                raise HTTPException(400, "zip must contain manifest.json")
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "bad manifest") from exc
        if data.get("recorder") != "factorio-trace":
            raise HTTPException(400, "recorder must be factorio-trace")
        session_id = str(data.get("id") or "").strip()
        if not session_id or "/" in session_id or ".." in session_id:
            raise HTTPException(400, "bad session id")
        dest = SESSIONS / session_id
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(tmp_path, dest)
    return {"ok": True, "id": session_id, "url": f"/api/sessions/{session_id}/manifest"}


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/schema")
def schema_page():
    readme = Path(__file__).resolve().parent.parent / "schema" / "trace-v0.md"
    if readme.exists():
        return FileResponse(readme, media_type="text/markdown")
    raise HTTPException(404, "schema missing")
