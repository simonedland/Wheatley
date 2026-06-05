"""Optional servo/LED hardware interface for Wheatley V2.

This is a simplified port of ``wheatley/hardware/arduino_interface.py``. The
hardware is OPTIONAL: by default the interface runs in dry-run mode and simply
logs the commands it would send, so the core voice loop never depends on a
physical robot being attached.

The big per-emotion animation table lives in the :data:`ANIMATIONS` constant at
the bottom of this module. Each emotion maps to the velocities, target factors,
idle ranges, intervals and LED color used to drive the ten servos.

Only the standard library and (lazily) :mod:`pyserial` are imported, so this
module imports cleanly even when pyserial is not installed.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Number of servos driven by the hardware.
SERVO_COUNT = 10

#: Static per-servo configuration ported from v1's ``ServoController``.
#: Each entry describes one servo's angle limits, used to turn a per-emotion
#: ``target_factor`` (0..1) into an absolute target angle.
SERVOS: list[dict[str, Any]] = [
    {"name": "lens", "min_angle": 0, "max_angle": 0},
    {"name": "eyelid1", "min_angle": 180, "max_angle": 220},
    {"name": "eyelid2", "min_angle": 140, "max_angle": 180},
    {"name": "eyeX", "min_angle": 130, "max_angle": 220},
    {"name": "eyeY", "min_angle": 140, "max_angle": 210},
    {"name": "handle1", "min_angle": -60, "max_angle": 60},
    {"name": "handle2", "min_angle": -60, "max_angle": 60},
    {"name": "eyeX2", "min_angle": 150, "max_angle": 180},
    {"name": "eyeY2", "min_angle": 130, "max_angle": 200},
    {"name": "eyeZ", "min_angle": 140, "max_angle": 220},
]

#: Brightness divisor applied to LED color channels (matches v1 behaviour).
_LED_BRIGHTNESS_DIVISOR = 5


class HardwareInterface:
    """Control the Arduino/M5Stack servos and status LED.

    When ``port == "dryrun"`` or ``dry_run`` is true, no serial port is opened
    and every command is logged instead of being written to hardware. A real
    :class:`serial.Serial` connection is only opened when a real port is given
    and ``dry_run`` is false; pyserial is imported lazily at that point.

    Attributes:
        port: The serial port name (or ``"dryrun"``).
        baud_rate: The serial baud rate.
        dry_run: Whether the interface is in dry-run (no hardware) mode.
    """

    def __init__(
        self,
        port: str = "dryrun",
        baud_rate: int = 115200,
        dry_run: bool = True,
    ) -> None:
        """Initialize the interface and (optionally) open the serial port.

        Args:
            port: Serial port name, e.g. ``"COM7"``. The special value
                ``"dryrun"`` forces dry-run mode.
            baud_rate: Serial baud rate.
            dry_run: When true (the default), no serial port is opened.
        """
        self.port = port
        self.baud_rate = baud_rate
        self.dry_run = dry_run or port == "dryrun"
        self._serial: Any = None

        if self.dry_run:
            logger.info(
                "[DRY RUN] HardwareInterface initialized (port=%s, baud=%s); "
                "no serial port opened.",
                port,
                baud_rate,
            )
            return

        # Lazy import so the module imports without pyserial installed.
        try:
            import serial  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("pyserial is not installed; falling back to dry-run mode.")
            self.dry_run = True
            return

        try:
            self._serial = serial.Serial(port, baud_rate, timeout=2)
            logger.info("Opened serial port %s at %s baud.", port, baud_rate)
        except Exception as exc:  # pragma: no cover - depends on real hardware
            logger.warning(
                "Could not open serial port %s: %s; falling back to dry-run.",
                port,
                exc,
            )
            self.dry_run = True
            self._serial = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def play_animation(self, emotion: str) -> None:
        """Apply the servo configuration and LED color for ``emotion``.

        Unknown emotions fall back to ``"neutral"`` so callers never have to
        validate input. The resulting servo config and LED command are sent
        over serial, or logged when in dry-run mode.

        Args:
            emotion: One of the keys in :data:`ANIMATIONS`.
        """
        if emotion not in ANIMATIONS:
            logger.warning("Emotion '%s' is not supported; using 'neutral'.", emotion)
            emotion = "neutral"

        params = ANIMATIONS[emotion]
        velocities = params["velocities"]
        target_factors = params["target_factors"]
        idle_ranges = params["idle_ranges"]
        intervals = params["intervals"]

        chunks: list[str] = []
        for i, servo in enumerate(SERVOS):
            target_angle = int(
                servo["min_angle"]
                + target_factors[i] * (servo["max_angle"] - servo["min_angle"])
            )
            chunks.append(
                f"{i},{target_angle},{velocities[i]},{idle_ranges[i]},{intervals[i]}"
            )
        servo_command = "SET_SERVO_CONFIG:" + ";".join(chunks) + "\n"
        self._send(servo_command)

        # Apply the emotion's LED color (scaled for brightness).
        self.set_led(tuple(params["color"]))  # type: ignore[arg-type]
        logger.info("Played animation for emotion '%s'.", emotion)

    def set_led(self, rgb: tuple[int, int, int]) -> None:
        """Set the status LED color.

        Channels are scaled down for brightness (matching v1) before being
        sent. In dry-run mode the command is only logged.

        Args:
            rgb: A ``(red, green, blue)`` tuple, each channel 0-255.
        """
        r, g, b = (int(c) // _LED_BRIGHTNESS_DIVISOR for c in rgb)
        self._send(f"SET_LED;R={r};G={g};B={b}\n")

    def close(self) -> None:
        """Close the serial connection if one is open."""
        if self._serial is not None:
            try:
                self._serial.close()
                logger.info("Closed serial port %s.", self.port)
            except Exception as exc:  # pragma: no cover - depends on hardware
                logger.warning("Error closing serial port: %s", exc)
            finally:
                self._serial = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _send(self, command: str) -> None:
        """Write ``command`` to the serial port, or log it in dry-run mode."""
        if self.dry_run or self._serial is None:
            logger.info("[DRY RUN] Would send: %s", command.strip())
            return
        self._serial.write(command.encode())
        logger.debug("Sent: %s", command.strip())


def dispatch(name: str, args: dict[str, Any], *, hw: HardwareInterface) -> str | None:
    """Dispatch a tool call owned by this unit.

    Args:
        name: The tool/function name being invoked.
        args: The decoded tool arguments.
        hw: The hardware interface to act on.

    Returns:
        A short confirmation string for owned tools, or ``None`` if ``name``
        is not handled by this unit.
    """
    if name == "set_animation":
        emotion = args["animation"]
        hw.play_animation(emotion)
        return f"Playing '{emotion}' animation."
    return None


# ----------------------------------------------------------------------
# Animation table
# ----------------------------------------------------------------------
# Each emotion maps to:
#   velocities      - per-servo movement speed
#   target_factors  - per-servo target position as a fraction (0..1) of range
#   idle_ranges     - per-servo idle wobble range
#   intervals       - per-servo animation interval (ms)
#   color           - [r, g, b] status LED color (pre-scaling)
# All per-servo lists have length SERVO_COUNT (10), one entry per SERVOS slot.
ANIMATIONS: dict[str, dict[str, Any]] = {
    "happy": {
        "velocities": [5, 2, 1, 2, 2, 5, 5, 1, 1, 1],
        "target_factors": [1.0, 0.075, 0.0, 0.489, 0.0, 0.0, 0.0, 0.8, 0.757, 0.475],
        "idle_ranges": [40, 2, 1, 30, 5, 10, 10, 10, 15, 10],
        "intervals": [1000, 1000, 2000, 1000, 1000, 2000, 2000, 1000, 1000, 4000],
        "color": [0, 255, 0],
    },
    "angry": {
        "velocities": [20, 10, 10, 10, 10, 5, 5, 20, 5, 1],
        "target_factors": [0.064, 0.25, 0.7, 0.489, 0.5, 0.0, 0.0, 0.867, 0.743, 0.487],
        "idle_ranges": [40, 2, 2, 5, 5, 10, 10, 2, 5, 10],
        "intervals": [2000, 2000, 2000, 5000, 2000, 2000, 2000, 4000, 4000, 4000],
        "color": [255, 0, 0],
    },
    "sad": {
        "velocities": [5, 1, 1, 1, 1, 5, 5, 1, 1, 1],
        "target_factors": [1.0, 1.0, 0.825, 0.489, 1.0, 0.0, 0.0, 0.867, 0.129, 0.5],
        "idle_ranges": [10, 10, 10, 40, 5, 10, 10, 10, 5, 20],
        "intervals": [2000, 2000, 2000, 5000, 2000, 2000, 2000, 4000, 4000, 4000],
        "color": [0, 0, 255],
    },
    "neutral": {
        "velocities": [2, 1, 1, 2, 2, 5, 5, 1, 1, 1],
        "target_factors": [0.504, 1.0, 0.0, 0.489, 0.5, 0.0, 0.0, 0.8, 0.771, 0.487],
        "idle_ranges": [300, 10, 10, 10, 5, 10, 10, 10, 15, 10],
        "intervals": [10000, 5000, 5000, 5000, 5000, 2000, 2000, 2000, 2000, 4000],
        "color": [255, 255, 255],
    },
    "excited": {
        "velocities": [5, 10, 10, 10, 10, 5, 5, 10, 2, 1],
        "target_factors": [0.497, 1.0, 0.0, 0.489, 0.429, 0.0, 0.0, 0.9, 0.7, 0.45],
        "idle_ranges": [10, 10, 10, 10, 10, 10, 10, 10, 10, 5],
        "intervals": [2000, 2000, 2000, 5000, 2000, 2000, 2000, 1000, 1000, 4000],
        "color": [255, 128, 0],
    },
    "confused": {
        "velocities": [5, 5, 5, 5, 5, 5, 5, 1, 2, 1],
        "target_factors": [0.5, 1.0, 0.0, 0.5, 0.5, 0.0, 0.0, 0.5, 0.829, 0.0],
        "idle_ranges": [400, 10, 10, 40, 35, 10, 10, 15, 10, 4],
        "intervals": [2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000],
        "color": [128, 255, 255],
    },
    "surprised": {
        "velocities": [20, 20, 20, 10, 10, 5, 5, 10, 2, 1],
        "target_factors": [1.0, 1.0, 0.0, 0.5, 0.5, 0.0, 0.0, 0.7, 1.0, 0.5],
        "idle_ranges": [10, 1, 1, 10, 10, 10, 10, 10, 10, 5],
        "intervals": [1000, 1000, 1000, 500, 500, 2000, 2000, 1000, 1000, 4000],
        "color": [255, 255, 0],
    },
    "curious": {
        "velocities": [10, 1, 1, 5, 1, 1, 1, 5, 1, 1],
        "target_factors": [0.0, 0.375, 0.25, 0.5, 0.0, 0.0, 0.0, 0.5, 0.843, 0.475],
        "idle_ranges": [100, 5, 5, 50, 10, 10, 10, 35, 2, 30],
        "intervals": [5000, 2000, 2000, 2000, 10400, 10500, 10600, 2000, 1000, 2000],
        "color": [255, 128, 0],
    },
    "bored": {
        "velocities": [5, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "target_factors": [0.0, 1.0, 0.825, 0.5, 0.0, 0.0, 0.0, 0.511, 0.5, 0.45],
        "idle_ranges": [100, 5, 5, 20, 10, 10, 10, 40, 30, 0],
        "intervals": [5000, 5000, 5000, 2000, 10400, 10500, 10600, 10000, 10000, 10000],
        "color": [128, 0, 255],
    },
    "fearful": {
        "velocities": [10, 3, 3, 10, 10, 1, 1, 5, 2, 1],
        "target_factors": [0.0, 1.0, 0.0, 0.5, 0.486, 0.0, 0.0, 0.5, 0.743, 0.512],
        "idle_ranges": [100, 2, 2, 40, 30, 10, 10, 35, 5, 20],
        "intervals": [1000, 1000, 1000, 1000, 1000, 10500, 10600, 2000, 2000, 5000],
        "color": [255, 0, 0],
    },
    "hopeful": {
        "velocities": [20, 1, 1, 10, 1, 1, 1, 5, 1, 1],
        "target_factors": [0.0, 0.475, 0.075, 0.5, 0.0, 0.0, 0.0, 0.5, 0.75, 0.5],
        "idle_ranges": [200, 5, 3, 50, 10, 10, 10, 20, 4, 0],
        "intervals": [5000, 1000, 1000, 500, 10400, 10500, 10600, 1000, 1000, 10000],
        "color": [128, 128, 255],
    },
    "embarrassed": {
        "velocities": [2, 5, 5, 5, 5, 5, 5, 1, 1, 1],
        "target_factors": [1.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.767, 0.843, 0.55],
        "idle_ranges": [10, 10, 10, 40, 10, 10, 10, 10, 10, 30],
        "intervals": [2000, 2000, 2000, 500, 2000, 2000, 2000, 1000, 10000, 3000],
        "color": [255, 0, 255],
    },
    "frustrated": {
        "velocities": [5, 1, 1, 5, 1, 1, 1, 1, 1, 1],
        "target_factors": [0.032, 0.25, 0.75, 0.5, 0.5, 0.0, 0.0, 0.733, 0.829, 0.5],
        "idle_ranges": [10, 5, 3, 10, 10, 10, 10, 10, 5, 5],
        "intervals": [5000, 1000, 1000, 1000, 1000, 1000, 1000, 5000, 3000, 3000],
        "color": [255, 0, 0],
    },
    "proud": {
        "velocities": [10, 1, 1, 10, 1, 5, 5, 1, 1, 1],
        "target_factors": [0.865, 0.15, 0.0, 0.489, 0.043, 0.0, 0.0, 0.7, 1.0, 0.5],
        "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 15, 1, 1],
        "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 2000, 3000, 4000],
        "color": [255, 255, 0],
    },
    "nostalgic": {
        "velocities": [10, 1, 1, 5, 1, 1, 1, 1, 1, 1],
        "target_factors": [0.865, 0.375, 0.25, 0.5, 0.0, 0.0, 0.0, 0.733, 0.829, 0.512],
        "idle_ranges": [100, 5, 5, 50, 10, 10, 10, 7, 5, 40],
        "intervals": [5000, 1000, 1000, 2000, 10400, 10500, 10600, 5000, 1000, 2000],
        "color": [0, 0, 64],
    },
    "relieved": {
        "velocities": [10, 1, 1, 10, 1, 5, 5, 3, 1, 1],
        "target_factors": [
            0.865,
            0.15,
            0.0,
            0.489,
            0.043,
            0.0,
            0.0,
            0.733,
            0.857,
            0.487,
        ],
        "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 7, 3, 20],
        "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 1000, 3000, 5000],
        "color": [0, 0, 160],
    },
    "grateful": {
        "velocities": [10, 1, 1, 10, 1, 5, 5, 1, 1, 1],
        "target_factors": [0.865, 0.15, 0.0, 0.489, 0.043, 0.0, 0.0, 0.533, 0.829, 0.5],
        "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 10, 10, 15],
        "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 5000, 3000, 10000],
        "color": [0, 255, 255],
    },
    "shy": {
        "velocities": [5, 1, 1, 5, 1, 1, 1, 2, 1, 1],
        "target_factors": [0.489, 1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.767, 1.0, 0.5],
        "idle_ranges": [300, 5, 3, 50, 10, 10, 10, 7, 3, 20],
        "intervals": [5000, 1000, 1000, 1000, 10400, 10500, 10600, 3000, 3000, 5000],
        "color": [255, 0, 255],
    },
    "disappointed": {
        "velocities": [2, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "target_factors": [0.449, 1.0, 0.8, 0.5, 0.529, 0.0, 0.0, 0.7, 0.857, 0.5],
        "idle_ranges": [100, 5, 5, 20, 10, 10, 10, 7, 7, 1],
        "intervals": [5000, 1000, 1000, 2000, 1000, 1000, 1000, 1000, 7000, 1000],
        "color": [255, 255, 0],
    },
    "jealous": {
        "velocities": [2, 10, 10, 5, 5, 5, 5, 3, 3, 1],
        "target_factors": [0.0, 0.325, 0.625, 0.489, 0.486, 0.0, 0.0, 0.5, 0.857, 0.5],
        "idle_ranges": [100, 2, 2, 40, 3, 10, 10, 10, 5, 20],
        "intervals": [2000, 5000, 5000, 5000, 5000, 2000, 2000, 2000, 2000, 4000],
        "color": [128, 0, 255],
    },
}


#: OpenAI chat tool schema for ``set_animation``. Shape:
#: ``{"type": "function", "function": {...}}``. The enum is derived from
#: :data:`ANIMATIONS` so the schema and table can never drift apart.
ANIMATION_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "set_animation",
            "description": (
                "Select an animation based on the emotional state determined "
                "from the current context or input. The chosen emotion drives "
                "Wheatley's servo movements and status LED color."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "animation": {
                        "type": "string",
                        "enum": list(ANIMATIONS.keys()),
                    }
                },
                "required": ["animation"],
                "additionalProperties": False,
            },
        },
    }
]
