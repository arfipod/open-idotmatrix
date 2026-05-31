# Reverse Engineering Process

## Goal

Complete the iDotMatrix 32x32 protocol in a reproducible way, with tests and documentation.

## Sources Of Truth

1. What real hardware does.
2. BLE captures from the official app or this library.
3. Exact-byte tests.
4. Documentation in `docs/PROTOCOL.md`.

## Capturing Traffic On Linux

With BlueZ, use `btmon`:

```bash
sudo btmon | tee captures/session.btmon.txt
```

Run commands in another terminal:

```bash
open-idotmatrix scan
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "Hello"
```

Then look for writes to `fa02` and notifications from `fa03`.

## Capturing Traffic From Android

Android often has an option to enable HCI snoop logs in Developer Options. The exact name depends on the manufacturer. The general flow is:

1. Enable Bluetooth HCI snoop log.
2. Open the official iDotMatrix app.
3. Perform one specific action, such as changing the clock or sending text.
4. Export the log.
5. Open it with Wireshark.
6. Filter by GATT writes/notifies and UUID `fa02`/`fa03`.

Do not upload captures with personal information or private BLE addresses if the repository is public.

## Recommended Log Format

Create text or JSONL files with this structure:

```json
{"direction":"tx","uuid":"0000fa02-0000-1000-8000-00805f9b34fb","hex":"05 00 07 01 01","note":"screen on"}
{"direction":"rx","uuid":"0000fa03-0000-1000-8000-00805f9b34fb","hex":"05 00 01 00 01","note":"chunk ack"}
```

## Method For Decoding New Commands

1. Run one action in the official app.
2. Capture bytes.
3. Repeat with one changed parameter.
4. Compare byte-by-byte diffs.
5. Isolate fields.
6. Create a builder in `protocol.py`.
7. Add parser support in `parse_packet`.
8. Add a unit test.
9. Test with hardware.
10. Document the result.

## Do Not Do Initially

- Do not fuzz destructive commands.
- Do not send huge payloads without limits.
- Do not test passwords/protection until there is a clear recovery path.
- Do not assume all iDotMatrix firmware behaves the same way.

## Important Current Hypotheses

| Topic | Hypothesis | Required action |
|---|---|---|
| Year in `sync-time` | `year & 0xff` or `year % 100` | test clock/date after sync |
| GIF total length | includes headers or raw payload | test both modes |
| Final GIF ACK | last chunk replies `0500010003` | record notifications |
| Text mode 1/2 | direction depends on firmware/app | test visually |
| PNG/DIY | format not confirmed | prioritize single-frame GIF |

## Repository Tools

Decode a packet:

```bash
open-idotmatrix decode "0a 00 05 01 00 ff 00 00 1f 1f"
```

Simulate a packet:

```bash
open-idotmatrix simulate --packet-hex "07 00 02 02 00 00 ff" --save out/blue.png
```

Generate and visualize text:

```bash
open-idotmatrix simulate --text "ABC" --save out/abc.png
```
