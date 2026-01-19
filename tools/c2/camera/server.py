"""Main camera server combining UDP receiver and web server."""

from typing import Optional, Callable

from .config import UDP_HOST, UDP_PORT, WEB_HOST, WEB_PORT, IMAGE_DIR, DEFAULT_USERNAME, DEFAULT_PASSWORD
from .udp_receiver import UDPReceiver
from .web_server import WebServer


class CameraServer:
    """
    Combined camera server that manages both:
    - UDP receiver for incoming camera frames from ESP devices
    - Web server for viewing the camera streams
    """

    def __init__(self,
                 udp_host: str = UDP_HOST,
                 udp_port: int = UDP_PORT,
                 web_host: str = WEB_HOST,
                 web_port: int = WEB_PORT,
                 image_dir: str = IMAGE_DIR,
                 username: str = DEFAULT_USERNAME,
                 password: str = DEFAULT_PASSWORD,
                 on_frame: Optional[Callable] = None):
        """
        Initialize the camera server.

        Args:
            udp_host: Host to bind UDP receiver
            udp_port: Port for UDP receiver
            web_host: Host to bind web server
            web_port: Port for web server
            image_dir: Directory to store camera frames
            username: Web interface username
            password: Web interface password
            on_frame: Optional callback when frame is received (camera_id, frame, addr)
        """
        self.udp_receiver = UDPReceiver(
            host=udp_host,
            port=udp_port,
            image_dir=image_dir,
            on_frame=on_frame
        )

        self.web_server = WebServer(
            host=web_host,
            port=web_port,
            image_dir=image_dir,
            username=username,
            password=password
        )

    @property
    def is_running(self) -> bool:
        """Check if both servers are running."""
        return self.udp_receiver.is_running and self.web_server.is_running

    @property
    def udp_running(self) -> bool:
        return self.udp_receiver.is_running

    @property
    def web_running(self) -> bool:
        return self.web_server.is_running

    def start(self) -> dict:
        """
        Start both UDP receiver and web server.

        Returns:
            dict with status of each server
        """
        results = {
            "udp": {"started": False, "host": self.udp_receiver.host, "port": self.udp_receiver.port},
            "web": {"started": False, "host": self.web_server.host, "port": self.web_server.port}
        }

        if self.udp_receiver.start():
            results["udp"]["started"] = True

        if self.web_server.start():
            results["web"]["started"] = True
            results["web"]["url"] = self.web_server.get_url()

        return results

    def stop(self) -> dict:
        """
        Stop both servers.

        Returns:
            dict with stop status
        """
        self.udp_receiver.stop()
        self.web_server.stop()

        return {
            "udp": {"stopped": True},
            "web": {"stopped": True}
        }

    def get_status(self) -> dict:
        """Get status of both servers."""
        return {
            "udp": {
                "running": self.udp_receiver.is_running,
                "host": self.udp_receiver.host,
                "port": self.udp_receiver.port,
                **self.udp_receiver.get_stats()
            },
            "web": {
                "running": self.web_server.is_running,
                "host": self.web_server.host,
                "port": self.web_server.port,
                "url": self.web_server.get_url() if self.web_server.is_running else None
            }
        }

    def get_active_cameras(self) -> list:
        """Get list of active camera IDs."""
        return self.udp_receiver.active_cameras
