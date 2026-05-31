# Hardware test report

Copy this file to `captures/YYYY-MM-DD-hardware-test.md` when testing a real matrix.

## Environment

- Date:
- Operator:
- OS:
- Kernel:
- BlueZ:
- Python:
- bleak:
- open-idotmatrix commit:
- Device advertised name:
- Device address:
- Matrix size: 32x32
- Firmware/app version if known:

## Results

| Test | Command | TX bytes | RX bytes | Expected | Observed | Status | Notes |
|---|---|---|---|---|---|---|---|
| scan | `open-idotmatrix scan` | n/a | n/a | finds IDM-* | | | |
| on | `open-idotmatrix --address ... on` | `05 00 07 01 01` | | screen on | | | |
| off | `open-idotmatrix --address ... off` | `05 00 07 01 00` | | screen off | | | |
| brightness | `... brightness 50` | `05 00 04 80 32` | | dimmer | | | |
| fill red | `... fill 255 0 0` | `07 00 02 02 ff 00 00` | | red | | | |
| pixel 0,0 | `... pixel 0 0 255 0 0` | `0a 00 05 01 00 ff 00 00 00 00` | | red corner | | | |
| text A | `... text A --mode 0` | generated | | A visible | | | |
| gif | `... gif demo.gif` | generated chunks | | GIF visible | | | |

## Notes

- Orientation notes:
- GIF ACK notes:
- Any crashes/recovery:
- Protocol changes needed:
