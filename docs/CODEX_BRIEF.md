# Codex Guide

This document is written so Codex can continue from this repository with real hardware and improve the library without losing context.

## Context

We have a 32x32 RGB iDotMatrix display. We want to control it from Linux over BLE and progressively reverse engineer the full protocol.

The repository already includes:

- pure packet builders in `open_idotmatrix/protocol.py`;
- BLE transport in `open_idotmatrix/transport.py`;
- high-level API in `open_idotmatrix/device.py`;
- CLI in `open_idotmatrix/cli.py`;
- Qt desktop app in `open_idotmatrix/qt_window.py`;
- visual simulator in `open_idotmatrix/simulator.py`;
- hardware-free tests in `tests/`;
- protocol documentation in `docs/PROTOCOL.md`.

## Recommended First Request To Codex

```text
Read README.md, docs/PROTOCOL.md, docs/TEST_PLAN.md, docs/ROADMAP.md, and docs/CODEX_BRIEF.md.
Run pytest and only fix things if it fails.
Then prepare a hardware smoke-test session for a 32x32 iDotMatrix on Linux:
scan, on, off, brightness, fill, pixel corners, sync-time, text A, text Hello, and a small GIF.
Do not run build_delete_device_data or destructive commands.
For every test, record: CLI command, sent bytes, received notifications,
expected visual result, observed visual result, and proposed changes.
```

## Rules For Codex

1. Do not delete protocol documentation; extend it.
2. Do not mix BLE transport with packet construction.
3. Do not copy GPL or otherwise incompatible code if the project remains MIT.
4. If a packet changes, add or update an exact-byte test.
5. If behavior depends on hardware, mark it as `experimental` until validated.
6. Do not run destructive commands unless explicitly instructed.
7. Record discrepancies; do not hide them.

## Priority Tasks

### Task 1 - BLE Session Logging

Add a CLI option:

```bash
open-idotmatrix --address ... --session-log out/session.jsonl text "Hello"
```

Each JSONL line should contain:

```json
{"ts":"...", "direction":"tx", "hex":"05 00 07 01 01", "kind":"screen_on"}
{"ts":"...", "direction":"rx", "hex":"05 00 01 00 01", "kind":"notification"}
```

### Task 2 - Automated Smoke Test

Create a command:

```bash
open-idotmatrix --address ... smoke-test --out out/smoke.json
```

It should run safe commands and ask the user for visual confirmation or save a checklist.

### Task 3 - GIF ACK Validation

Test both modes:

```bash
open-idotmatrix --address ... gif demo.gif --total-length-mode include_headers
open-idotmatrix --address ... gif demo.gif --total-length-mode raw_payload_only
```

Record which combination works with:

- write with response;
- write without response;
- waiting for ACK;
- not waiting for ACK.

### Task 4 - MTU / Write Splitting

Inspect whether `max_write_without_response_size` works reliably on BlueZ. If not, add options:

```bash
--gatt-chunk-size 20
--gatt-chunk-size 244
```

### Task 5 - BLE Captures

Add a tool to import `btmon` or `btsnoop` logs when they are exported as text. Goal: extract writes to `fa02` and notifications from `fa03`.

### Task 6 - Advanced Simulator

Improve text animations:

- real horizontal mode 1/2 behavior;
- vertical mode 3/4 behavior;
- mode 5 strobe;
- mode 6 fade;
- mode 7 falling blocks;
- mode 8 laser/filling.

### Task 7 - Document Unknowns

Add to `docs/UNKNOWN_BYTES.md` or extend `PROTOCOL.md` with:

- byte offset;
- observed values;
- hypothesis;
- test performed;
- result.

## Recommended Hardware Result Format

```markdown
## Hardware test YYYY-MM-DD

- OS:
- Kernel:
- BlueZ:
- Python:
- bleak:
- Device BLE name:
- Device address:
- Firmware/app version if known:

| Test | Command | TX bytes | RX bytes | Expected | Observed | Status |
|---|---|---|---|---|---|---|
| on | `open-idotmatrix ... on` | `05 00 07 01 01` | ... | screen on | screen on | pass |
```

## Areas That Need Care

- `delete_device_data` can delete data from the device.
- Password/protection support is not integrated in the high-level API.
- Fuzzing unknown commands can leave firmware in a strange state; use `reset` if it gets stuck.
- Large GIFs can take a long time or fail because of timing.
