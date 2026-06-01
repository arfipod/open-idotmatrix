# Architecture

## Layers

```text
CLI / examples / frame renderer
    |
OpenIDotMatrix       # high-level async API
    |
protocol.py          # pure bytes
transport.py         # BLE with bleak
    |
iDotMatrix 32x32
```

The simulator uses `protocol.py` and `text.py`, but it does not use BLE.

## Why Protocol And Transport Are Separate

This makes it possible to:

- test without hardware;
- compare bytes against captures;
- reuse the protocol with another BLE backend;
- add simulation and tooling without connecting to the matrix.

## Modules

| Module | Responsibility |
|---|---|
| `constants.py` | UUIDs, sizes, ACKs |
| `types.py` | enums and basic validation |
| `protocol.py` | packet building/parsing |
| `text.py` | PIL -> 16x32 bitmaps |
| `gif.py` | GIF/image -> 32x32 GIF -> chunks |
| `framebuffer.py` | Bytearray-backed 32x32 RGB frames and frame diffing |
| `renderer.py` | Chooses fill, pixel diff, or single-frame GIF update strategies |
| `profile.py` | Per-device protocol and transport defaults discovered during hardware testing |
| `session.py` | JSONL TX/RX logging for reverse-engineering sessions |
| `transport.py` | BLE scan/connect/write/notify |
| `device.py` | convenient async API |
| `simulator.py` | local 32x32 view |
| `cli.py` | user commands |
| `qt_app.py` | optional Qt app launcher |
| `qt_window.py` | optional Qt desktop UI |

## Stability

- `protocol.py`: should be the most tested and stable part.
- `transport.py`: may need BlueZ/MTU adjustments.
- `gif.py`: will likely need firmware-specific validation.
- `simulator.py`: approximate; it is not intended to exactly replicate firmware behavior.
