# Security and Safety

This project controls BLE hardware. Some operations can leave the device in an unusual state or delete data.

## Do Not Do By Default

- Do not fuzz unknown commands on devices you cannot reset.
- Do not run `delete_device_data` unless explicitly instructed.
- Do not publish logs containing personal BLE addresses if privacy matters.
- Do not assume all iDotMatrix devices share the same firmware.

## Reporting Issues

For vulnerabilities or dangerous behavior, open an issue describing:

- device;
- firmware/app version if known;
- sent commands;
- observed effect;
- whether the issue is reproducible.
