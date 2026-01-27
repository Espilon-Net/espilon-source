"""Multilateration engine for BLE device positioning."""

import time
import re
from typing import Optional
import numpy as np
from scipy.optimize import minimize


class MultilaterationEngine:
    """
    Calculates target position from multiple BLE scanner RSSI readings.

    Uses the log-distance path loss model to convert RSSI to distance,
    then weighted least squares optimization for position estimation.
    """

    def __init__(self, rssi_at_1m: float = -40, path_loss_n: float = 2.5, smoothing_window: int = 5):
        """
        Initialize the trilateration engine.

        Args:
            rssi_at_1m: RSSI value at 1 meter distance (calibration, typically -40 to -50)
            path_loss_n: Path loss exponent (2.0 free space, 2.5-3.5 indoors)
            smoothing_window: Number of readings to average for noise reduction
        """
        self.rssi_at_1m = rssi_at_1m
        self.path_loss_n = path_loss_n
        self.smoothing_window = smoothing_window

        # Scanner data: {scanner_id: {"position": (x, y), "rssi_history": [], "last_seen": timestamp}}
        self.scanners: dict = {}

        # Last calculated target position
        self._last_target: Optional[dict] = None
        self._last_calculation: float = 0

    def parse_data(self, raw_data: str) -> int:
        """
        Parse raw trilateration data from ESP32.

        Format: ESP_ID;(x,y);rssi\n
        Example: ESP3;(10.0,0.0);-45

        Args:
            raw_data: Raw text data with one or more readings

        Returns:
            Number of readings successfully processed
        """
        pattern = re.compile(r'^(\w+);\(([0-9.+-]+),([0-9.+-]+)\);(-?\d+)$')
        count = 0
        timestamp = time.time()

        for line in raw_data.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                scanner_id = match.group(1)
                x = float(match.group(2))
                y = float(match.group(3))
                rssi = int(match.group(4))

                self.add_reading(scanner_id, x, y, rssi, timestamp)
                count += 1

        return count

    def add_reading(self, scanner_id: str, x: float, y: float, rssi: int, timestamp: float = None):
        """
        Add a new RSSI reading from a scanner.

        Args:
            scanner_id: Unique identifier for the scanner (e.g., "ESP1")
            x: X coordinate of the scanner
            y: Y coordinate of the scanner
            rssi: RSSI value (negative dBm)
            timestamp: Reading timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        if scanner_id not in self.scanners:
            self.scanners[scanner_id] = {
                "position": (x, y),
                "rssi_history": [],
                "last_seen": timestamp
            }

        scanner = self.scanners[scanner_id]
        scanner["position"] = (x, y)
        scanner["rssi_history"].append(rssi)
        scanner["last_seen"] = timestamp

        # Keep only recent readings for smoothing
        if len(scanner["rssi_history"]) > self.smoothing_window:
            scanner["rssi_history"] = scanner["rssi_history"][-self.smoothing_window:]

    def rssi_to_distance(self, rssi: float) -> float:
        """
        Convert RSSI to estimated distance using log-distance path loss model.

        d = 10^((RSSI_1m - RSSI) / (10 * n))

        Args:
            rssi: RSSI value (negative dBm)

        Returns:
            Estimated distance in meters
        """
        return 10 ** ((self.rssi_at_1m - rssi) / (10 * self.path_loss_n))

    def calculate_position(self) -> dict:
        """
        Calculate target position using trilateration.

        Requires at least 3 active scanners with recent readings.
        Uses weighted least squares optimization.

        Returns:
            dict with position, confidence, and scanner info, or error
        """
        # Get active scanners (those with readings)
        active_scanners = [
            (sid, s) for sid, s in self.scanners.items()
            if s["rssi_history"]
        ]

        if len(active_scanners) < 3:
            return {
                "error": f"Need at least 3 active scanners (have {len(active_scanners)})",
                "scanners_count": len(active_scanners)
            }

        # Prepare data arrays
        positions = []
        distances = []
        weights = []

        for scanner_id, scanner in active_scanners:
            x, y = scanner["position"]

            # Average RSSI for noise reduction
            avg_rssi = sum(scanner["rssi_history"]) / len(scanner["rssi_history"])
            distance = self.rssi_to_distance(avg_rssi)

            positions.append([x, y])
            distances.append(distance)

            # Weight by signal strength (stronger signal = more reliable)
            # Using inverse square of absolute RSSI
            weights.append(1.0 / (abs(avg_rssi) ** 2))

        positions = np.array(positions)
        distances = np.array(distances)
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize weights

        # Cost function: weighted sum of squared distance errors
        def cost_function(point):
            x, y = point
            estimated_distances = np.sqrt((positions[:, 0] - x)**2 + (positions[:, 1] - y)**2)
            errors = (estimated_distances - distances) ** 2
            return np.sum(weights * errors)

        # Initial guess: weighted centroid of scanner positions
        x0 = np.sum(weights * positions[:, 0])
        y0 = np.sum(weights * positions[:, 1])

        # Optimize
        result = minimize(cost_function, [x0, y0], method='L-BFGS-B')

        if result.success:
            target_x, target_y = result.x
            # Confidence: inverse of residual error (higher cost = lower confidence)
            confidence = 1.0 / (1.0 + result.fun)

            self._last_target = {
                "x": round(float(target_x), 2),
                "y": round(float(target_y), 2)
            }
            self._last_calculation = time.time()

            return {
                "position": self._last_target,
                "confidence": round(float(confidence), 3),
                "scanners_used": len(active_scanners),
                "calculated_at": self._last_calculation
            }
        else:
            return {
                "error": "Optimization failed",
                "details": result.message
            }

    def get_state(self) -> dict:
        """
        Get the current state of the trilateration system.

        Returns:
            dict with scanner info and last target position
        """
        now = time.time()
        scanners_data = []

        for scanner_id, scanner in self.scanners.items():
            avg_rssi = None
            distance = None

            if scanner["rssi_history"]:
                avg_rssi = sum(scanner["rssi_history"]) / len(scanner["rssi_history"])
                distance = round(self.rssi_to_distance(avg_rssi), 2)
                avg_rssi = round(avg_rssi, 1)

            scanners_data.append({
                "id": scanner_id,
                "position": {"x": scanner["position"][0], "y": scanner["position"][1]},
                "last_rssi": avg_rssi,
                "estimated_distance": distance,
                "last_seen": scanner["last_seen"],
                "age_seconds": round(now - scanner["last_seen"], 1)
            })

        result = {
            "scanners": scanners_data,
            "scanners_count": len(scanners_data),
            "target": None,
            "config": {
                "rssi_at_1m": self.rssi_at_1m,
                "path_loss_n": self.path_loss_n,
                "smoothing_window": self.smoothing_window
            }
        }

        # Add target if available
        if self._last_target and (now - self._last_calculation) < 60:
            result["target"] = {
                "position": self._last_target,
                "calculated_at": self._last_calculation,
                "age_seconds": round(now - self._last_calculation, 1)
            }

        return result

    def update_config(self, rssi_at_1m: float = None, path_loss_n: float = None, smoothing_window: int = None):
        """
        Update trilateration configuration parameters.

        Args:
            rssi_at_1m: New RSSI at 1m value
            path_loss_n: New path loss exponent
            smoothing_window: New smoothing window size
        """
        if rssi_at_1m is not None:
            self.rssi_at_1m = rssi_at_1m
        if path_loss_n is not None:
            self.path_loss_n = path_loss_n
        if smoothing_window is not None:
            self.smoothing_window = max(1, smoothing_window)

    def clear(self):
        """Clear all scanner data and reset state."""
        self.scanners.clear()
        self._last_target = None
        self._last_calculation = 0
