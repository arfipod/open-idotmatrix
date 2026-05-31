"""Decode a raw packet from hex."""

import json
import sys

from open_idotmatrix.protocol import parse_packet

if len(sys.argv) < 2:
    raise SystemExit('usage: python examples/decode_packet.py "05 00 07 01 01"')

packet = bytes.fromhex(" ".join(sys.argv[1:]))
print(json.dumps(parse_packet(packet), indent=2, sort_keys=True))
