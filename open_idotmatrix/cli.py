"""Command-line interface for open-idotmatrix."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .constants import DEVICE_NAME_PREFIX
from .device import OpenIDotMatrix
from .exceptions import OpenIDotMatrixError, ProtocolError
from .protocol import parse_packet
from .simulator import (
    MatrixSimulator,
    save_gif_preview_frames,
    save_text_animation,
    simulate_text_frame,
)
from .types import GifTotalLengthMode, TextBackgroundMode, TextColorMode, TextMode, YearByteMode


def _json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _rgb(values: list[str] | tuple[str, str, str]) -> tuple[int, int, int]:
    if len(values) != 3:
        raise ProtocolError("expected three RGB values")
    return tuple(int(v) for v in values)  # type: ignore[return-value]


def _parse_effect_colors(value: str) -> list[tuple[int, int, int]]:
    colors = []
    for chunk in value.split(";"):
        parts = [int(p.strip()) for p in chunk.split(",")]
        if len(parts) != 3:
            raise ProtocolError("effect colors must look like '255,0,0;0,255,0'")
        colors.append((parts[0], parts[1], parts[2]))
    return colors


def _validate_file_arg(value: str, label: str) -> None:
    path = Path(value).expanduser()
    if not path.exists():
        raise ProtocolError(f"{label} file does not exist: {value}")
    if path.is_dir():
        raise ProtocolError(f"{label} path must be a file, not a directory: {value}")


async def _cmd_scan(args: argparse.Namespace) -> None:
    name_prefix = "" if args.all else args.name_prefix
    devices = await OpenIDotMatrix.scan(timeout=args.timeout, name_prefix=name_prefix)
    _json([device.__dict__ for device in devices])


async def _run_hardware_command(args: argparse.Namespace) -> None:
    if args.command == "delete-device-data" and not args.yes:
        raise ProtocolError("delete-device-data requires --yes because it is destructive")
    if args.command == "gif":
        _validate_file_arg(args.path, "GIF")
    if args.command == "image":
        _validate_file_arg(args.path, "image")

    async with OpenIDotMatrix(address=args.address) as matrix:
        command = args.command
        if command == "status":
            result = {
                "address": args.address or matrix.transport.address,
                "connected": matrix.transport.is_connected(),
            }
        elif command == "on":
            result = await matrix.on()
        elif command == "off":
            result = await matrix.off()
        elif command == "reset":
            result = await matrix.reset()
        elif command == "brightness":
            result = await matrix.set_brightness(args.percent)
        elif command == "flip":
            result = await matrix.flip(not args.disable)
        elif command == "freeze":
            result = await matrix.freeze()
        elif command == "sync-time":
            result = await matrix.sync_time(year_mode=YearByteMode(args.year_mode))
        elif command == "fill":
            result = await matrix.fill((args.r, args.g, args.b))
        elif command == "pixel":
            result = await matrix.pixel(args.x, args.y, (args.r, args.g, args.b))
        elif command == "spiral":
            result = await matrix.spiral((args.r, args.g, args.b), delay=args.delay)
        elif command == "text":
            result = await matrix.text(
                args.text,
                mode=TextMode(args.mode),
                speed=args.speed,
                color_mode=TextColorMode(args.color_mode),
                color=(args.r, args.g, args.b),
                background_mode=TextBackgroundMode(args.background_mode),
                background=(args.bg_r, args.bg_g, args.bg_b),
                font_path=args.font_path,
                font_size=args.font_size,
            )
        elif command == "gif":
            result = await matrix.gif(
                args.path,
                process=not args.raw,
                total_length_mode=GifTotalLengthMode(args.total_length_mode),
                wait_for_ack=not args.no_ack,
                response=not args.no_response,
                ack_timeout=args.ack_timeout,
                sleep_between_chunks=args.sleep_between_chunks,
            )
        elif command == "image":
            result = await matrix.image(
                args.path,
                total_length_mode=GifTotalLengthMode(args.total_length_mode),
                wait_for_ack=not args.no_ack,
                response=not args.no_response,
                ack_timeout=args.ack_timeout,
                sleep_between_chunks=args.sleep_between_chunks,
            )
        elif command == "clock":
            result = await matrix.clock(
                args.style,
                visible_date=not args.hide_date,
                hour24=not args.hour12,
                color=(args.r, args.g, args.b),
            )
        elif command == "chronograph":
            result = await matrix.chronograph(args.mode)
        elif command == "scoreboard":
            result = await matrix.scoreboard(args.left, args.right)
        elif command == "countdown":
            result = await matrix.countdown(args.mode, args.minutes, args.seconds)
        elif command == "eco":
            result = await matrix.eco(
                args.flag,
                args.start_hour,
                args.start_minute,
                args.end_hour,
                args.end_minute,
                args.brightness,
            )
        elif command == "effect":
            result = await matrix.effect(args.style, _parse_effect_colors(args.colors), speed=args.speed)
        elif command == "delete-device-data":
            result = await matrix.delete_device_data()
        elif command == "raw":
            result = await matrix.send(bytes.fromhex(args.hex))
        else:  # pragma: no cover - argparse guards this
            raise ProtocolError(f"unknown command: {command}")
    _json(result)


def _cmd_decode(args: argparse.Namespace) -> None:
    _json(parse_packet(bytes.fromhex(args.hex)))


def _cmd_simulate(args: argparse.Namespace) -> None:
    out_path = Path(args.save) if args.save else Path("out/simulation.png")
    if args.text_animation:
        path = save_text_animation(
            args.text_animation,
            out_path.with_suffix(".gif"),
            frames=args.frames,
            scale=args.scale,
            color=(args.r, args.g, args.b),
            font_path=args.font_path,
            font_size=args.font_size,
        )
        print(path)
        return

    sim = MatrixSimulator()
    if args.fill:
        sim.fill(_rgb(args.fill))
    if args.gif:
        sim.load_gif_preview(args.gif)
    if args.text:
        sim = simulate_text_frame(
            args.text,
            offset=args.offset,
            color=(args.r, args.g, args.b),
            font_path=args.font_path,
            font_size=args.font_size,
        )
    if args.packet_hex:
        sim.apply_packet(bytes.fromhex(args.packet_hex), text_scroll_offset=args.offset)
    for pixel in args.pixel or []:
        x, y, r, g, b = [int(v) for v in pixel]
        sim.set_pixel(x, y, (r, g, b))
    path = sim.save(out_path, scale=args.scale, grid=not args.no_grid)
    print(path)
    if args.show:
        sim.show(scale=args.scale, grid=not args.no_grid)


def _cmd_gif_preview(args: argparse.Namespace) -> None:
    paths = save_gif_preview_frames(args.path, args.out_dir, scale=args.scale, max_frames=args.max_frames)
    _json([str(path) for path in paths])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="open-idotmatrix",
        description="Control and reverse-engineer iDotMatrix 32x32 BLE pixel displays.",
    )
    parser.add_argument("--address", help="BLE MAC/address. If omitted, hardware commands connect to first IDM-* device found.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="Scan for IDM-* BLE devices")
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--name-prefix", default=DEVICE_NAME_PREFIX, help="Filter devices by advertised local-name prefix")
    p.add_argument("--all", action="store_true", help="Do not filter by advertised local-name prefix")
    p.set_defaults(func=_cmd_scan)

    for name in ("on", "off", "reset", "freeze"):
        sub.add_parser(name, help=f"Send {name} command")

    sub.add_parser("status", help="Connect to the device and report connection state")

    p = sub.add_parser("brightness", help="Set brightness percent, usually 5..100")
    p.add_argument("percent", type=int)

    p = sub.add_parser("flip", help="Enable or disable flipped screen orientation")
    p.add_argument("--disable", action="store_true", help="Disable screen flip instead of enabling it")

    p = sub.add_parser("sync-time", help="Sync device time")
    p.add_argument("--year-mode", choices=[m.value for m in YearByteMode], default=YearByteMode.LOW_BYTE.value)

    p = sub.add_parser("fill", help="Fill whole display with one color")
    p.add_argument("r", type=int)
    p.add_argument("g", type=int)
    p.add_argument("b", type=int)

    p = sub.add_parser("pixel", help="Set one pixel")
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("r", type=int)
    p.add_argument("g", type=int)
    p.add_argument("b", type=int)

    p = sub.add_parser("spiral", help="Draw a generated spiral with pixel commands")
    p.add_argument("r", type=int, nargs="?", default=255)
    p.add_argument("g", type=int, nargs="?", default=0)
    p.add_argument("b", type=int, nargs="?", default=0)
    p.add_argument("--delay", type=float, default=0.0)

    p = sub.add_parser("text", help="Send text")
    p.add_argument("text")
    p.add_argument("--mode", type=int, default=TextMode.SCROLL_LEFT_TO_RIGHT)
    p.add_argument("--speed", type=int, default=95)
    p.add_argument("--color-mode", type=int, choices=[int(m) for m in TextColorMode], default=int(TextColorMode.FIXED))
    p.add_argument("--rgb", dest="rgb", nargs=3, default=["255", "255", "255"], metavar=("R", "G", "B"))
    p.add_argument("--background-mode", type=int, choices=[int(m) for m in TextBackgroundMode], default=int(TextBackgroundMode.OFF))
    p.add_argument("--background-rgb", dest="background_rgb", nargs=3, default=["0", "0", "0"], metavar=("R", "G", "B"))
    p.add_argument("--font-path")
    p.add_argument("--font-size", type=int, default=24)

    p = sub.add_parser("gif", help="Upload GIF/image as 32x32 GIF")
    p.add_argument("path")
    p.add_argument("--raw", action="store_true", help="Do not resize/re-encode; file must already be 32x32")
    p.add_argument("--no-ack", action="store_true", help="Do not wait for protocol notifications between chunks")
    p.add_argument("--no-response", action="store_true", help="Use GATT write without response")
    p.add_argument("--ack-timeout", type=float, default=10.0, help="Seconds to wait for each GIF ACK")
    p.add_argument("--sleep-between-chunks", type=float, default=1.0, help="Delay when sending GIF chunks without ACK")
    p.add_argument("--total-length-mode", choices=[m.value for m in GifTotalLengthMode], default=GifTotalLengthMode.INCLUDE_HEADERS.value)

    p = sub.add_parser("image", help="Distort any image to 1:1, subsample to 32x32, and upload it")
    p.add_argument("path")
    p.add_argument("--no-ack", action="store_true", help="Do not wait for protocol notifications between chunks")
    p.add_argument("--no-response", action="store_true", help="Use GATT write without response")
    p.add_argument("--ack-timeout", type=float, default=10.0, help="Seconds to wait for each image ACK")
    p.add_argument("--sleep-between-chunks", type=float, default=1.0, help="Delay when sending image chunks without ACK")
    p.add_argument("--total-length-mode", choices=[m.value for m in GifTotalLengthMode], default=GifTotalLengthMode.INCLUDE_HEADERS.value)

    p = sub.add_parser("clock", help="Show device clock")
    p.add_argument("style", type=int)
    p.add_argument("--hide-date", action="store_true")
    p.add_argument("--hour12", action="store_true")
    p.add_argument("--rgb", nargs=3, default=["255", "255", "255"], metavar=("R", "G", "B"))

    p = sub.add_parser("chronograph", help="Set chronograph mode")
    p.add_argument("mode", type=int)

    p = sub.add_parser("scoreboard", help="Set scoreboard")
    p.add_argument("left", type=int)
    p.add_argument("right", type=int)

    p = sub.add_parser("countdown", help="Set countdown mode/time")
    p.add_argument("mode", type=int)
    p.add_argument("minutes", type=int)
    p.add_argument("seconds", type=int)

    p = sub.add_parser("eco", help="Set ECO/night mode schedule and brightness")
    p.add_argument("flag", type=int)
    p.add_argument("start_hour", type=int)
    p.add_argument("start_minute", type=int)
    p.add_argument("end_hour", type=int)
    p.add_argument("end_minute", type=int)
    p.add_argument("brightness", type=int)

    p = sub.add_parser("effect", help="Set effect mode")
    p.add_argument("style", type=int)
    p.add_argument("colors", help="Semicolon-separated RGB triples, e.g. '255,0,0;0,255,0'")
    p.add_argument("--speed", type=int, default=90)

    p = sub.add_parser("delete-device-data", help="Destructively delete device-side data")
    p.add_argument("--yes", action="store_true", help="Confirm this destructive command")

    p = sub.add_parser("raw", help="Send raw hex bytes")
    p.add_argument("hex")

    p = sub.add_parser("decode", help="Decode/inspect raw hex bytes without hardware")
    p.add_argument("hex")
    p.set_defaults(func=_cmd_decode)

    p = sub.add_parser("simulate", help="Render a simulated 32x32 frame without hardware")
    p.add_argument("--text")
    p.add_argument("--text-animation", help="Save animated text preview as GIF")
    p.add_argument("--gif", help="Load first GIF/image frame into simulator")
    p.add_argument("--packet-hex", help="Apply one raw protocol packet")
    p.add_argument("--fill", nargs=3, metavar=("R", "G", "B"))
    p.add_argument("--pixel", nargs=5, action="append", metavar=("X", "Y", "R", "G", "B"))
    p.add_argument("--rgb", nargs=3, default=["255", "255", "255"], metavar=("R", "G", "B"))
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--frames", type=int, default=64)
    p.add_argument("--save", default="out/simulation.png")
    p.add_argument("--scale", type=int, default=16)
    p.add_argument("--no-grid", action="store_true")
    p.add_argument("--show", action="store_true")
    p.add_argument("--font-path")
    p.add_argument("--font-size", type=int, default=24)
    p.set_defaults(func=_cmd_simulate)

    p = sub.add_parser("gif-preview", help="Export scaled PNG preview frames from a GIF/image")
    p.add_argument("path")
    p.add_argument("out_dir")
    p.add_argument("--scale", type=int, default=16)
    p.add_argument("--max-frames", type=int, default=16)
    p.set_defaults(func=_cmd_gif_preview)

    return parser


def _normalize_rgb_args(args: argparse.Namespace) -> None:
    if hasattr(args, "rgb"):
        args.r, args.g, args.b = _rgb(args.rgb)
    if hasattr(args, "background_rgb"):
        args.bg_r, args.bg_g, args.bg_b = _rgb(args.background_rgb)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _normalize_rgb_args(args)
    try:
        if hasattr(args, "func"):
            result = args.func(args)
            if asyncio.iscoroutine(result):
                asyncio.run(result)
        elif args.command == "scan":
            asyncio.run(_cmd_scan(args))
        else:
            asyncio.run(_run_hardware_command(args))
        return 0
    except OpenIDotMatrixError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
