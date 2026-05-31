# open-idotmatrix

Open toolkit for controlling and studying **32x32 RGB iDotMatrix** displays from Linux with Python.

This repository is intended as a clean starting point for:

- controlling the matrix over Bluetooth Low Energy from Linux;
- building protocol packets without hardware;
- sending basic commands, text, and GIFs;
- simulating on a PC what should appear on the matrix;
- giving Codex a clear base for real-hardware testing and incremental protocol reverse engineering.

> Status: **alpha / reverse engineering**. The initial target is the 32x32 iDotMatrix display whose BLE name usually starts with `IDM-`.

## Contents

```text
open-idotmatrix/
  open_idotmatrix/
    constants.py      # UUIDs, geometry, and protocol constants
    protocol.py       # pure BLE packet builders/parsers
    text.py           # 16x32 text rendering with Pillow
    gif.py            # 32x32 GIF processing and chunking
    transport.py      # BLE transport with bleak
    device.py         # high-level async API
    simulator.py      # 32x32 simulator with Pillow
    cli.py            # open-idotmatrix CLI
    qt_app.py         # optional PySide6 app launcher
    qt_window.py      # optional PySide6 desktop UI
  docs/
    PROTOCOL.md
    ROADMAP.md
    CODEX_BRIEF.md
    REVERSE_ENGINEERING.md
    SIMULATOR.md
    LINUX_BLUETOOTH.md
    TEST_PLAN.md
  examples/
  tests/
  .github/workflows/ci.yml
```

## Local Installation

System requirements:

- Python 3.10 or newer.
- Linux with Bluetooth enabled for real hardware access.
- BlueZ installed if you plan to use BLE.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Dependencies are declared in `pyproject.toml`: `bleak` and `pillow` for the base package; `pytest`, `pytest-asyncio`, and `ruff` for development; `PySide6` as the optional Qt extra.

To install the Qt desktop app too:

```bash
pip install -e ".[dev,qt]"
open-idotmatrix-qt
```

## First Use Without Hardware: Simulator

Render text to a local image:

```bash
open-idotmatrix simulate --text "Hello" --save out/hello.png
```

Render a scrolling text GIF:

```bash
open-idotmatrix simulate --text-animation "open-idotmatrix" --save out/text.gif
```

Simulate raw packets:

```bash
open-idotmatrix simulate --packet-hex "07 00 02 02 ff 00 00" --save out/red.png
open-idotmatrix simulate --packet-hex "0a 00 05 01 00 00 ff 00 1f 1f" --save out/pixel.png
```

## First Use With Real Hardware

Scan for devices:

```bash
open-idotmatrix scan
```

Turn the screen on/off:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF on
open-idotmatrix --address AA:BB:CC:DD:EE:FF off
```

Solid color:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 255 0 0
```

Single pixel:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 31 31 0 0 255
```

Text:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "Hello" --rgb 255 255 255 --mode 1 --speed 95
```

GIF:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif ./demo.gif
```

If notification ACK handling fails during early GIF testing:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif ./demo.gif --no-ack
```

## Qt Application

The PySide6 app exposes the same operation families as the CLI:

- BLE scanning and address selection;
- on/off, reset, freeze, brightness, flip, and sync-time;
- fill, pixel, and spiral;
- text with animation, color, background, and font controls;
- GIF upload with raw, ACK, response, timeout, and total-length options;
- clock, chronograph, countdown, scoreboard, ECO, and effects;
- raw hex, decode, simulator, text animation, and gif-preview tools;
- delete-device-data with explicit confirmation.

```bash
open-idotmatrix-qt
```

## Python API

```python
import asyncio
from open_idotmatrix import OpenIDotMatrix, TextMode

async def main():
    async with OpenIDotMatrix(address="AA:BB:CC:DD:EE:FF") as m:
        await m.on()
        await m.set_brightness(80)
        await m.sync_time()
        await m.fill((0, 0, 0))
        await m.pixel(0, 0, (255, 0, 0))
        await m.pixel(31, 31, (0, 0, 255))
        await m.text("Hello", mode=TextMode.SCROLL_LEFT_TO_RIGHT, color=(255, 255, 255))
        await m.gif("demo.gif")

asyncio.run(main())
```

## Known Protocol Summary

Main UUIDs:

```text
Service: 000000fa-0000-1000-8000-00805f9b34fb
Write:   0000fa02-0000-1000-8000-00805f9b34fb
Notify:  0000fa03-0000-1000-8000-00805f9b34fb
```

Basic commands:

| Action | Bytes |
|---|---|
| Screen on | `05 00 07 01 01` |
| Screen off | `05 00 07 01 00` |
| Brightness | `05 00 04 80 <percent>` |
| Full-screen color | `07 00 02 02 <r> <g> <b>` |
| Pixel | `0a 00 05 01 00 <r> <g> <b> <x> <y>` |
| Time | `0b 00 01 80 <yy> <mm> <dd> <dow> <hh> <min> <sec>` |

More details are in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Decode Packets

```bash
open-idotmatrix decode "05 00 07 01 01"
open-idotmatrix decode "0a 00 05 01 00 ff 00 00 1f 1f"
```

This prints JSON with the recognized packet type, lengths, and fields.

## Tests

```bash
pytest
```

Current tests cover:

- exact bytes for basic commands;
- range validation;
- text packetization and CRC32;
- GIF chunking;
- pixel, solid-color, and text simulation.

See [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md).

## How Codex Should Continue

This repository includes a specific guide for continuing with real hardware: [`docs/CODEX_BRIEF.md`](docs/CODEX_BRIEF.md).

Suggested first request for Codex:

```text
Read README.md, docs/PROTOCOL.md, docs/TEST_PLAN.md, and docs/CODEX_BRIEF.md.
Run pytest. Then, with my 32x32 iDotMatrix connected over Bluetooth, test
scan, on/off, fill, pixel, text, and gif. Record sent bytes, received
notifications, and any discrepancy. Do not run destructive commands unless I
explicitly ask for them.
```

## Project Principles

1. **Clean code from scratch.** Do not copy code from other repositories; reimplement packets from public knowledge and tests.
2. **Pure builders.** Protocol logic is separated from BLE transport.
3. **Hardware-optional tests.** Unit tests work without a matrix.
4. **32x32 first.** Do not attempt 16x16 or 64x64 support until the real 32x32 path is stable.
5. **Reproducible reverse engineering.** Every new command should be documented with bytes, hypotheses, tests, and captures when available.

## License

MIT. See [`LICENSE`](LICENSE).

## Technical Credits

This project builds on public iDotMatrix analysis, especially 8none1's notes and community work around Python iDotMatrix clients. The implementation in this repository is new and organized for testing, simulation, and incremental reverse engineering.
