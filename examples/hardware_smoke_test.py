"""Safe smoke test for a real iDotMatrix 32x32 display.

Usage:
    python examples/hardware_smoke_test.py AA:BB:CC:DD:EE:FF
"""

import asyncio
import sys

from open_idotmatrix import OpenIDotMatrix


async def main(address: str) -> None:
    async with OpenIDotMatrix(address=address) as matrix:
        await matrix.on()
        await matrix.set_brightness(80)
        await matrix.fill((255, 0, 0))
        await asyncio.sleep(0.5)
        await matrix.fill((0, 255, 0))
        await asyncio.sleep(0.5)
        await matrix.fill((0, 0, 255))
        await asyncio.sleep(0.5)
        await matrix.fill((0, 0, 0))
        await matrix.pixel(0, 0, (255, 0, 0))
        await matrix.pixel(31, 0, (0, 255, 0))
        await matrix.pixel(0, 31, (0, 0, 255))
        await matrix.pixel(31, 31, (255, 255, 255))
        await asyncio.sleep(1.0)
        await matrix.text("OK", color=(255, 255, 255), mode=0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python examples/hardware_smoke_test.py AA:BB:CC:DD:EE:FF")
    asyncio.run(main(sys.argv[1]))
