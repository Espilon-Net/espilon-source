import secrets
import hashlib

def generate_random_endpoint():
    endpoint = f"/stream_{secrets.token_hex(4)}"
    print(f"[+] Endpoint généré : {endpoint}")
    return endpoint

def generate_token():
    raw = secrets.token_bytes(8)
    hashed = hashlib.sha256(raw).hexdigest()
    print(f"[+] Bearer Token généré : {hashed}")
    return hashed
