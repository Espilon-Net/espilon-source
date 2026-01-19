"""UDP server for receiving camera frames from ESP devices."""

import os
import socket
import threading
import cv2
import numpy as np
from typing import Optional, Callable

from .config import (
    UDP_HOST, UDP_PORT, UDP_BUFFER_SIZE,
    SECRET_TOKEN, IMAGE_DIR,
    VIDEO_ENABLED, VIDEO_PATH, VIDEO_FPS, VIDEO_CODEC
)


class UDPReceiver:
    """Receives JPEG frames via UDP from ESP camera devices."""

    def __init__(self,
                 host: str = UDP_HOST,
                 port: int = UDP_PORT,
                 image_dir: str = IMAGE_DIR,
                 on_frame: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.image_dir = image_dir
        self.on_frame = on_frame  # Callback when frame received

        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Video recording
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._video_size: Optional[tuple] = None

        # Statistics
        self.frames_received = 0
        self.invalid_tokens = 0
        self.decode_errors = 0

        # Active cameras tracking
        self._active_cameras: dict = {}  # {camera_id: last_frame_time}

        os.makedirs(self.image_dir, exist_ok=True)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def active_cameras(self) -> list:
        """Returns list of active camera identifiers."""
        return list(self._active_cameras.keys())

    def start(self) -> bool:
        """Start the UDP receiver thread."""
        if self.is_running:
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop the UDP receiver and cleanup."""
        self._stop_event.set()

        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None

        # Clean up frame files
        self._cleanup_frames()

        self._active_cameras.clear()
        self.frames_received = 0

    def _cleanup_frames(self):
        """Remove all .jpg files from image directory."""
        try:
            for f in os.listdir(self.image_dir):
                if f.endswith(".jpg"):
                    os.remove(os.path.join(self.image_dir, f))
        except Exception:
            pass

    def _receive_loop(self):
        """Main UDP receive loop."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(1.0)

        while not self._stop_event.is_set():
            try:
                data, addr = self._sock.recvfrom(UDP_BUFFER_SIZE)
            except socket.timeout:
                continue
            except OSError:
                break

            # Validate token
            if not data.startswith(SECRET_TOKEN):
                self.invalid_tokens += 1
                continue

            # Remove token prefix
            frame_data = data[len(SECRET_TOKEN):]

            # Decode JPEG
            frame = self._decode_frame(frame_data)
            if frame is None:
                self.decode_errors += 1
                continue

            self.frames_received += 1
            camera_id = f"{addr[0]}_{addr[1]}"
            self._active_cameras[camera_id] = True

            # Save frame
            self._save_frame(camera_id, frame)

            # Record video if enabled
            if VIDEO_ENABLED:
                self._record_frame(frame)

            # Callback
            if self.on_frame:
                self.on_frame(camera_id, frame, addr)

        # Cleanup
        if self._sock:
            self._sock.close()
            self._sock = None

        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None

    def _decode_frame(self, data: bytes) -> Optional[np.ndarray]:
        """Decode JPEG data to OpenCV frame."""
        try:
            npdata = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None

    def _save_frame(self, camera_id: str, frame: np.ndarray):
        """Save frame as JPEG file."""
        try:
            filepath = os.path.join(self.image_dir, f"{camera_id}.jpg")
            cv2.imwrite(filepath, frame)
        except Exception:
            pass

    def _record_frame(self, frame: np.ndarray):
        """Record frame to video file."""
        if self._video_writer is None:
            self._video_size = (frame.shape[1], frame.shape[0])
            fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
            video_path = os.path.join(os.path.dirname(self.image_dir), VIDEO_PATH.split('/')[-1])
            self._video_writer = cv2.VideoWriter(
                video_path, fourcc, VIDEO_FPS, self._video_size
            )

        if self._video_writer and self._video_writer.isOpened():
            self._video_writer.write(frame)

    def get_stats(self) -> dict:
        """Return receiver statistics."""
        return {
            "running": self.is_running,
            "frames_received": self.frames_received,
            "invalid_tokens": self.invalid_tokens,
            "decode_errors": self.decode_errors,
            "active_cameras": len(self._active_cameras)
        }
