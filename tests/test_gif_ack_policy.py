import pytest

from open_idotmatrix.constants import ACK_CHUNK_OK, ACK_UPLOAD_DONE
from open_idotmatrix.device import OpenIDotMatrix
from open_idotmatrix.profile import DeviceProfile
from open_idotmatrix.protocol import build_gif_chunks
from open_idotmatrix.testing import FakeTransport
from open_idotmatrix.types import GifAckPolicy


class AutoNotifyTransport(FakeTransport):
    def __init__(self, ack_groups):
        super().__init__()
        self.ack_groups = [list(group) for group in ack_groups]

    async def write(self, data, *, response=False):
        await super().write(data, response=response)
        for ack in self.ack_groups.pop(0):
            self.push_notification(ack)


@pytest.mark.asyncio
async def test_wait_done_after_final_accepts_ok_then_done_on_final_chunk():
    chunks = build_gif_chunks(b"GIF89a" + b"x" * 20)
    transport = AutoNotifyTransport([[ACK_CHUNK_OK, ACK_UPLOAD_DONE]])
    matrix = OpenIDotMatrix(
        transport=transport,
        profile=DeviceProfile(gif_ack_policy=GifAckPolicy.WAIT_DONE_AFTER_FINAL),
    )

    await matrix._send_upload_chunks(
        chunks,
        wait_for_ack=True,
        ack_policy=GifAckPolicy.WAIT_DONE_AFTER_FINAL,
        response=True,
        ack_timeout=0.01,
        sleep_between_chunks=0.0,
    )

    assert transport.notification_history == [ACK_CHUNK_OK, ACK_UPLOAD_DONE]
    assert len(transport.writes) == 1


@pytest.mark.asyncio
async def test_ok_or_done_policy_accepts_upload_done():
    chunks = build_gif_chunks(b"GIF89a" + b"x" * 20)
    transport = AutoNotifyTransport([[ACK_UPLOAD_DONE]])
    matrix = OpenIDotMatrix(transport=transport)

    await matrix._send_upload_chunks(
        chunks,
        wait_for_ack=True,
        ack_policy=GifAckPolicy.OK_OR_DONE,
        response=True,
        ack_timeout=0.01,
        sleep_between_chunks=0.0,
    )

    assert transport.notification_history == [ACK_UPLOAD_DONE]


@pytest.mark.asyncio
async def test_none_ack_policy_skips_notifications_and_uses_sleep_path():
    chunks = build_gif_chunks(b"GIF89a" + b"x" * 20)
    transport = FakeTransport()
    matrix = OpenIDotMatrix(transport=transport)

    await matrix._send_upload_chunks(
        chunks,
        wait_for_ack=True,
        ack_policy=GifAckPolicy.NONE,
        response=False,
        ack_timeout=0.01,
        sleep_between_chunks=0.0,
    )

    assert transport.notifications_started_count == 0
    assert len(transport.writes) == 1
