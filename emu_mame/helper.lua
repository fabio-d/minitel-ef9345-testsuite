-- Replace the minitel2's grayscale palette with RGB, to match what the tests
-- expect.
function set_palette_rgb()
  local pal = manager.machine.palettes:at(1)
  pal:set_pen_color(0, 0x00, 0x00, 0x00) -- black
  pal:set_pen_color(1, 0xFF, 0x00, 0x00) -- red
  pal:set_pen_color(2, 0x00, 0xFF, 0x00) -- green
  pal:set_pen_color(3, 0xFF, 0xFF, 0x00) -- yellow
  pal:set_pen_color(4, 0x00, 0x00, 0xFF) -- blue
  pal:set_pen_color(5, 0xFF, 0x00, 0xFF) -- magenta
  pal:set_pen_color(6, 0x00, 0xFF, 0xFF) -- cyan
  pal:set_pen_color(7, 0xFF, 0xFF, 0xFF) -- white
end
set_palette_rgb()

-- Connect to the local TCP server whose port is stored in the environment
-- variable.
local sock = emu.file("rw")
sock:open("socket.127.0.0.1:" .. os.getenv("HELPERLUA_SCREENSHOT_PORT"))

-- Take a screenshot and send it to the socket.
function frame_callback()
  local video = manager.machine.video
  frame_w, frame_h = video:snapshot_size()
  frame_data = video:snapshot_pixels()
  sock:write(string.pack("<HH", frame_w, frame_h) .. frame_data)
end

-- Schedule the above function to be called for each frame.
emu.register_frame_done(frame_callback)
