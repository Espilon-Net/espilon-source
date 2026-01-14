import os
import cv2
import numpy as np
import threading
import socket
# from flask import Flask, render_template, send_from_directory
from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, jsonify
from collections import deque

TX_POWER = -40
ENV_FACTOR = 2
WINDOW_SIZE = 5

esp_data = {}
latest_observations = {}
esp_positions = {}
position_history = deque(maxlen=WINDOW_SIZE)
trilat_points = []


# === CONFIG ===
UDP_IP = "0.0.0.0"
UDP_PORT = 5000
BUFFER_SIZE = 65535
IMAGE_DIR = "static/streams"

# === FLASK SECRET KEY ===
SECRET_KEY = "change_this_for_prod"
SECRET_TOKEN = b"Sup3rS3cretT0k3n"
app = Flask(__name__)
app.secret_key = SECRET_KEY


# === CRÉATION DES DOSSIERS ===
os.makedirs(IMAGE_DIR, exist_ok=True)

udp_thread = None
flask_thread = None
udp_sock = None
flask_server = None
stop_udp_event = threading.Event()

VIDEO_PATH = "static/streams/record.avi"
video_writer = None
video_writer_fps = 10  # images/seconde
video_writer_size = None


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin":
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Identifiants invalides."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    # Liste les images disponibles
    image_files = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])
    if not image_files:
        image_files = ["waiting_for_camera"]
    return render_template("index.html", image_files=image_files)

@app.route("/streams/<filename>")
def stream_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

from flask import request, jsonify

@app.route("/api/trilateration", methods=["POST"])
def trilateration_api():
    # Accepte du texte brut : Content-Type: text/plain
    if request.content_type == "text/plain":
        raw_data = request.data.decode("utf-8").strip()
        print(f"[RAW POST] {raw_data}")
        handle_trilateration_data(raw_data)
        return jsonify({"status": "OK"})
    
    # Sinon : rejet explicite
    return "Unsupported Media Type", 415


@app.route("/trilateration")
def trilateration_view():
    point = get_latest_position()
    return render_template("trilateration.html", point=point, anchors=esp_positions)




# === UDP Server pour recevoir les flux ===
def udp_receiver():
    global udp_sock, video_writer, video_writer_size
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((UDP_IP, UDP_PORT))
    print(f"[UDP] En écoute sur {UDP_IP}:{UDP_PORT}")

    while not stop_udp_event.is_set():
        try:
            udp_sock.settimeout(1.0)
            try:
                data, addr = udp_sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                continue

            # Vérifie le token
            if not data.startswith(SECRET_TOKEN):
                print(f"[SECURITE] Token invalide de {addr}")
                continue
            data = data[len(SECRET_TOKEN):]  # Retire le token

            npdata = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)

            if frame is not None:
                print(f"[DEBUG] Frame shape: {frame.shape}")
                filename = f"{addr[0]}_{addr[1]}.jpg"
                filepath = os.path.join(IMAGE_DIR, filename)
                cv2.imwrite(filepath, frame)

                # --- Ajout pour l'enregistrement vidéo ---
                if video_writer is None:
                    video_writer_size = (frame.shape[1], frame.shape[0])
                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                    video_writer = cv2.VideoWriter(VIDEO_PATH, fourcc, video_writer_fps, video_writer_size)
                    if not video_writer.isOpened():
                        print("[ERREUR] VideoWriter n'a pas pu être ouvert !")

                if video_writer is not None:
                    video_writer.write(frame)
                    
        except Exception as e:
            print(f"[ERREUR] {e}")
    if video_writer is not None:
        video_writer.release()
        video_writer = None
    udp_sock.close()
    udp_sock = None
    
def rssi_to_distance(rssi):
    return 10 ** ((TX_POWER - rssi) / (10 * ENV_FACTOR))

def trilaterate(p1, r1, p2, r2, p3, r3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    A = 2 * (x2 - x1)
    B = 2 * (y2 - y1)
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2

    D = 2 * (x3 - x2)
    E = 2 * (y3 - y2)
    F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2

    denominator = A * E - B * D
    if denominator == 0:
        raise Exception("Trilatération impossible")

    x = (C * E - B * F) / denominator
    y = (A * F - C * D) / denominator

    return (x, y)


def handle_trilateration_data(text):
    global latest_observations, trilat_points, position_history, esp_positions

    try:
        esp_id, coord_str, rssi_str = text.split(";")
        x_str, y_str = coord_str.split(",")
        x, y = float(x_str), float(y_str)
        rssi = float(rssi_str)
        dist = rssi_to_distance(rssi)

        latest_observations[esp_id] = ((x, y), dist)
        esp_positions[esp_id] = (x, y, dist)  # ✅ essentiel pour affichage

        print(f"[OBS] Reçu de {esp_id} → pos=({x}, {y}), rssi={rssi}, dist={dist:.2f}")

        if len(latest_observations) >= 3:
            anchors = list(latest_observations.values())[:3]
            pos = trilaterate(*anchors[0], *anchors[1], *anchors[2])
            position_history.append(pos)

            avg_x = sum(p[0] for p in position_history) / len(position_history)
            avg_y = sum(p[1] for p in position_history) / len(position_history)
            trilat_points = [(avg_x, avg_y)]

            print(f"[TRILAT] Moyenne position : ({avg_x:.3f}, {avg_y:.3f})")
    except Exception as e:
        print(f"[ERREUR PARSING] {text} → {e}")


def get_latest_position():
    return trilat_points[-1] if trilat_points else None




def _run_flask():
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

def start_cam_server():
    global udp_thread, flask_thread, stop_udp_event
    if udp_thread and udp_thread.is_alive():
        print("[INFO] UDP server déjà démarré.")
    else:
        stop_udp_event.clear()
        udp_thread = threading.Thread(target=udp_receiver, daemon=True)
        udp_thread.start()
        print("[INFO] UDP server démarré.")

    if flask_thread and flask_thread.is_alive():
        print("[INFO] Flask server déjà démarré.")
    else:
        flask_thread = threading.Thread(target=_run_flask, daemon=True)
        flask_thread.start()
        print("[INFO] Flask server démarré sur http://0.0.0.0:8000.")


def stop_cam_server():
    global stop_udp_event, udp_sock, video_writer
    print("[INFO] Arrêt du serveur UDP...")
    stop_udp_event.set()
    if udp_sock:
        try:
            udp_sock.close()
        except Exception:
            pass
        udp_sock = None
    if video_writer is not None:
        video_writer.release()
        print("[DEBUG] VideoWriter released")
        video_writer = None
    print("[INFO] Serveur UDP arrêté.")

    # Suppression des fichiers .jpg
    for f in os.listdir(IMAGE_DIR):
        if f.endswith(".jpg"):
            try:
                os.remove(os.path.join(IMAGE_DIR, f))
            except Exception as e:
                print(f"[ERREUR] Impossible de supprimer {f}: {e}")

if __name__ == "__main__":
    start_cam_server()
    try:
        while True:
            pass  # Le serveur Flask et le thread UDP fonctionnent en arrière-plan
    except KeyboardInterrupt:
        stop_cam_server()
        print("[INFO] Serveur arrêté.")