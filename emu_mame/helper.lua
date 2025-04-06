-- Replace the minitel2's grayscale palette with RGB, to match what the tests
-- expect.
function set_palette_rgbi()
  local pal = manager.machine.palettes:at(1)
  if pal.entries == 8 then -- the insert channel cannot be rendered
    pal:set_pen_color(0, 0x00, 0x00, 0x00) -- black
    pal:set_pen_color(1, 0xFF, 0x00, 0x00) -- red
    pal:set_pen_color(2, 0x00, 0xFF, 0x00) -- green
    pal:set_pen_color(3, 0xFF, 0xFF, 0x00) -- yellow
    pal:set_pen_color(4, 0x00, 0x00, 0xFF) -- blue
    pal:set_pen_color(5, 0xFF, 0x00, 0xFF) -- magenta
    pal:set_pen_color(6, 0x00, 0xFF, 0xFF) -- cyan
    pal:set_pen_color(7, 0xFF, 0xFF, 0xFF) -- white
    return 3
  elseif pal.entries == 16 then -- the insert channel can be rendered
    pal:set_pen_color(0, 0x44, 0x44, 0x44) -- black
    pal:set_pen_color(1, 0xCC, 0x44, 0x44) -- red
    pal:set_pen_color(2, 0x44, 0xCC, 0x44) -- green
    pal:set_pen_color(3, 0xCC, 0xCC, 0x44) -- yellow
    pal:set_pen_color(4, 0x44, 0x44, 0xCC) -- blue
    pal:set_pen_color(5, 0xCC, 0x44, 0xCC) -- magenta
    pal:set_pen_color(6, 0x44, 0xCC, 0xCC) -- cyan
    pal:set_pen_color(7, 0xCC, 0xCC, 0xCC) -- white
    pal:set_pen_color(8, 0x00, 0x00, 0x00) -- black + insert
    pal:set_pen_color(9, 0xFF, 0x00, 0x00) -- red + insert
    pal:set_pen_color(10, 0x00, 0xFF, 0x00) -- green + insert
    pal:set_pen_color(11, 0xFF, 0xFF, 0x00) -- yellow + insert
    pal:set_pen_color(12, 0x00, 0x00, 0xFF) -- blue + insert
    pal:set_pen_color(13, 0xFF, 0x00, 0xFF) -- magenta + insert
    pal:set_pen_color(14, 0x00, 0xFF, 0xFF) -- cyan + insert
    pal:set_pen_color(15, 0xFF, 0xFF, 0xFF) -- white + insert
    return 4
  else
    return 0
  end
end
local num_channels = set_palette_rgbi()

-- Connect to the local TCP server whose port is stored in the environment
-- variable.
local sock = emu.file("rw")
sock:open("socket.127.0.0.1:" .. os.getenv("HELPERLUA_SCREENSHOT_PORT"))

-- Take a screenshot and send it to the socket.
function frame_callback()
  local video = manager.machine.video
  frame_w, frame_h = video:snapshot_size()
  frame_data = video:snapshot_pixels()
  sock:write(string.pack("<BHH", num_channels, frame_w, frame_h) .. frame_data)
end

-- Schedule the above function to be called for each frame.
emu.register_frame_done(frame_callback)
