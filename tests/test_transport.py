import asyncio
import json

import pytest

from open_idotmatrix.constants import ACK_CHUNK_OK, NOTIFY_UUID, WRITE_UUID
from open_idotmatrix.exceptions import AckTimeoutError
from open_idotmatrix.protocol import build_screen_on
from open_idotmatrix.session import SessionLogger
from open_idotmatrix.transport import BleTransport


@pytest.mark.asyncio
async def test_wait_for_notification_timeout_uses_package_exception():
    transport = BleTransport(address="test-device")
    transport._notification_queue = asyncio.Queue()

    with pytest.raises(AckTimeoutError, match="timed out waiting for BLE notification"):
        await transport.wait_for_notification(b"\x01", timeout=0.01)


class FakeServices:
    def get_characteristic(self, _uuid):
        return type("Characteristic", (), {"max_write_without_response_size": 20})()


class FakeClient:
    is_connected = True
    services = FakeServices()

    def __init__(self):
        self.writes = []
        self.notification_callback = None

    async def write_gatt_char(self, uuid, data, *, response=False):
        self.writes.append((uuid, bytes(data), response))

    async def start_notify(self, _uuid, callback):
        self.notification_callback = callback


@pytest.mark.asyncio
async def test_write_many_packets_and_session_logger(tmp_path):
    logger = SessionLogger(tmp_path / "session.jsonl")
    client = FakeClient()
    transport = BleTransport(
        address="test-device",
        inter_write_delay=0.0,
        gatt_chunk_size=20,
        session_logger=logger,
    )
    transport.client = client

    await transport.write_many_packets([build_screen_on(), b"\x01\x02"], response=True)
    await transport.start_notifications()
    client.notification_callback(NOTIFY_UUID, bytearray(ACK_CHUNK_OK))

    assert client.writes == [
        (WRITE_UUID, build_screen_on(), True),
        (WRITE_UUID, b"\x01\x02", True),
    ]
    lines = [json.loads(line) for line in (tmp_path / "session.jsonl").read_text().splitlines()]
    assert lines[0]["direction"] == "tx"
    assert lines[0]["uuid"] == WRITE_UUID
    assert lines[0]["kind"] == "screen_on"
    assert lines[-1]["direction"] == "rx"
    assert lines[-1]["uuid"] == NOTIFY_UUID
    assert lines[-1]["kind"] == "ack_chunk_ok"
