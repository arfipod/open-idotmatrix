# Test Plan

## Hardware-Free Tests

Run:

```bash
pytest
```

Covers:

- exact bytes for basic commands;
- coordinate and color validation;
- time encoding with two year strategies;
- text packet builder;
- text CRC32;
- GIF chunking;
- basic simulator behavior.

## Hardware Tests

Use a powered-on 32x32 iDotMatrix close to the PC.

Automated safe checklist:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF --session-log out/smoke.jsonl smoke-test --out out/smoke.json
```

The JSON report marks display-dependent checks as `needs_user_confirmation` so the observed result can be filled into the hardware report.

### 1. Scan

```bash
open-idotmatrix scan
```

Record:

- BLE name;
- address;
- RSSI.

### 2. On/Off

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF on
open-idotmatrix --address AA:BB:CC:DD:EE:FF off
open-idotmatrix --address AA:BB:CC:DD:EE:FF on
```

Expected: screen turns off/on.

### 3. Brightness

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF brightness 20
open-idotmatrix --address AA:BB:CC:DD:EE:FF brightness 80
```

Expected: visible brightness change.

### 4. Solid Color

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 255 0 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 255 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 0 255
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 0 0
```

Expected: red, green, blue, and black screen.

### 5. Pixel Orientation

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF fill 0 0 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 0 0 255 0 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 31 0 0 255 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 0 31 0 0 255
open-idotmatrix --address AA:BB:CC:DD:EE:FF pixel 31 31 255 255 255
```

Record real orientation:

| Coordinate | Color | Observed position |
|---|---|---|
| 0,0 | red | |
| 31,0 | green | |
| 0,31 | blue | |
| 31,31 | white | |

### 6. Time

Test both modes:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode low_byte
open-idotmatrix --address AA:BB:CC:DD:EE:FF clock 0
open-idotmatrix --address AA:BB:CC:DD:EE:FF sync-time --year-mode two_digit
open-idotmatrix --address AA:BB:CC:DD:EE:FF clock 0
```

Record which one displays the correct date/time if the clock mode shows a date.

### 7. Text

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "A" --mode 0 --rgb 255 255 255
open-idotmatrix --address AA:BB:CC:DD:EE:FF text "Hello" --mode 1 --speed 95 --rgb 255 0 0
```

Record:

- orientation;
- scroll direction;
- speed;
- real color.

### 8. GIF

Use a small GIF. If you do not have one, create it with Pillow or use an image and let the CLI process it.

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif
```

If it fails:

```bash
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --no-ack
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --total-length-mode raw_payload_only
open-idotmatrix --address AA:BB:CC:DD:EE:FF gif demo.gif --no-response
```

Record notifications if logging is available.

## Report Template

```markdown
# Hardware test

- Date:
- OS:
- Kernel:
- BlueZ:
- Python:
- bleak:
- Device name:
- Address:

| Test | Command | Expected | Observed | Status | Notes |
|---|---|---|---|---|---|
| scan | `open-idotmatrix scan` | find IDM-* | | | |
| on | `... on` | screen on | | | |
```
