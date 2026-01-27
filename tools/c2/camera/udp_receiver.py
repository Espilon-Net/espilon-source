"""UDP server for receiving camera frames from ESP devices.

Protocol from ESP32:
- TOKEN + "START" -> Start of new frame
- TOKEN + chunk    -> JPEG data chunk
- TOKEN + "END"   -> End of frame, decode and process
"""

import os
import socket
import threading
import time
import cv2
import numpy as np
from typing import Optional, Callable, Dict

from .config import (
    UDP_HOST, UDP_PORT, UDP_BUFFER_SIZE,
    SECRET_TOKEN, IMAGE_DIR,
    VIDEO_ENABLED, VIDEO_PATH, VIDEO_FPS, VIDEO_CODEC
)


class FrameAssembler:
    """Assembles JPEG frames from multiple UDP packets."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.buffer = bytearray()
        self.start_time: Optional[float] = None
        self.receiving = False

    def start_frame(self):
        """Start receiving a new frame."""
        self.buffer = bytearray()
        self.start_time = time.time()
        self.receiving = True

    def add_chunk(self, data: bytes) -> bool:
        """Add a chunk to the frame buffer. Returns False if timed out."""
        if not self.receiving:
            return False
        if self.start_time and (time.time() - self.start_time) > self.timeout:
            self.reset()
            return False
        self.buffer.extend(data)
        return True

    def finish_frame(self) -> Optional[bytes]:
        """Finish frame assembly and return complete data."""
        if not self.receiving or len(self.buffer) == 0:
            return None
        data = bytes(self.buffer)
        self.reset()
        return data

    def reset(self):
        """Reset the assembler state."""
        self.buffer = bytearray()
        self.start_time = None
        self.receiving = False


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

        # Frame assemblers per source address
        self._assemblers: Dict[str, FrameAssembler] = {}

        # Video recording
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._video_size: Optional[tuple] = None

        # Statistics
        self.frames_received = 0
        self.invalid_tokens = 0
        self.decode_errors = 0
        self.packets_received = 0

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
        self._assemblers.clear()
        self.frames_received = 0
        self.packets_received = 0

    def _cleanup_frames(self):
        """Remove all .jpg files from image directory."""
        try:
            for f in os.listdir(self.image_dir):
                if f.endswith(".jpg"):
                    os.remove(os.path.join(self.image_dir, f))
        except Exception:
            pass

    def _get_assembler(self, addr: tuple) -> FrameAssembler:
        """Get or create a frame assembler for the given address."""
        key = f"{addr[0]}:{addr[1]}"
        if key not in self._assemblers:
            self._assemblers[key] = FrameAssembler()
        return self._assemblers[key]

    def _receive_loop(self):
        """Main UDP receive loop with START/END protocol handling."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(1.0)

        print(f"[UDP] Receiver started on {self.host}:{self.port}")

        while not self._stop_event.is_set():
            try:
                data, addr = self._sock.recvfrom(UDP_BUFFER_SIZE)
            except socket.timeout:
                continue
            except OSError:
                break

            self.packets_received += 1

            # Validate token
            if not data.startswith(SECRET_TOKEN):
                self.invalid_tokens += 1
                continue

            # Remove token prefix
            payload = data[len(SECRET_TOKEN):]
            assembler = self._get_assembler(addr)
            camera_id = f"{addr[0]}_{addr[1]}"

            # Handle protocol markers
            if payload == b"START":
                assembler.start_frame()
                continue
            elif payload == b"END":
                frame_data = assembler.finish_frame()
                if frame_data:
                    self._process_complete_frame(camera_id, frame_data, addr)
                continue
            else:
                # Regular data chunk
                if not assembler.receiving:
                    # No START received, try as single-packet frame (legacy)
                    frame = self._decode_frame(payload)
                    if frame is not None:
                        self._process_frame(camera_id, frame, addr)
                    else:
                        self.decode_errors += 1
                else:
                    assembler.add_chunk(payload)

        # Cleanup
        if self._sock:
            self._sock.close()
            self._sock = None

        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None

        print("[UDP] Receiver stopped")

    def _process_complete_frame(self, camera_id: str, frame_data: bytes, addr: tuple):
        """Process a fully assembled frame."""
        frame = self._decode_frame(frame_data)
        if frame is None:
            self.decode_errors += 1
            return
        self._process_frame(camera_id, frame, addr)

    def _process_frame(self, camera_id: str, frame: np.ndarray, addr: tuple):
        """Process a decoded frame."""
        self.frames_received += 1
        self._active_cameras[camera_id] = time.time()

        # Save frame
        self._save_frame(camera_id, frame)

        # Record video if enabled
        if VIDEO_ENABLED:
            self._record_frame(frame)

        # Callback
        if self.on_frame:
            self.on_frame(camera_id, frame, addr)

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
            "packets_received": self.packets_received,
            "frames_received": self.frames_received,
            "invalid_tokens": self.invalid_tokens,
            "decode_errors": self.decode_errors,
            "active_cameras": len(self._active_cameras)
        }
