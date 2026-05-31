import asyncio

import pytest

from open_idotmatrix.exceptions import AckTimeoutError
from open_idotmatrix.transport import BleTransport


@pytest.mark.asyncio
async def test_wait_for_notification_timeout_uses_package_exception():
    transport = BleTransport(address="test-device")
    transport._notification_queue = asyncio.Queue()

    with pytest.raises(AckTimeoutError, match="timed out waiting for BLE notification"):
        await transport.wait_for_notification(b"\x01", timeout=0.01)
