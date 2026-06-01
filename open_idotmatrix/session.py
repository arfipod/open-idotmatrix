"""Structured JSONL session logging for BLE reverse engineering."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .constants import ACK_CHUNK_OK, ACK_UPLOAD_DONE
from .protocol import parse_packet


class SessionLogger:
    """Append TX/RX BLE events to a JSONL file.

    The logger is intentionally synchronous so it can be called safely from
    Bleak notification callbacks. Each line is self-contained and easy to grep,
    diff, or attach to hardware reports.
    """

    def __init__(self, path: str | Path, *, append: bool = False) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not append:
            self.path.write_text("", encoding="utf-8")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @staticmethod
    def _kind(data: bytes, *, direction: str, kind: str | None = None) -> str:
        if kind:
            return kind
        if data == ACK_CHUNK_OK:
            return "ack_chunk_ok"
        if data == ACK_UPLOAD_DONE:
            return "ack_upload_done"
        parsed_kind = str(parse_packet(data).get("kind", "unknown"))
        if direction == "rx" and parsed_kind == "unknown":
            return "notification"
        return parsed_kind

    def log(
        self,
        direction: str,
        data: bytes | bytearray,
        *,
        uuid: str | None = None,
        kind: str | None = None,
    ) -> dict[str, str]:
        payload = bytes(data)
        entry = {
            "ts": self._timestamp(),
            "direction": direction,
            "hex": payload.hex(" "),
            "kind": self._kind(payload, direction=direction, kind=kind),
        }
        if uuid is not None:
            entry["uuid"] = uuid
        line = json.dumps(entry, sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
        return entry

    def tx(self, data: bytes | bytearray, *, uuid: str | None = None, kind: str | None = None) -> dict[str, str]:
        return self.log("tx", data, uuid=uuid, kind=kind)

    def rx(self, data: bytes | bytearray, *, uuid: str | None = None, kind: str | None = None) -> dict[str, str]:
        return self.log("rx", data, uuid=uuid, kind=kind)


__all__ = ["SessionLogger"]
