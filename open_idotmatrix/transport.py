"""BLE transport for Linux and other Bleak-supported platforms."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from .constants import DEVICE_NAME_PREFIX, NOTIFY_UUID, WRITE_UUID
from .exceptions import AckTimeoutError, DeviceNotFoundError, TransportError

NotificationCallback = Callable[[bytes], None]


@dataclass(frozen=True)
class DiscoveredDevice:
    address: str
    name: str
    rssi: int | None = None


class BleTransport:
    """Thin async wrapper around BleakClient.

    It deliberately keeps protocol-level chunking outside the transport. This
    class only handles BLE scanning, connection, GATT write splitting and
    notification queues.
    """

    def __init__(
        self,
        address: str | None = None,
        *,
        name_prefix: str = DEVICE_NAME_PREFIX,
        write_uuid: str = WRITE_UUID,
        notify_uuid: str = NOTIFY_UUID,
        inter_write_delay: float = 0.01,
    ) -> None:
        self.address = address
        self.name_prefix = name_prefix
        self.write_uuid = write_uuid
        self.notify_uuid = notify_uuid
        self.inter_write_delay = inter_write_delay
        self.client = None
        self._notification_queue: asyncio.Queue[bytes] | None = None
        self._user_notification_callback: NotificationCallback | None = None

    @staticmethod
    def _import_bleak():
        try:
            from bleak import BleakClient, BleakScanner
        except Exception as exc:  # pragma: no cover - environment dependent
            raise TransportError("Bleak is required for BLE hardware access: pip install bleak") from exc
        return BleakClient, BleakScanner

    @classmethod
    async def scan(cls, *, timeout: float = 5.0, name_prefix: str = DEVICE_NAME_PREFIX) -> list[DiscoveredDevice]:
        """Scan for devices whose advertised local name starts with IDM-."""

        _BleakClient, BleakScanner = cls._import_bleak()
        discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
        devices: list[DiscoveredDevice] = []
        for _key, (device, adv) in discovered.items():
            name = getattr(adv, "local_name", None) or getattr(device, "name", None) or ""
            if name.startswith(name_prefix):
                devices.append(
                    DiscoveredDevice(
                        address=str(device.address),
                        name=str(name),
                        rssi=getattr(adv, "rssi", None) or getattr(device, "rssi", None),
                    )
                )
        return devices

    @classmethod
    async def first_device(cls, *, timeout: float = 5.0, name_prefix: str = DEVICE_NAME_PREFIX) -> DiscoveredDevice:
        devices = await cls.scan(timeout=timeout, name_prefix=name_prefix)
        if not devices:
            raise DeviceNotFoundError(f"no device found with BLE name prefix {name_prefix!r}")
        return devices[0]

    async def connect(self) -> None:
        if not self.address:
            device = await self.first_device(name_prefix=self.name_prefix)
            self.address = device.address
        BleakClient, _BleakScanner = self._import_bleak()
        if self.client is None:
            self.client = BleakClient(self.address)
        if not self.client.is_connected:
            await self.client.connect()

    async def disconnect(self) -> None:
        if self.client is not None and self.client.is_connected:
            with contextlib.suppress(Exception):
                await self.stop_notifications()
            await self.client.disconnect()

    async def __aenter__(self) -> "BleTransport":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()

    def is_connected(self) -> bool:
        return bool(self.client is not None and self.client.is_connected)

    def _gatt_chunk_size(self, *, response: bool) -> int:
        if self.client is None:
            return 20
        try:
            characteristic = self.client.services.get_characteristic(self.write_uuid)
            size = int(getattr(characteristic, "max_write_without_response_size", 20) or 20)
        except Exception:
            size = 20
        # With response, many stacks allow larger writes, but 20 is the safest
        # cross-device default. Codex/hardware testing can tune this later.
        return max(1, size if not response else min(size, 20))

    async def write(self, data: bytes | bytearray, *, response: bool = False) -> None:
        """Write bytes to the device, splitting into GATT-sized chunks."""

        if self.client is None or not self.client.is_connected:
            await self.connect()
        if self.client is None:  # pragma: no cover - defensive
            raise TransportError("BLE client was not initialized")
        data = bytes(data)
        chunk_size = self._gatt_chunk_size(response=response)
        for offset in range(0, len(data), chunk_size):
            chunk = data[offset : offset + chunk_size]
            await self.client.write_gatt_char(self.write_uuid, chunk, response=response)
            if self.inter_write_delay:
                await asyncio.sleep(self.inter_write_delay)

    async def start_notifications(self, callback: NotificationCallback | None = None) -> None:
        if self.client is None or not self.client.is_connected:
            await self.connect()
        if self.client is None:  # pragma: no cover - defensive
            raise TransportError("BLE client was not initialized")
        self._notification_queue = asyncio.Queue()
        self._user_notification_callback = callback

        def _callback(_sender, data: bytearray) -> None:
            payload = bytes(data)
            if self._notification_queue is not None:
                self._notification_queue.put_nowait(payload)
            if self._user_notification_callback is not None:
                self._user_notification_callback(payload)

        await self.client.start_notify(self.notify_uuid, _callback)

    async def stop_notifications(self) -> None:
        if self.client is not None and self.client.is_connected:
            with contextlib.suppress(Exception):
                await self.client.stop_notify(self.notify_uuid)
        self._notification_queue = None
        self._user_notification_callback = None

    async def wait_for_notification(
        self,
        expected: bytes | Sequence[bytes] | None = None,
        *,
        timeout: float = 5.0,
    ) -> bytes:
        """Wait for a notification, optionally matching one of several byte patterns."""

        if self._notification_queue is None:
            await self.start_notifications()
        assert self._notification_queue is not None
        expected_values: tuple[bytes, ...] | None
        if expected is None:
            expected_values = None
        elif isinstance(expected, bytes):
            expected_values = (expected,)
        else:
            expected_values = tuple(bytes(item) for item in expected)

        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise AckTimeoutError("timed out waiting for BLE notification")
            payload = await asyncio.wait_for(self._notification_queue.get(), timeout=remaining)
            if expected_values is None or payload in expected_values:
                return payload

    async def write_chunks_with_acks(
        self,
        chunks: Iterable[bytes | bytearray],
        *,
        expected_acks: Iterable[bytes],
        response: bool = True,
        timeout: float = 10.0,
    ) -> list[bytes]:
        """Write application-level chunks and wait for one expected ACK per chunk."""

        await self.start_notifications()
        received: list[bytes] = []
        for chunk, expected in zip(chunks, expected_acks, strict=True):
            await self.write(chunk, response=response)
            received.append(await self.wait_for_notification(expected, timeout=timeout))
        return received
