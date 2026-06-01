import pytest

from open_idotmatrix.device import OpenIDotMatrix
from open_idotmatrix.exceptions import ProtocolError
from open_idotmatrix.profile import DeviceProfile
from open_idotmatrix.types import GifAckPolicy, GifTotalLengthMode, YearByteMode


def test_device_profile_normalizes_enums_and_drives_transport_defaults():
    profile = DeviceProfile(
        address="AA:BB",
        gif_total_length_mode="raw_payload_only",
        gif_ack_policy="ok_or_done",
        year_byte_mode="two_digit",
        inter_write_delay=0.2,
        gatt_chunk_size=123,
    )
    matrix = OpenIDotMatrix(profile=profile)

    assert profile.gif_total_length_mode is GifTotalLengthMode.RAW_PAYLOAD_ONLY
    assert profile.gif_ack_policy is GifAckPolicy.OK_OR_DONE
    assert profile.year_byte_mode is YearByteMode.TWO_DIGIT
    assert matrix.transport.address == "AA:BB"
    assert matrix.transport.inter_write_delay == 0.2
    assert matrix.transport.gatt_chunk_size == 123


def test_device_profile_validates_batch_mode():
    with pytest.raises(ProtocolError):
        DeviceProfile(pixel_batch_mode="packed")
