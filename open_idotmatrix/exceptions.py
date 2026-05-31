"""Exceptions raised by open-idotmatrix."""


class OpenIDotMatrixError(Exception):
    """Base exception for this package."""


class ProtocolError(OpenIDotMatrixError):
    """Raised when packet construction or parsing fails."""


class TransportError(OpenIDotMatrixError):
    """Raised when BLE transport fails."""


class DeviceNotFoundError(TransportError):
    """Raised when no iDotMatrix-like device is found."""


class AckTimeoutError(TransportError):
    """Raised when the device does not send the expected protocol-level ACK."""
