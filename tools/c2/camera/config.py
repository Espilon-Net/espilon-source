"""Configuration loader for camera server module - reads from .env file."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from c2 root directory
C2_ROOT = Path(__file__).parent.parent
ENV_FILE = C2_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # Try .env.example as fallback for development
    example_env = C2_ROOT / ".env.example"
    if example_env.exists():
        load_dotenv(example_env)


def _get_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment."""
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


def _get_int(key: str, default: int) -> int:
    """Get integer value from environment."""
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return default


# C2 Server
C2_HOST = os.getenv("C2_HOST", "0.0.0.0")
C2_PORT = _get_int("C2_PORT", 2626)

# UDP Server configuration
UDP_HOST = os.getenv("UDP_HOST", "0.0.0.0")
UDP_PORT = _get_int("UDP_PORT", 5000)
UDP_BUFFER_SIZE = _get_int("UDP_BUFFER_SIZE", 65535)

# Flask Web Server configuration
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = _get_int("WEB_PORT", 8000)

# Security
SECRET_TOKEN = os.getenv("CAMERA_SECRET_TOKEN", "Sup3rS3cretT0k3n").encode()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change_this_for_prod")

# Credentials
DEFAULT_USERNAME = os.getenv("WEB_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("WEB_PASSWORD", "admin")

# Storage paths
IMAGE_DIR = os.getenv("IMAGE_DIR", "static/streams")

# Video recording
VIDEO_ENABLED = _get_bool("VIDEO_ENABLED", True)
VIDEO_PATH = os.getenv("VIDEO_PATH", "static/streams/record.avi")
VIDEO_FPS = _get_int("VIDEO_FPS", 10)
VIDEO_CODEC = os.getenv("VIDEO_CODEC", "MJPG")
