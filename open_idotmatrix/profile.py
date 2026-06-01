"""Device profile defaults for firmware-specific behavior."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .exceptions import ProtocolError
from .types import GifAckPolicy, GifTotalLengthMode, YearByteMode


@dataclass(frozen=True)
class DeviceProfile:
    """Known or assumed behavior for one concrete matrix.

    Profiles keep hardware discoveries explicit instead of baking them into
    packet builders. The default profile is conservative and matches the
    current public notes for the 32x32 iDotMatrix.
    """

    name: str = "default-32x32"
    address: str | None = None
    gif_total_length_mode: GifTotalLengthMode | str = GifTotalLengthMode.INCLUDE_HEADERS
    year_byte_mode: YearByteMode | str = YearByteMode.LOW_BYTE
    inter_write_delay: float = 0.0
    gatt_chunk_size: int | None = None
    write_response: bool = False
    gif_wait_for_ack: bool = True
    gif_ack_policy: GifAckPolicy | str = GifAckPolicy.EXACT
    orientation: str = "normal"
    pixel_batch_mode: str = "separate"

    def __post_init__(self) -> None:
        object.__setattr__(self, "gif_total_length_mode", GifTotalLengthMode(self.gif_total_length_mode))
        object.__setattr__(self, "year_byte_mode", YearByteMode(self.year_byte_mode))
        object.__setattr__(self, "gif_ack_policy", GifAckPolicy(self.gif_ack_policy))
        if self.inter_write_delay < 0:
            raise ProtocolError("inter_write_delay must be non-negative")
        if self.gatt_chunk_size is not None and self.gatt_chunk_size <= 0:
            raise ProtocolError("gatt_chunk_size must be positive")
        if self.pixel_batch_mode not in {"separate", "concatenate"}:
            raise ProtocolError("pixel_batch_mode must be 'separate' or 'concatenate'")
        if not self.orientation:
            raise ProtocolError("orientation must be a non-empty string")

    def with_address(self, address: str | None) -> DeviceProfile:
        return replace(self, address=address)


__all__ = ["DeviceProfile"]
