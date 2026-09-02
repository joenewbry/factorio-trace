# Training loop (the monkey / cut-wires design)

This is the same eval shape as the arcade Screen-Self-Driving bots, and the
same idea as the primate BMI experiments: a subject plays a game, a decoder
is trained on that play, then you **cut the joystick** and see whether the
decoder still plays. The monkey did not know the wires were cut. Drift is
the score.

```
record  →  train  →  shadow  →  play
  you         net      you+net     net
  drives               you drive    net drives
                       net scored   you are intent
```

| Mode | Who drives Factorio | What we log | Analog |
|---|---|---|---|
| `record` | human | pixels + HID + game.jsonl | joystick connected, collect data |
| `shadow` | human | that, plus `predicted.jsonl` and `drift.jsonl` | joystick connected, decoder scored, nothing injected |
| `play` (`--cut-wires`) | policy | `intent.jsonl` (your HID) vs injected actions | wires cut |

Shadow is PREVIEW in the arcade inference engine. Play is AUTO.

## Commands

```bash
# 1. Collect. This is what you do on the work laptop tonight.
factorio-trace record --contributor joe --upload --yes

# 2. After a net exists, sit in the game and watch disagreement without
#    giving the net the mouse. HoldPolicy is a sanity check (drift ≈ 0).
factorio-trace shadow --policy hold
factorio-trace shadow --policy replay --from ~/.factorio-trace/sessions/<id>

# 3. Cut the wires. Required flag so this cannot happen by accident.
factorio-trace play --cut-wires --policy replay --from ~/.factorio-trace/sessions/<id>

# Offline score
factorio-trace score ~/.factorio-trace/sessions/<id>
```

A real checkpoint plugs in as a `Policy` in `factorio_trace/policy.py`
(`predict(human, frame_index) -> Action`). Do not change the session schema
to add a model — add a policy class.

## What "drift" is

Per frame, while Factorio is focused:

- **mouse** — Euclidean distance in window-normalized 0..1 coordinates
  between human cursor and predicted cursor
- **key_agree** — Jaccard overlap of held keys
- **button_agree** — same for mouse buttons

`play` also writes Lua `game.jsonl` (builds, research, production snapshots)
so factory outcome can be compared to a human baseline of the same map.

## Why record is enough tonight

Training needs pixels aligned to HID. `record` already writes that.
`shadow` / `play` reuse the same session directory shape, so a net trained
on tonight's uploads can be dropped in without recapturing.
