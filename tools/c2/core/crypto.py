import base64
from Crypto.Cipher import ChaCha20

KEY = b"testde32chars0000000000000000000"
NONCE = b"noncenonceno"


class CryptoContext:
    def __init__(self, key: bytes = KEY, nonce: bytes = NONCE):
        self.key = key
        self.nonce = nonce

    # =========================
    # ChaCha20
    # =========================
    def encrypt(self, data: bytes) -> bytes:
        cipher = ChaCha20.new(key=self.key, nonce=self.nonce)
        return cipher.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        cipher = ChaCha20.new(key=self.key, nonce=self.nonce)
        return cipher.decrypt(data)

    # =========================
    # Base64
    # =========================
    def b64_encode(self, data: bytes) -> bytes:
        return base64.b64encode(data)

    def b64_decode(self, data: bytes) -> bytes:
        return base64.b64decode(data)
