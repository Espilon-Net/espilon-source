#!/usr/bin/env python3
"""Simple UDP test server to debug camera streaming."""

import socket
import sys

HOST = "0.0.0.0"
PORT = 5000
TOKEN = b"Sup3rS3cretT0k3n"

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, port))

    print(f"[UDP] Listening on {HOST}:{port}")
    print(f"[UDP] Token: {TOKEN.decode()}")
    print("[UDP] Waiting for packets...\n")

    packet_count = 0
    frame_count = 0

    try:
        while True:
            data, addr = sock.recvfrom(65535)
            packet_count += 1

            # Check token
            if data.startswith(TOKEN):
                payload = data[len(TOKEN):]

                if payload == b"START":
                    print(f"[{addr[0]}:{addr[1]}] START (new frame)")
                elif payload == b"END":
                    frame_count += 1
                    print(f"[{addr[0]}:{addr[1]}] END (frame #{frame_count} complete)")
                else:
                    print(f"[{addr[0]}:{addr[1]}] CHUNK: {len(payload)} bytes")
            else:
                print(f"[{addr[0]}:{addr[1]}] INVALID TOKEN: {data[:20]}...")

            # Stats every 100 packets
            if packet_count % 100 == 0:
                print(f"\n--- Stats: {packet_count} packets, {frame_count} frames ---\n")

    except KeyboardInterrupt:
        print(f"\n[UDP] Stopped. Total: {packet_count} packets, {frame_count} frames")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
