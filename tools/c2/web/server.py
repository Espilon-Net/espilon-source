"""Unified Flask web server for ESPILON C2 dashboard."""

import os
import logging
import threading
import time
from functools import wraps
from typing import Optional

from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, jsonify
from werkzeug.serving import make_server

from .multilateration import MultilaterationEngine

# Disable Flask/Werkzeug request logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


class UnifiedWebServer:
    """
    Unified Flask-based web server for ESPILON C2.

    Provides:
    - Dashboard: View connected ESP32 devices
    - Cameras: View live camera streams
    - Trilateration: Visualize BLE device positioning
    """

    def __init__(self,
                 host: str = "0.0.0.0",
                 port: int = 8000,
                 image_dir: str = "static/streams",
                 username: str = "admin",
                 password: str = "admin",
                 secret_key: str = "change_this_for_prod",
                 multilat_token: str = "multilat_secret_token",
                 device_registry=None,
                 multilateration_engine: Optional[MultilaterationEngine] = None):
        """
        Initialize the unified web server.

        Args:
            host: Host to bind the server
            port: Port for the web server
            image_dir: Directory containing camera frame images
            username: Login username
            password: Login password
            secret_key: Flask session secret key
            multilat_token: Bearer token for multilateration API
            device_registry: DeviceRegistry instance for device listing
            multilateration_engine: MultilaterationEngine instance (created if None)
        """
        self.host = host
        self.port = port
        self.image_dir = image_dir
        self.username = username
        self.password = password
        self.secret_key = secret_key
        self.multilat_token = multilat_token
        self.device_registry = device_registry
        self.multilat = multilateration_engine or MultilaterationEngine()

        self._app = self._create_app()
        self._server = None
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _create_app(self) -> Flask:
        """Create and configure the Flask application."""
        # Get the c2 root directory for templates
        c2_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_dir = os.path.join(c2_root, "templates")
        static_dir = os.path.join(c2_root, "static")

        app = Flask(__name__,
                    template_folder=template_dir,
                    static_folder=static_dir)
        app.secret_key = self.secret_key

        # Store reference to self for route handlers
        web_server = self

        # ========== Auth Decorators ==========

        def require_login(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if not session.get("logged_in"):
                    return redirect(url_for("login"))
                return f(*args, **kwargs)
            return decorated

        def require_api_auth(f):
            """Require session login OR Bearer token for API endpoints."""
            @wraps(f)
            def decorated(*args, **kwargs):
                # Check session
                if session.get("logged_in"):
                    return f(*args, **kwargs)

                # Check Bearer token
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    if token == web_server.multilat_token:
                        return f(*args, **kwargs)

                return jsonify({"error": "Unauthorized"}), 401
            return decorated

        # ========== Auth Routes ==========

        @app.route("/login", methods=["GET", "POST"])
        def login():
            error = None
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
                if username == web_server.username and password == web_server.password:
                    session["logged_in"] = True
                    return redirect(url_for("dashboard"))
                else:
                    error = "Invalid credentials."
            return render_template("login.html", error=error)

        @app.route("/logout")
        def logout():
            session.pop("logged_in", None)
            return redirect(url_for("login"))

        # ========== Page Routes ==========

        @app.route("/")
        @require_login
        def index():
            return redirect(url_for("dashboard"))

        @app.route("/dashboard")
        @require_login
        def dashboard():
            return render_template("dashboard.html", active_page="dashboard")

        @app.route("/cameras")
        @require_login
        def cameras():
            # List available camera images
            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            try:
                image_files = sorted([
                    f for f in os.listdir(full_image_dir)
                    if f.endswith(".jpg")
                ])
            except FileNotFoundError:
                image_files = []

            return render_template("cameras.html", active_page="cameras", image_files=image_files)

        @app.route("/multilateration")
        @require_login
        def multilateration():
            return render_template("multilateration.html", active_page="multilateration")

        # ========== Static Files ==========

        @app.route("/streams/<filename>")
        @require_login
        def stream_image(filename):
            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            return send_from_directory(full_image_dir, filename)

        # ========== Device API ==========

        @app.route("/api/devices")
        @require_api_auth
        def api_devices():
            """Get list of connected devices."""
            if web_server.device_registry is None:
                return jsonify({"error": "Device registry not available", "devices": []})

            now = time.time()
            devices = []

            for d in web_server.device_registry.all():
                devices.append({
                    "id": d.id,
                    "ip": d.address[0] if d.address else "unknown",
                    "port": d.address[1] if d.address else 0,
                    "status": d.status,
                    "connected_at": d.connected_at,
                    "last_seen": d.last_seen,
                    "connected_for_seconds": round(now - d.connected_at, 1),
                    "last_seen_ago_seconds": round(now - d.last_seen, 1)
                })

            return jsonify({
                "devices": devices,
                "count": len(devices)
            })

        # ========== Camera API ==========

        @app.route("/api/cameras")
        @require_api_auth
        def api_cameras():
            """Get list of active cameras."""
            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            try:
                cameras = [
                    f.replace(".jpg", "")
                    for f in os.listdir(full_image_dir)
                    if f.endswith(".jpg")
                ]
            except FileNotFoundError:
                cameras = []

            return jsonify({"cameras": cameras, "count": len(cameras)})

        # ========== Trilateration API ==========

        @app.route("/api/multilat/collect", methods=["POST"])
        @require_api_auth
        def api_multilat_collect():
            """
            Receive multilateration data from ESP32 scanners.

            Expected format (text/plain):
            ESP_ID;(x,y);rssi
            ESP3;(10.0,0.0);-45
            """
            raw_data = request.get_data(as_text=True)
            count = web_server.multilat.parse_data(raw_data)

            # Recalculate position after new data
            if count > 0:
                web_server.multilat.calculate_position()

            return jsonify({
                "status": "ok",
                "readings_processed": count
            })

        @app.route("/api/multilat/state")
        @require_api_auth
        def api_multilat_state():
            """Get current multilateration state (scanners + target)."""
            state = web_server.multilat.get_state()

            # Include latest calculation if not present
            if state["target"] is None and state["scanners_count"] >= 3:
                result = web_server.multilat.calculate_position()
                if "position" in result:
                    state["target"] = {
                        "position": result["position"],
                        "confidence": result.get("confidence", 0),
                        "calculated_at": result.get("calculated_at", time.time()),
                        "age_seconds": 0
                    }

            return jsonify(state)

        @app.route("/api/multilat/config", methods=["GET", "POST"])
        @require_api_auth
        def api_multilat_config():
            """Get or update multilateration configuration."""
            if request.method == "POST":
                data = request.get_json() or {}
                web_server.multilat.update_config(
                    rssi_at_1m=data.get("rssi_at_1m"),
                    path_loss_n=data.get("path_loss_n"),
                    smoothing_window=data.get("smoothing_window")
                )

            return jsonify({
                "rssi_at_1m": web_server.multilat.rssi_at_1m,
                "path_loss_n": web_server.multilat.path_loss_n,
                "smoothing_window": web_server.multilat.smoothing_window
            })

        @app.route("/api/multilat/clear", methods=["POST"])
        @require_api_auth
        def api_multilat_clear():
            """Clear all multilateration data."""
            web_server.multilat.clear()
            return jsonify({"status": "ok"})

        # ========== Stats API ==========

        @app.route("/api/stats")
        @require_api_auth
        def api_stats():
            """Get overall server statistics."""
            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            try:
                camera_count = len([
                    f for f in os.listdir(full_image_dir)
                    if f.endswith(".jpg")
                ])
            except FileNotFoundError:
                camera_count = 0

            device_count = 0
            if web_server.device_registry:
                device_count = len(list(web_server.device_registry.all()))

            multilat_state = web_server.multilat.get_state()

            return jsonify({
                "active_cameras": camera_count,
                "connected_devices": device_count,
                "multilateration_scanners": multilat_state["scanners_count"],
                "server_running": True
            })

        return app

    def start(self) -> bool:
        """Start the web server in a background thread."""
        if self.is_running:
            return False

        self._server = make_server(self.host, self.port, self._app, threaded=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop the web server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        self._thread = None

    def get_url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"
