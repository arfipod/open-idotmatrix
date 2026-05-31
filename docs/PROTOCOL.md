# iDotMatrix 32x32 Protocol

This document summarizes the known protocol for a 32x32 RGB iDotMatrix display accessible over BLE.

The protocol is not complete. Sections marked as `experimental` or `hypothesis` must be validated with real hardware and traces.

## BLE

| Field | Value |
|---|---|
| Expected BLE name | `IDM-` prefix |
| Service UUID | `000000fa-0000-1000-8000-00805f9b34fb` |
| Write UUID | `0000fa02-0000-1000-8000-00805f9b34fb` |
| Notify UUID | `0000fa03-0000-1000-8000-00805f9b34fb` |

Observed basic packets do not require encryption.

## Conventions

- Multi-byte length fields are little-endian unless stated otherwise.
- Colors are encoded as RGB: `r g b`.
- This repository validates coordinates for a 32x32 matrix: `x = 0..31`, `y = 0..31`.
- Builders in `open_idotmatrix.protocol` return pure `bytes`.

## Basic Commands

### Screen On

```text
05 00 07 01 01
```

### Screen Off

```text
05 00 07 01 00
```

### Brightness

```text
05 00 04 80 <brightness>
```

Likely range: `5..100`.

Example, 80%:

```text
05 00 04 80 50
```

### Flip / 180-Degree Rotation

```text
05 00 06 80 <enabled>
```

`enabled = 00` normal, `01` rotated.

### Freeze / Unfreeze

```text
04 00 03 00
```

Status: inconsistent. Do not rely on this for critical features until it is validated.

### Recovery / Soft Reset

```text
04 00 03 80
05 00 04 80 50
```

Note: the second packet is identical to brightness 80. This repository treats the operation as `reset/recover`, not as a factory reset.

## Time

Format:

```text
0b 00 01 80 <year_byte> <month> <day> <dow> <hour> <minute> <second>
```

`dow` uses Monday = 1, Sunday = 7.

Two known strategies exist for `year_byte`:

| Strategy | Calculation |
|---|---|
| `low_byte` | `year & 0xff` |
| `two_digit` | `year % 100` |

This repository uses `low_byte` by default, but exposes both for testing:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode low_byte
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode two_digit
```

## Pixel / Graffiti

Format:

```text
0a 00 05 01 00 <r> <g> <b> <x> <y>
```

Example: red pixel in the lower-right corner:

```text
0a 00 05 01 00 ff 00 00 1f 1f
```

## Full-Screen Color

Format:

```text
07 00 02 02 <r> <g> <b>
```

Example: red:

```text
07 00 02 02 ff 00 00
```

## Clock

Known format:

```text
08 00 06 01 <flags> <r> <g> <b>
```

Flags:

```python
flags = style | (0x80 if visible_date else 0x00) | (0x40 if hour24 else 0x00)
```

Known `style`: `0..7`.

## Chronograph

```text
05 00 09 80 <mode>
```

Known modes:

| Mode | Action |
|---:|---|
| 0 | reset |
| 1 | start/restart |
| 2 | pause |
| 3 | continue |

## Countdown

```text
07 00 08 80 <mode> <minutes> <seconds>
```

Known modes:

| Mode | Action |
|---:|---|
| 0 | disable |
| 1 | start |
| 2 | pause |
| 3 | restart |

## Scoreboard

```text
08 00 0a 80 <left_lo> <left_hi> <right_lo> <right_hi>
```

Recommended scores: `0..999`.

## Eco Mode

```text
0a 00 02 80 <flag> <start_hour> <start_minute> <end_hour> <end_minute> <brightness>
```

Status: partially known.

## Effects

Implemented format:

```text
<length> 00 03 02 <style> <speed> <num_colors> <r1> <g1> <b1> ...
```

Styles known from community notes:

| Style | Tentative description |
|---:|---|
| 0 | horizontal gradient rainbow |
| 1 | random colored pixels on black |
| 2 | random white pixels on changing background |
| 3 | vertical rainbow |
| 4 | diagonal rainbow to the right |
| 5 | diagonal rainbow to the left on black |
| 6 | random colored pixels |

## 32x32 Text

Text is not sent as plain UTF-8. Each character is rendered to a monochrome 16x32 bitmap.

Each character:

```text
05 ff ff ff <64 bitmap bytes>
```

The bitmap is row-major and little-endian within each byte:

- 16 pixels per row;
- 32 rows;
- 2 bytes per row;
- 64 bytes per character.

### Complete Text Packet

```text
[16-byte header] [14-byte metadata] [glyph blocks]
```

Header:

| Offset | Size | Description |
|---:|---:|---|
| 0 | 2 | total length including header |
| 2 | 1 | `03` |
| 3 | 1 | `00` |
| 4 | 1 | continuation marker, usually `00` |
| 5 | 4 | metadata + bitmap length |
| 9 | 4 | CRC32 of metadata + bitmaps |
| 13 | 2 | `00 00` |
| 15 | 1 | `0c` |

Metadata:

| Offset | Size | Description |
|---:|---:|---|
| 0 | 2 | number of characters |
| 2 | 1 | `00` |
| 3 | 1 | `01` |
| 4 | 1 | text mode |
| 5 | 1 | speed |
| 6 | 1 | text color mode |
| 7 | 1 | text R |
| 8 | 1 | text G |
| 9 | 1 | text B |
| 10 | 1 | background mode |
| 11 | 1 | background R |
| 12 | 1 | background G |
| 13 | 1 | background B |

Known text modes:

| Value | Effect |
|---:|---|
| 0 | fixed |
| 1 | left/right scroll, depending on firmware/app |
| 2 | reverse scroll / RTL |
| 3 | scroll up |
| 4 | scroll down |
| 5 | strobe / blink |
| 6 | fade |
| 7 | falling blocks |
| 8 | laser / filling |

Color modes:

| Value | Effect |
|---:|---|
| 0 | unknown / app default |
| 1 | fixed RGB |
| 2 | blue-red gradient |
| 3 | pastel gradient |
| 4 | pink-orange gradient |
| 5 | unknown |

Background:

| Value | Effect |
|---:|---|
| 0 | off / black |
| 1 | solid RGB |

## GIFs

The most useful path for images and animations is uploading 32x32 GIFs.

GIFs are split into 4096-byte chunks. Each application chunk has a 16-byte header:

```text
[16-byte header] [up to 4096 GIF bytes]
```

Header:

| Offset | Size | Description |
|---:|---:|---|
| 0 | 2 | length of this chunk including header |
| 2 | 1 | `01` |
| 3 | 1 | `00` |
| 4 | 1 | `00` first chunk, `02` following chunks |
| 5 | 4 | total length, mode to validate |
| 9 | 4 | CRC32 of the full GIF |
| 13 | 1 | `05` |
| 14 | 1 | `00` |
| 15 | 1 | `0d` |

There are two variants for the `total_length` field:

| Mode | Calculation |
|---|---|
| `include_headers` | `len(gif_bytes) + 16 * num_chunks` |
| `raw_payload_only` | `len(gif_bytes)` |

The repository uses `include_headers` by default, but lets you choose:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --total-length-mode include_headers
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --total-length-mode raw_payload_only
```

Expected notifications:

```text
05 00 01 00 01 = chunk accepted / continue
05 00 01 00 03 = upload finished
```

## Still Images

Still images are uploaded through the same GIF chunk protocol. The image path is:

1. load the first frame of any Pillow-supported image;
2. stretch or squash it directly to a 1:1 square;
3. nearest-neighbor sample it to 32x32;
4. encode it as a single-frame GIF;
5. upload it with the GIF chunk protocol above.

This intentionally does not preserve aspect ratio. It matches the behavior requested for LED-matrix display: every source image fills the entire 32x32 matrix.

## PNG / DIY Image

An experimental `build_png_payloads_experimental` function exists. It is not included in the main API because single-frame GIFs should be safer for still images until more traces are validated.

## Destructive Commands

`build_delete_device_data()` exists to document the protocol, but it must not be used during fuzzing or initial testing.

## How To Add New Commands

1. Capture or infer bytes.
2. Add a pure builder in `open_idotmatrix/protocol.py`.
3. Add parser support in `parse_packet` when applicable.
4. Add a high-level method in `device.py`.
5. Add CLI support if useful.
6. Add exact-byte tests.
7. Document the format and status here: confirmed, experimental, or hypothesis.
