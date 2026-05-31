# Linux Bluetooth / BlueZ

## Requirements

Install Bluetooth/BlueZ according to your distribution.

Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y bluetooth bluez bluez-tools rfkill
sudo systemctl enable --now bluetooth
```

Check status:

```bash
rfkill list bluetooth
bluetoothctl show
```

If Bluetooth is blocked:

```bash
sudo rfkill unblock bluetooth
```

## Permissions

Normally `bleak` talks to BlueZ over D-Bus. If the user cannot access it, try:

```bash
sudo usermod -aG bluetooth "$USER"
```

Log out and log back in.

If it still fails, temporarily try root to isolate whether this is a permissions problem:

```bash
sudo .venv/bin/open-idotmatrix scan
```

## Scanning

```bash
open-idotmatrix scan
```

Expected output:

```json
[
  {
    "address": "AA:BB:CC:DD:EE:FF",
    "name": "IDM-xxxx",
    "rssi": -42
  }
]
```

## Manual Diagnostics With bluetoothctl

```bash
bluetoothctl
power on
scan on
```

Look for devices whose name starts with `IDM-`.

## Captures With btmon

```bash
sudo btmon | tee captures/session.btmon.txt
```

While `btmon` is active, run commands from another terminal.

## Common Problems

### The Device Does Not Appear

- Move the matrix closer to the PC.
- Restart Bluetooth: `sudo systemctl restart bluetooth`.
- Disconnect and reconnect matrix power.
- Check that the mobile app is not connected at the same time.
- Check `rfkill`.

### It Connects But Does Not Write

- Try `reset`.
- Try `--no-response` for GIFs.
- Try short commands first: `on`, `off`, `fill`.
- Add session logging as a roadmap task.

### GIF Fails

Try combinations:

```bash
open-idotmatrix --address ... gif demo.gif --total-length-mode include_headers
open-idotmatrix --address ... gif demo.gif --total-length-mode raw_payload_only
open-idotmatrix --address ... gif demo.gif --no-ack
open-idotmatrix --address ... gif demo.gif --no-response
```

Record which one works.
