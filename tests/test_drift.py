from pathlib import Path

from factorio_trace.actions import Action, HumanState
from factorio_trace.drift import compute_drift, score_session
from factorio_trace.policy import HoldPolicy, ReplayPolicy
from factorio_trace.session import SessionWriter


def test_identical_actions_have_zero_mouse_drift():
    human = HumanState(x=0.4, y=0.6, keys={"w"})
    pred = Action(x=0.4, y=0.6, keys=("w",))
    d = compute_drift(human, pred)
    assert d["mouse"] == 0.0
    assert d["key_agree"] == 1.0


def test_hold_policy_matches_human():
    human = HumanState(x=0.2, y=0.8, keys={"a", "d"})
    pred = HoldPolicy().predict(human, 0)
    d = compute_drift(human, pred)
    assert d["mouse"] == 0.0
    assert d["key_agree"] == 1.0


def test_mouse_drift_is_window_normalized_distance():
    human = HumanState(x=0.0, y=0.0)
    pred = Action(x=0.3, y=0.4)
    d = compute_drift(human, pred)
    assert d["mouse"] == 0.5


def test_score_session_from_shadow_files(tmp_path: Path):
    w = SessionWriter(tmp_path, contributor="t", mode="shadow", policy_name="hold")
    w.event({"t_ms": 0, "type": "mouse_move", "x": 0.1, "y": 0.1})
    w.event({"t_ms": 10, "type": "mouse_move", "x": 0.2, "y": 0.2})
    w.predicted({"t_ms": 10, "x": 0.2, "y": 0.2})
    w.predicted({"t_ms": 20, "x": 0.9, "y": 0.2})
    w.close()
    summary = score_session(w.dir)
    assert summary["n"] == 2
    assert summary["mouse_mean"] is not None
    assert summary["mouse_mean"] > 0


def test_replay_policy_reads_recorded_mouse(tmp_path: Path):
    w = SessionWriter(tmp_path, contributor="t")
    w.event({"type": "mouse_move", "x": 0.11, "y": 0.22})
    w.event({"type": "mouse_move", "x": 0.33, "y": 0.44})
    w.close()
    policy = ReplayPolicy(w.dir)
    a0 = policy.predict(HumanState(), 0)
    a1 = policy.predict(HumanState(), 1)
    assert a0.x == 0.11
    assert a1.x == 0.33
