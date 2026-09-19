"""Sensor input definitions and validation ranges."""

from __future__ import annotations

from dataclasses import dataclass

SENSOR_FIELDS = (
    "battery",
    "right_antenna",
    "left_antenna",
    "light",
    "glucose",
    "speech",
    "front_button",
    "right_ear_button",
    "left_ear_button",
    "right_body_button",
    "left_body_button",
)

# Fictitious demo ranges in arbitrary units; research ranges are private.
SENSOR_RANGES = {
    "battery": (0, 16),
    "right_antenna": (0, 16),
    "left_antenna": (0, 16),
    "light": (0, 16),
    "glucose": (0, 16),
    "speech": (0, 16),
    "front_button": (0, 16),
    "right_ear_button": (0, 16),
    "left_ear_button": (0, 16),
    "right_body_button": (0, 16),
    "left_body_button": (0, 16),
}


@dataclass(slots=True)
class SensorInputs:
    """Optional sensor updates for one model step."""

    battery: float | None = None
    right_antenna: float | None = None
    left_antenna: float | None = None
    light: float | None = None
    glucose: float | None = None
    speech: float | None = None
    front_button: float | None = None
    right_ear_button: float | None = None
    left_ear_button: float | None = None
    right_body_button: float | None = None
    left_body_button: float | None = None
