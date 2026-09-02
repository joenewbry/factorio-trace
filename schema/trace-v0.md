# Factorio Trace schema v0

A session is a directory:

```
<id>/
  manifest.json
  video.mp4          # H.264, Factorio window only, focused segments concatenated
  frames.jsonl       # video frame index → wall t_ms
  input.jsonl        # HID events, Factorio-focus gated
  anchors.jsonl      # wall t_ms ↔ game tick (when the Lua mod is installed)
  game.jsonl         # optional Lua sidecar
```

`t_ms` is milliseconds since session start (wall clock). Pauses omit video frames
and HID. Join video frame `i` to inputs by `frames.jsonl`.

Mouse `x`/`y` are 0..1 relative to the Factorio window, not the desktop.

Input event `type` values: `resume`, `pause`, `mouse_move`, `mouse_down`,
`mouse_up`, `mouse_scroll`, `key_down`, `key_up`.

Game sidecar `type` values: `tick`, `built`, `mined`, `rotated`, `crafted`,
`research_started`, `research_finished`, `gui_opened`, `gui_closed`,
`cursor_stack`, `selected`, `pre_build`, `control`, `joined`, `left`.
