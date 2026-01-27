"""Log manager for storing device messages."""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LogEntry:
    """A single log entry from a device."""
    timestamp: float
    device_id: str
    msg_type: str
    source: str
    payload: str
    request_id: Optional[str] = None


class LogManager:
    """Manages log storage for device messages."""

    def __init__(self, max_entries_per_device: int = 1000):
        self.max_entries = max_entries_per_device
        self._logs: Dict[str, List[LogEntry]] = {}

    def add(self, device_id: str, msg_type: str, source: str, payload: str, request_id: str = None):
        if device_id not in self._logs:
            self._logs[device_id] = []

        entry = LogEntry(
            timestamp=time.time(),
            device_id=device_id,
            msg_type=msg_type,
            source=source,
            payload=payload,
            request_id=request_id
        )

        self._logs[device_id].append(entry)

        if len(self._logs[device_id]) > self.max_entries:
            self._logs[device_id] = self._logs[device_id][-self.max_entries:]

    def get_logs(self, device_id: str, limit: int = 100) -> List[LogEntry]:
        if device_id not in self._logs:
            return []
        return self._logs[device_id][-limit:]

    def get_all_logs(self, limit: int = 100) -> List[LogEntry]:
        all_entries = []
        for entries in self._logs.values():
            all_entries.extend(entries)
        all_entries.sort(key=lambda e: e.timestamp)
        return all_entries[-limit:]

    def clear(self, device_id: str = None):
        if device_id:
            self._logs.pop(device_id, None)
        else:
            self._logs.clear()

    def device_count(self) -> int:
        return len(self._logs)

    def total_entries(self) -> int:
        return sum(len(entries) for entries in self._logs.values())
