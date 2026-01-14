import threading


class GroupRegistry:
    def __init__(self):
        self._groups: dict[str, set[str]] = {}
        self._lock = threading.Lock()

    def add_group(self, name: str):
        with self._lock:
            self._groups.setdefault(name, set())

    def delete_group(self, name: str):
        with self._lock:
            self._groups.pop(name, None)

    def add_device(self, group: str, esp_id: str):
        with self._lock:
            self._groups.setdefault(group, set()).add(esp_id)

    def remove_device(self, group: str, esp_id: str):
        with self._lock:
            if group in self._groups:
                self._groups[group].discard(esp_id)
                if not self._groups[group]:
                    del self._groups[group]

    def get(self, group: str) -> set[str]:
        with self._lock:
            return set(self._groups.get(group, []))

    def all_groups(self) -> dict[str, set[str]]:
        with self._lock:
            return {k: set(v) for k, v in self._groups.items()}
