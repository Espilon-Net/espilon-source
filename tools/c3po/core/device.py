from dataclasses import dataclass, field
import socket
import time


@dataclass
class Device:
    """
    Représente un ESP32 connecté au serveur
    """
    id: str
    sock: socket.socket
    address: tuple[str, int]

    connected_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def touch(self):
        """
        Met à jour la date de dernière activité
        """
        self.last_seen = time.time()

    def close(self):
        """
        Ferme proprement la connexion
        """
        try:
            self.sock.close()
        except Exception:
            pass
