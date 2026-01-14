import threading
import socket # Added missing import
from typing import Dict, List, Optional
from core.device import Device


class DeviceRegistry:
    """
    Registre central des ESP connectés.
    Clé primaire : esp_id
    """
    def __init__(self):
        self._devices: Dict[str, Device] = {}
        self._lock = threading.Lock()

    # ---------- Gestion des devices ----------

    def add(self, device: Device) -> None:
        """
        Ajoute ou remplace un device (reconnexion)
        """
        with self._lock:
            self._devices[device.id] = device

    def remove(self, esp_id: str) -> None:
        """
        Supprime un device par ID
        """
        with self._lock:
            device = self._devices.pop(esp_id, None)
            if device:
                device.close()

    def get(self, esp_id: str) -> Optional[Device]:
        """
        Récupère un device par ID
        """
        with self._lock:
            return self._devices.get(esp_id)

    def get_device_by_sock(self, sock: socket.socket) -> Optional[Device]:
        """
        Récupère un device par son objet socket.
        """
        with self._lock:
            for device in self._devices.values():
                if device.sock == sock:
                    return device
            return None

    def all(self) -> List[Device]:
        """
        Retourne la liste de tous les devices
        """
        with self._lock:
            return list(self._devices.values())

    def ids(self) -> List[str]:
        """
        Retourne la liste des IDs ESP (pour CLI / tabulation)
        """
        with self._lock:
            return list(self._devices.keys())

    # ---------- Utilitaires ----------

    def exists(self, esp_id: str) -> bool:
        with self._lock:
            return esp_id in self._devices

    def touch(self, esp_id: str) -> None:
        """
        Met à jour last_seen d’un ESP
        """
        with self._lock:
            device = self._devices.get(esp_id)
            if device:
                device.touch()
