# Capture surface: mod vs OS

Factorio's Lua API is a simulation API. Wube's own docs and a December 2025
forum reply from a contributor are blunt: **mouse position is not part of game
state**, so mods cannot read it each frame. Custom inputs expose
`cursor_position` and `cursor_display_location` only when that input fires
(clicks / bound controls), not while the mouse is moving.

`LuaGameScript.take_screenshot` writes the **game renderer** into
`script-output/`. It can include in-game GUI, alt-mode, and the building
preview. It does not include:

- Steam overlay, Discord overlay, NVIDIA / RivaTuner overlays
- OS notifications, menu bar, Notch extras
- Any other application's window
- The OS cursor (Factorio draws its own)
- Alt-Tab / Mission Control
- Pixel-accurate 30 fps video (PNG-to-disk every frame would hitch)

Window capture of the Factorio client gets the swapchain, so **injected**
overlays (Steam, Discord, GPU HUDs) usually appear. Separate OS windows do not.
This project also **pauses on focus loss**, so a Slack message you type after
alt-tab never lands in the log.

That is the split:

| Goal | Use |
|---|---|
| Train a computer-use agent (pixels + HID) | OS recorder, Factorio-focus gated |
| Label builds, research, camera, hover entity | Lua sidecar |
| Reproduce the save exactly | Factorio's own replay, not this dataset |

A mod-only dataset would be cleaner pixels and worse actions. We ship both.
