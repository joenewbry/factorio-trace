-- Linked controls fire alongside the real keybind and give us cursor_position
-- / cursor_display_location at click time. They do not consume the input.
-- Continuous mouse motion is still not available to mods (not game state).

local controls = {
  "build",
  "mine",
  "rotate",
  "reverse-rotate",
  "fast-entity-transfer",
  "fast-entity-split",
  "copy-entity-settings",
  "paste-entity-settings",
}

for _, name in ipairs(controls) do
  data:extend({
    {
      type = "custom-input",
      name = "factorio-trace-" .. name,
      key_sequence = "",
      linked_game_control = name,
      consuming = "none",
      include_selected_prototype = true,
    },
  })
end
