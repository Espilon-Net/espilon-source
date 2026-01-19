"""Flask web server for camera stream display."""

import os
import logging
import threading
from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, jsonify
from werkzeug.serving import make_server

from .config import (
    WEB_HOST, WEB_PORT, FLASK_SECRET_KEY,
    DEFAULT_USERNAME, DEFAULT_PASSWORD, IMAGE_DIR
)

# Disable Flask/Werkzeug request logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


class WebServer:
    """Flask-based web server for viewing camera streams."""

    def __init__(self,
                 host: str = WEB_HOST,
                 port: int = WEB_PORT,
                 image_dir: str = IMAGE_DIR,
                 username: str = DEFAULT_USERNAME,
                 password: str = DEFAULT_PASSWORD):
        self.host = host
        self.port = port
        self.image_dir = image_dir
        self.username = username
        self.password = password

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
        app.secret_key = FLASK_SECRET_KEY

        # Store reference to self for route handlers
        web_server = self

        @app.route("/login", methods=["GET", "POST"])
        def login():
            error = None
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
                if username == web_server.username and password == web_server.password:
                    session["logged_in"] = True
                    return redirect(url_for("index"))
                else:
                    error = "Invalid credentials."
            return render_template("login.html", error=error)

        @app.route("/logout")
        def logout():
            session.pop("logged_in", None)
            return redirect(url_for("login"))

        @app.route("/")
        def index():
            if not session.get("logged_in"):
                return redirect(url_for("login"))

            # List available camera images
            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            try:
                image_files = sorted([
                    f for f in os.listdir(full_image_dir)
                    if f.endswith(".jpg")
                ])
            except FileNotFoundError:
                image_files = []

            if not image_files:
                image_files = []

            return render_template("index.html", image_files=image_files)

        @app.route("/streams/<filename>")
        def stream_image(filename):
            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            return send_from_directory(full_image_dir, filename)

        @app.route("/api/cameras")
        def api_cameras():
            """API endpoint to get list of active cameras."""
            if not session.get("logged_in"):
                return jsonify({"error": "Unauthorized"}), 401

            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            try:
                cameras = [
                    f.replace(".jpg", "")
                    for f in os.listdir(full_image_dir)
                    if f.endswith(".jpg")
                ]
            except FileNotFoundError:
                cameras = []

            return jsonify({"cameras": cameras})

        @app.route("/api/stats")
        def api_stats():
            """API endpoint for server statistics."""
            if not session.get("logged_in"):
                return jsonify({"error": "Unauthorized"}), 401

            full_image_dir = os.path.join(c2_root, web_server.image_dir)
            try:
                camera_count = len([
                    f for f in os.listdir(full_image_dir)
                    if f.endswith(".jpg")
                ])
            except FileNotFoundError:
                camera_count = 0

            return jsonify({
                "active_cameras": camera_count,
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
