hl.monitor({ output = "", mode = "1280x720", position = "0x0", scale = 1 })
hl.monitor({ output = "HYPRUNE-PREVIEW", mode = "1920x1080@60", position = "1280x0", scale = 1 })
hl.config({
  general = { gaps_in = 0, gaps_out = 0, border_size = 0 },
  decoration = { rounding = 0 },
  animations = { enabled = false },
  misc = { disable_hyprland_logo = true, disable_splash_rendering = true },
})
hl.on("hyprland.start", function()
  local root = os.getenv("HYPRUNE_SHELL_ROOT")
  hl.exec_cmd("python3 " .. root .. "/dev/session-info.py " .. root .. "/dev/.run/session.json")
end)
