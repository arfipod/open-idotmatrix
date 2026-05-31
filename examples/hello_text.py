"""Send text to a real iDotMatrix display.

Usage:
    python examples/hello_text.py AA:BB:CC:DD:EE:FF
"""

import asyncio
import sys

from open_idotmatrix import OpenIDotMatrix, TextMode


async def main(address: str) -> None:
    async with OpenIDotMatrix(address=address) as matrix:
        await matrix.on()
        await matrix.set_brightness(80)
        await matrix.text("Hola", mode=TextMode.SCROLL_LEFT_TO_RIGHT, color=(255, 255, 255))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python examples/hello_text.py AA:BB:CC:DD:EE:FF")
    asyncio.run(main(sys.argv[1]))
