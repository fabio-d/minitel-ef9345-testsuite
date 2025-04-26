import argparse
import asyncio
import base64
import io
import os
import re
import shutil
import struct
import tempfile
from typing import Tuple
import PIL.Image

QUERY_RE = re.compile("(E?)R([0-7])\\?")
SET_RE = re.compile("(E?)R([0-7])=([0-9A-F]{2})")

MACHINE = "minitel2"
BIOSFILE = "minitel2_bv4.bin"
CHARSETFILE = "charset.rom"


async def run_mame_minitel2(
    mame: str,
    charset_rom: str,
    serial_tcp_port: int,
    screenshot_tcp_port: int,
):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a ROM directory containing our firmware. We use the same
        # filename as the real firmware, so that MAME will load us instead when
        # it tries to load the file with the name it expects.
        romdir = os.path.join(tmpdir, "minitel2")
        os.mkdir(romdir)
        shutil.copy(
            "firmware/build/minitel2.bin",
            os.path.join(romdir, BIOSFILE),
        )
        shutil.copy(charset_rom, os.path.join(romdir, CHARSETFILE))

        # Create a cfg directory with a custom serial port configuration, i.e.
        # 14400 8N1 (instead of the default 1200 8E1).
        cfgdir = os.path.join(tmpdir, "cfg")
        os.mkdir(cfgdir)
        with open(os.path.join(cfgdir, "minitel2.cfg"), "wt") as fp:
            print(
                """\
<?xml version="1.0"?>
<mameconfig version="10">
    <system name="minitel2">
        <input>
            <port tag=":periinfo:null_modem:RS232_DATABITS" type="CONFIG" mask="255" defvalue="2" value="3" />
            <port tag=":periinfo:null_modem:RS232_PARITY" type="CONFIG" mask="255" defvalue="2" value="0" />
            <port tag=":periinfo:null_modem:RS232_RXBAUD" type="CONFIG" mask="255" defvalue="4" value="8" />
            <port tag=":periinfo:null_modem:RS232_STOPBITS" type="CONFIG" mask="255" defvalue="1" value="1" />
            <port tag=":periinfo:null_modem:RS232_TXBAUD" type="CONFIG" mask="255" defvalue="4" value="8" />
        </input>
    </system>
</mameconfig>
                """,
                file=fp,
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                mame,
                "minitel2",
                # Do not look for .ini files.
                "-noreadconfig",
                # Tell MAME where to find our custom ROM and the charset file.
                "-rompath",
                tmpdir,
                # We don't use the modem port: connect it to /dev/null.
                "-modem",
                "null_modem",
                "-bitb1",
                "/dev/null",
                # We do use the periinfo port: connect it to our listening port.
                "-periinfo",
                "null_modem",
                "-bitb2",
                "socket.127.0.0.1:%d" % serial_tcp_port,
                # Load our XML configuration that sets periinfo at 14400 8N1.
                "-cfg_directory",
                cfgdir,
                # Disable video output. As a side effect, this will skip the
                # "bad ROM" warning prompt, which would otherwise require a user
                # interaction.
                "-videodriver",
                "offscreen",
                "-video",
                "none",
                # Disable audio output.
                "-sound",
                "none",
                # Run our lua helper script.
                "-autoboot_script",
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "helper.lua")
                ),
                cwd=tmpdir,
                env={
                    # Tell our lua helper script where to send the screenshots
                    # it takes.
                    "HELPERLUA_SCREENSHOT_PORT": "%d" % screenshot_tcp_port,
                    **os.environ,
                },
            )
        except FileNotFoundError:
            exit(
                f"MAME not found (searched as {mame!r}). "
                "Use --mame to set a non-standard name or path."
            )

        return await proc.wait()


# Given a MAME screenshot taken by helper.lua, only leave 2 px of margin in the
# four directions.
def crop_minitel2_image(img: PIL.Image.Image) -> PIL.Image.Image:
    MARGIN = 2
    match img.size:
        case (334, 278):
            return img.crop(
                (6 - MARGIN, 10 - MARGIN, 326 + MARGIN, 260 + MARGIN)
            )
        case (490, 278):
            return img.crop(
                (4 - MARGIN, 10 - MARGIN, 484 + MARGIN, 260 + MARGIN)
            )


class ScreenshotBroker:
    def __init__(self, screenshot_r: asyncio.StreamReader):
        self._screenshot_r = screenshot_r
        self._latest_image = None
        asyncio.create_task(self._conn_handler())

    async def _conn_handler(self):
        while True:
            num_channels, frame_w, frame_h = struct.unpack(
                "<BHH", await self._screenshot_r.readexactly(5)
            )
            frame_size = 4 * frame_w * frame_h
            frame_data = await self._screenshot_r.readexactly(frame_size)
            header = {3: "RGB", 4: "RGBI"}[num_channels]
            self._latest_image = header, crop_minitel2_image(
                PIL.Image.frombytes(
                    "RGBA", (frame_w, frame_h), frame_data, "raw", "BGRA"
                ).convert("RGB")
            )

    def get_latest_image(self) -> Tuple[str, bytes]:
        if self._latest_image is None:
            return "", b""

        header, image = self._latest_image
        buf = io.BytesIO()
        image.save(buf, format="png")
        return header, buf.getvalue()


class Server:
    def __init__(
        self,
        serial_r: asyncio.StreamReader,
        serial_w: asyncio.StreamWriter,
        screenshot_broker: ScreenshotBroker,
    ):
        self._transaction_lock = asyncio.Lock()
        self._serial_r = serial_r
        self._serial_w = serial_w
        self._screenshot_broker = screenshot_broker

    async def handle_client(
        self, client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter
    ):
        while request_bytes := await client_r.readline():
            request_str = request_bytes.decode().strip()
            if request_str == "TYPE?":
                response = b"TS9347\n"
            elif request_str == "SCREENSHOT?":
                header, image_bytes = self._screenshot_broker.get_latest_image()
                response = header.encode() + b"\n"
                response += base64.b64encode(image_bytes) + b"\n"
            elif query_match := QUERY_RE.fullmatch(request_str):
                # Build and execute a read register request.
                exec_bit, reg = query_match.groups()
                if not exec_bit:
                    request = bytes([0x10 + int(reg)])
                else:
                    request = bytes([0x18 + int(reg)])
                async with self._transaction_lock:
                    self._serial_w.write(request)
                    await self._serial_w.drain()
                    reply = await self._serial_r.read(1)
                    response = b"%02x\n" % reply[0]
            elif set_match := SET_RE.fullmatch(request_str):
                # Build and execute a write register request.
                exec_bit, reg, value = set_match.groups()
                if not exec_bit:
                    request = bytes([0x20 + int(reg), int(value, 16)])
                else:
                    request = bytes([0x28 + int(reg), int(value, 16)])
                async with self._transaction_lock:
                    self._serial_w.write(request)
                    await self._serial_w.drain()
                response = b""
            else:
                response = b"Invalid request, ignoring\n"
            client_w.write(response)
            await client_w.drain()


def _host_and_port(text: str) -> Tuple[str, int]:
    host, sep, port_str = text.rpartition(":")
    port = int(port_str)
    if port < 1 or port > 65535 or sep != ":":
        raise ValueError
    return host, port


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--listen",
        metavar="HOST:PORT",
        required=True,
        type=_host_and_port,
        help="Address to listen on",
    )
    parser.add_argument(
        "--mame",
        default="mame",
        metavar="PATH",
        help='Name or full path of the "mame" executable',
    )
    parser.add_argument(
        "--charset-rom",
        metavar="PATH",
        required=True,
        help='Path to the "charset.rom" file',
    )
    args = parser.parse_args()
    listen_host, listen_port = args.listen

    # Start two temporary TCP servers and tell MAME to connect.
    serial_conn = asyncio.Future()
    serial_serv = await asyncio.start_server(
        lambda r, w: serial_conn.set_result((r, w)), "127.0.0.1", 0
    )
    screenshot_conn = asyncio.Future()
    screenshot_serv = await asyncio.start_server(
        lambda r, w: screenshot_conn.set_result((r, w)), "127.0.0.1", 0
    )
    mame_task = asyncio.create_task(
        run_mame_minitel2(
            mame=args.mame,
            charset_rom=args.charset_rom,
            serial_tcp_port=serial_serv.sockets[0].getsockname()[1],
            screenshot_tcp_port=screenshot_serv.sockets[0].getsockname()[1],
        )
    )

    # Ensure that if MAME stops, we stop too.
    mame_task.add_done_callback(lambda _: exit("MAME stopped"))

    # Close the temporary server as soon as we get the connections from MAME.
    serial_r, serial_w = await serial_conn
    screenshot_r, screenshot_w = await screenshot_conn
    serial_serv.close()
    screenshot_serv.close()

    # Start receiving screenshots.
    screenshot_broker = ScreenshotBroker(screenshot_r)

    # Wait for the firmware running in MAME to signal readiness.
    await serial_r.readuntil(b"!")

    server = Server(serial_r, serial_w, screenshot_broker)
    real_serv = await asyncio.start_server(
        server.handle_client,
        listen_host,
        listen_port,
    )
    await real_serv.serve_forever()


asyncio.run(main())
