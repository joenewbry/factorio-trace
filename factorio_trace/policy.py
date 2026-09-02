"""Policies that turn pixels + human state into an Action.

Plug a trained net in here later. HoldPolicy and ReplayPolicy exist so the
shadow / closed-loop plumbing can be tested before a checkpoint exists.
"""

from __future__ import annotations

import json
from pathlib import Path

from factorio_trace.actions import Action, HumanState


class Policy:
    name = "base"

    def predict(self, human: HumanState, frame_index: int) -> Action:
        raise NotImplementedError


class HoldPolicy(Policy):
    """Copy the last human action. Shadow drift should sit near zero."""

    name = "hold"

    def predict(self, human: HumanState, frame_index: int) -> Action:
        return human.snapshot()


class ReplayPolicy(Policy):
    """Replay mouse/keys from an earlier session as the 'decoder'.

    Used to dry-run shadow/play: the factory still runs under the human,
    while a ghost of a previous session is scored as if it were the net.
    """

    name = "replay"

    def __init__(self, session_dir: Path):
        self.session_dir = Path(session_dir)
        self.actions: list[Action] = []
        path = self.session_dir / "input.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        last = Action()
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            kind = ev.get("type")
            if kind == "mouse_move":
                last = Action(x=ev.get("x"), y=ev.get("y"), buttons=last.buttons, keys=last.keys)
                self.actions.append(last)
            elif kind == "mouse_down":
                last = Action(
                    x=ev.get("x", last.x),
                    y=ev.get("y", last.y),
                    buttons=(str(ev.get("button") or "left"),),
                    keys=last.keys,
                )
                self.actions.append(last)
            elif kind == "key_down":
                keys = tuple(sorted(set(last.keys) | {str(ev.get("key"))}))
                last = Action(x=last.x, y=last.y, buttons=last.buttons, keys=keys)
                self.actions.append(last)
        if not self.actions:
            self.actions = [Action()]

    def predict(self, human: HumanState, frame_index: int) -> Action:
        return self.actions[min(frame_index, len(self.actions) - 1)]


def load_policy(kind: str, replay_from: Path | None = None) -> Policy | None:
    if not kind or kind in {"none", "off"}:
        return None
    if kind == "hold":
        return HoldPolicy()
    if kind == "replay":
        if replay_from is None:
            raise ValueError("replay policy needs --from SESSION")
        return ReplayPolicy(replay_from)
    raise ValueError(f"unknown policy {kind!r} (none|hold|replay)")
