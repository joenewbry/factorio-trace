local PREFIX = "factorio-trace/"

local function esc(s)
  s = tostring(s)
  s = s:gsub("\\", "\\\\")
  s = s:gsub("\"", "\\\"")
  s = s:gsub("\n", "\\n")
  return s
end

local function encode(v)
  local t = type(v)
  if v == nil then
    return "null"
  elseif t == "boolean" then
    return v and "true" or "false"
  elseif t == "number" then
    return tostring(v)
  elseif t == "string" then
    return '"' .. esc(v) .. '"'
  elseif t == "table" then
    local is_array = v[1] ~= nil
    if is_array then
      local parts = {}
      for i = 1, #v do
        parts[i] = encode(v[i])
      end
      return "[" .. table.concat(parts, ",") .. "]"
    end
    local parts = {}
    for k, val in pairs(v) do
      if val ~= nil then
        parts[#parts + 1] = '"' .. esc(k) .. '":' .. encode(val)
      end
    end
    return "{" .. table.concat(parts, ",") .. "}"
  end
  return "null"
end

local buffer = {}

local function enabled_for(player)
  if not player then
    return false
  end
  local s = player.mod_settings["factorio-trace-enabled"]
  return (not s) or s.value
end

local function flush()
  if #buffer == 0 then
    return
  end
  helpers.write_file(PREFIX .. "events.jsonl", table.concat(buffer, "\n") .. "\n", true)
  buffer = {}
end

local function emit(tbl)
  buffer[#buffer + 1] = encode(tbl)
  if #buffer >= 32 then
    flush()
  end
end

local function pos(p)
  if not p then
    return nil
  end
  return { x = p.x, y = p.y }
end

local function entity_info(e)
  if not e or not e.valid then
    return nil
  end
  return { name = e.name, x = e.position.x, y = e.position.y, dir = e.direction }
end

local function stack_name(player)
  local c = player.cursor_stack
  if c and c.valid_for_read then
    return c.name
  end
  return nil
end

local function opened_name(player)
  local o = player.opened
  if o == nil then
    return nil
  end
  local ot = type(o)
  if ot == "number" then
    return { kind = "gui_type", id = o }
  end
  if ot == "userdata" and o.valid then
    if o.object_name == "LuaEntity" then
      return { kind = "entity", name = o.name }
    end
    if o.object_name == "LuaGuiElement" then
      return { kind = "element", name = o.name }
    end
  end
  return { kind = "other" }
end

local function snapshot(player, tick)
  if not enabled_for(player) then
    return
  end
  local walking = player.walking_state
  emit({
    type = "tick",
    tick = tick,
    surface = player.surface.name,
    x = player.position.x,
    y = player.position.y,
    zoom = player.zoom,
    render_mode = player.render_mode,
    controller = player.controller_type,
    selected = player.selected and player.selected.name or nil,
    cursor = stack_name(player),
    walking = walking and walking.walking or false,
    mining = player.mining_state and player.mining_state.mining or false,
    opened = opened_name(player),
  })
  helpers.write_file(
    PREFIX .. "active.json",
    encode({
      tick = tick,
      player = player.name,
      surface = player.surface.name,
    }),
    false
  )
end

script.on_nth_tick(60, function(e)
  flush()
  for _, player in pairs(game.connected_players) do
    snapshot(player, e.tick)
  end
end)

script.on_event(defines.events.on_built_entity, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({ type = "built", tick = e.tick, entity = entity_info(e.entity) })
end)

script.on_event(defines.events.on_player_mined_entity, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({ type = "mined", tick = e.tick, entity = entity_info(e.entity) })
end)

script.on_event(defines.events.on_player_rotated_entity, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({ type = "rotated", tick = e.tick, entity = entity_info(e.entity) })
end)

script.on_event(defines.events.on_player_crafted_item, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({
    type = "crafted",
    tick = e.tick,
    item = e.item_stack and e.item_stack.name or nil,
    count = e.item_stack and e.item_stack.count or nil,
  })
end)

script.on_event(defines.events.on_research_started, function(e)
  emit({
    type = "research_started",
    tick = e.tick,
    tech = e.research and e.research.name or nil,
  })
end)

script.on_event(defines.events.on_research_finished, function(e)
  emit({
    type = "research_finished",
    tick = e.tick,
    tech = e.research and e.research.name or nil,
  })
end)

script.on_event(defines.events.on_gui_opened, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({ type = "gui_opened", tick = e.tick, gui = e.gui_type })
end)

script.on_event(defines.events.on_gui_closed, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({ type = "gui_closed", tick = e.tick, gui = e.gui_type })
end)

script.on_event(defines.events.on_player_cursor_stack_changed, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({ type = "cursor_stack", tick = e.tick, cursor = stack_name(player) })
end)

script.on_event(defines.events.on_selected_entity_changed, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({
    type = "selected",
    tick = e.tick,
    selected = player.selected and player.selected.name or nil,
  })
end)

script.on_event(defines.events.on_pre_build, function(e)
  local player = game.get_player(e.player_index)
  if not enabled_for(player) then
    return
  end
  emit({
    type = "pre_build",
    tick = e.tick,
    x = e.position.x,
    y = e.position.y,
    created_by_moving = e.created_by_moving,
  })
end)

local linked = {
  "build",
  "mine",
  "shoot-enemy",
  "shoot-selected",
  "rotate",
  "reverse-rotate",
  "pick-items",
  "drop-cursor",
  "fast-entity-transfer",
  "fast-entity-split",
  "open-item",
  "copy-entity-settings",
  "paste-entity-settings",
}

for _, name in ipairs(linked) do
  script.on_event("factorio-trace-" .. name, function(e)
    local player = game.get_player(e.player_index)
    if not enabled_for(player) then
      return
    end
    emit({
      type = "control",
      control = name,
      tick = e.tick,
      cursor = pos(e.cursor_position),
      display = pos(e.cursor_display_location),
      in_gui = e.in_gui,
    })
  end)
end

script.on_event(defines.events.on_player_joined_game, function(e)
  emit({ type = "joined", tick = e.tick, player_index = e.player_index })
  flush()
end)

script.on_event(defines.events.on_player_left_game, function(e)
  emit({ type = "left", tick = e.tick, player_index = e.player_index })
  flush()
end)
