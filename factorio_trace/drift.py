"""Drift between human intent and a policy — the 'wires cut' score."""

from __future__ import annotations

import json
import math
from pathlib import Path

from factorio_trace.actions import Action, HumanState


def compute_drift(human: HumanState | Action, pred: Action) -> dict:
    hx = human.x if isinstance(human, (HumanState, Action)) else None
    hy = human.y if isinstance(human, (HumanState, Action)) else None
    mouse = None
    if hx is not None and hy is not None and pred.x is not None and pred.y is not None:
        mouse = math.hypot(float(hx) - float(pred.x), float(hy) - float(pred.y))
    if isinstance(human, HumanState):
        keys_h = set(human.keys)
        buttons_h = set(human.buttons)
    else:
        keys_h = set(human.keys)
        buttons_h = set(human.buttons)
    keys_p = set(pred.keys)
    union = keys_h | keys_p
    key_agree = 1.0 if not union else len(keys_h & keys_p) / len(union)
    b_union = buttons_h | set(pred.buttons)
    button_agree = 1.0 if not b_union else len(buttons_h & set(pred.buttons)) / len(b_union)
    return {
        "mouse": None if mouse is None else round(mouse, 5),
        "key_agree": round(key_agree, 4),
        "button_agree": round(button_agree, 4),
    }


def summarize_drift(rows: list[dict]) -> dict:
    mice = [r["mouse"] for r in rows if r.get("mouse") is not None]
    keys = [r["key_agree"] for r in rows if "key_agree" in r]
    return {
        "n": len(rows),
        "mouse_mean": round(sum(mice) / len(mice), 5) if mice else None,
        "mouse_p95": _percentile(mice, 0.95) if mice else None,
        "key_agree_mean": round(sum(keys) / len(keys), 4) if keys else None,
    }


def score_session(session_dir: Path) -> dict:
    session_dir = Path(session_dir)
    pred_path = session_dir / "predicted.jsonl"
    intent_path = session_dir / "intent.jsonl"
    input_path = intent_path if intent_path.exists() and intent_path.stat().st_size > 0 else session_dir / "input.jsonl"
    if not pred_path.exists():
        raise FileNotFoundError(
            f"{session_dir} has no predicted.jsonl — record a shadow or closed-loop session"
        )
    human = HumanState()
    human_by_ms: list[tuple[int, Action]] = []
    if input_path.exists():
        for line in input_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            human.apply(ev)
            human_by_ms.append((int(ev.get("t_ms", 0)), human.snapshot()))
    rows = []
    for line in pred_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pred_ev = json.loads(line)
        t = int(pred_ev.get("t_ms", 0))
        pred = Action.from_dict(pred_ev)
        intent = _last_at(human_by_ms, t)
        if intent is None:
            continue
        row = compute_drift(intent, pred)
        row["t_ms"] = t
        rows.append(row)
    summary = summarize_drift(rows)
    summary["session"] = session_dir.name
    return summary


def _last_at(series: list[tuple[int, Action]], t_ms: int) -> Action | None:
    last = None
    for ts, action in series:
        if ts > t_ms:
            break
        last = action
    return last


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return round(s[idx], 5)
