import os
import base64
from datetime import datetime
from utils.espilon_pb2 import ESPMessage
from utils.utils import _print_status
from core.chacha20 import crypt
from utils.cli import _color

_last_client = None

def process_esp_message(c2, client_address, message):
    """
    Traite un message base64 provenant de l’ESP :
    - Décode base64, déchiffre et parse en ESPMessage
    - Affiche les champs
    - Sauvegarde dans logs/<tag>/<id>.log avec timestamp
    """

    global _last_client
    try:
        # 1. Decode Base64
        decoded = base64.b64decode(message)

        # 2. Déchiffrement
        decrypted = crypt(decoded)

        # 3. Parse Protobuf
        msg = ESPMessage()
        msg.ParseFromString(decrypted)

        # 4. Traitement du champ log (bytes)
        log_str = ""
        if msg.log:
            try:
                log_str = msg.log.decode("utf-8")
            except UnicodeDecodeError:
                log_str = f"<{len(msg.log)} bytes non-text>"

        # 5. Identification
        tag = msg.tag or "untagged"
        client_id = msg.id or "unknown"
        message_text = msg.message or ""

        # 6. Affichage console
        if _last_client != (client_id, client_address):
            print(_color("CYAN") + f"\n🛰  Received from id: {client_id} | {client_address}" + _color("RESET"))
            _last_client = (client_id, client_address)
            
        print(f"  Tag     : {tag}")

        if log_str:
            print(f"  Message : {message_text}")
            print(f"  Log     : {log_str}\n")
        else:
            print(f"  Message : {message_text}\n")

        # 7. Dossier et chemin
        safe_tag = tag.replace("/", "_")
        log_dir = os.path.join("logs", safe_tag)
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f"{client_id}.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_file = not os.path.exists(log_path)

        # 8. Écriture dans le fichier
        with open(log_path, "a", encoding="utf-8") as f:
            if new_file:
                f.write(f"# Log file generated at {timestamp}\n")
            f.write(f"[{timestamp}]-[{client_address}] "
                    f"MESSAGE[ID : {client_id}] "
                    f"DATA=[{message_text}]"
                    f"{f' LOG=[{log_str}]' if log_str else ''}\n")

        return decrypted

    except Exception as e:
        print(f"\n{_color('RED')}[⚠] Error process_esp_message : {e}{_color('RESET')}")
        return None
