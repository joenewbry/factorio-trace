# Factorio Trace

Open recorder and dataset for **humans playing Factorio**.

Site: [factorio.digitalsurfacelabs.com](https://factorio.digitalsurfacelabs.com)

This is **not** the Factorio Learning Environment. FLE agents write Python against a game API. Factorio Trace records the thing a person actually does: the Factorio window, the mouse, the keys. The intended use is computer-use / imitation-learning research. A Lua sidecar is optional and adds tick-accurate factory labels.

## Should this just be a mod?

No, not if you want pixels and mouse motion.

Wube does not expose the cursor as game state. Mods can see `cursor_position` on some **events** (build, mine, linked custom inputs). They cannot poll mouse movement every frame. `take_screenshot` captures the renderer — in-game HUD, tooltips, alt-mode — and misses Steam/Discord/NVIDIA overlays, OS banners, and other windows.

| | Lua mod | This recorder |
|---|---|---|
| In-game HUD / map / alt-mode | yes (screenshot) | yes (window capture) |
| Raw keys + mouse motion | no | yes, while Factorio is focused |
| Injected overlays (Steam, Discord) | no | usually yes |
| Other app windows, notifications | no | no — we pause on blur |
| Builds, research, selected entity | yes | not from pixels |

Hybrid is the package: OS capture gated on Factorio being the active application, plus an optional mod under `script-output/factorio-trace/`.

Details: [docs/capture-surface.md](docs/capture-surface.md).

## Record

```bash
git clone https://github.com/joenewbry/factorio-trace
cd factorio-trace
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ".[macos]"   # on a Mac

factorio-trace install-mod  # optional sidecar
factorio-trace doctor
factorio-trace record --contributor yourname --upload --yes
```

On macOS grant **Screen Recording** and **Accessibility** to Terminal (or iTerm). Then launch Factorio and play. Alt-tab whenever; capture pauses.

Windows is the same CLI. Linux needs `xdotool`.

Local sessions land in `~/.factorio-trace/sessions/` (`%USERPROFILE%\.factorio-trace\sessions` on Windows). Uploads go to the public dataset (CC BY 4.0). Code is MIT.

## Training loop (joystick → shadow → cut the wires)

Same shape as the arcade Screen-Self-Driving eval, and the primate BMI setup: collect play, train a decoder, score it while the human still drives, then disconnect the human's input and see whether the decoder still plays.

```bash
factorio-trace record --contributor joe --upload --yes          # you drive
factorio-trace shadow --policy hold                             # you drive, net scored
factorio-trace play --cut-wires --policy replay --from SESSION  # net drives
factorio-trace score SESSION
```

`shadow` never injects. `play` will not inject unless you pass `--cut-wires`. Details: [docs/training-loop.md](docs/training-loop.md). Tonight only `record` is required.

## Layout

```
factorio_trace/   CLI + recorder
mod/              Factorio 2.0 Lua sidecar
server/           catalog + ingest (factorio.digitalsurfacelabs.com)
schema/           trace-v0
```

## License

- Recorder, mod, and site: [MIT](LICENSE)
- Uploaded traces: [CC BY 4.0](LICENSE-DATA)
