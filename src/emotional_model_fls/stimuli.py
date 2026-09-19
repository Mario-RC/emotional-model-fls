"""Mutable input, controller and history state for the fuzzy model."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from emotional_model_fls.config_loader import ConfigError, _is_finite_number, _is_number_pair
from emotional_model_fls.example_specs import DEFAULT_SPECS
from emotional_model_fls.sensors import SENSOR_RANGES

# All calibration values below are fictitious demonstration parameters.
SENSOR_DEFAULTS = {
    "battery": 8,
    "light": 8,
    "glucose": 8,
    "speech": 0,
    "right_antenna": 0,
    "left_antenna": 0,
    "front_button": 0,
    "right_ear_button": 0,
    "left_ear_button": 0,
    "right_body_button": 0,
    "left_body_button": 0,
}

DERIVED_DEFAULTS = {
    "antennas": 0,
    "antennas_frequency": 0,
    "flashlights_frequency": 0,
    "head_state": None,
    "head_buttons": 0,
    "head_buttons_frequency": 0,
    "body_buttons": 0,
}

CONTROLLER_DEFAULTS = {
    "mood": None,
    "alertness": None,
    "interest": None,
    "affective": None,
    "affective_head_button_ctrl": None,
    "affective_body_button_ctrl": None,
    "affective_null_buttons_ctrl": None,
    "affective_aux": None,
    "expectancy": None,
    "heartbeat": None,
    "body_speed": None,
    "general_state": None,
}

INITIAL_STATE_VALUES = {
    "interest": 8,
    "mood": 8,
    "expectancy": 8,
    "affective": 8,
    "alertness": 8,
}

DELAY_CONSTANTS = {
    "interest": 2,
    "mood": 2,
    "expectancy": 2,
    "affective": 2,
    "alertness": 2,
}

SENSOR_WEIGHTS = {
    "right_antenna": 0.5,
    "left_antenna": 0.5,
    "front_button": 0.25,
    "right_ear_button": 0.25,
    "left_ear_button": 0.25,
    "right_body_button": 0.5,
    "left_body_button": 0.5,
}

PROCESSING_DEFAULTS = {
    "flashlights_time": 8,
    "flashlights_threshold": 4,
    "flashlights_threshold_value": 8,
    "antennas_frequency_time": 8,
    "head_buttons_frequency_time": 8,
    "flashlights_debounce_steps": 2,
    "frequency_scale": 16,
}


class Stimuli:
    """Container for sensor defaults and stateful event-frequency windows."""

    def __init__(self, specs: Any | None = None):
        self.specs = specs or DEFAULT_SPECS
        self._initialize_runtime_settings()
        _set_attrs(self, self.sensor_defaults)
        _set_attrs(self, DERIVED_DEFAULTS)
        _set_attrs(self, CONTROLLER_DEFAULTS)
        self._initialize_delayed_states()
        self._initialize_frequency_windows()

    def _initialize_runtime_settings(self) -> None:
        settings = getattr(self.specs, "config", {}).get("runtime", {})
        groups = {"sensor_ranges", "sensor_defaults", "initial_states", "delays", "sensor_weights", "processing"}
        if not isinstance(settings, Mapping) or set(settings) - groups:
            raise ConfigError("runtime must be a mapping with known setting groups.")

        ranges = dict(SENSOR_RANGES)
        for name in ranges:
            spec = getattr(self.specs, name.upper(), None)
            if spec is not None:
                ranges[name] = (spec.universe[0], spec.universe[1] - 1)
        self.sensor_ranges = _settings(settings, "sensor_ranges", ranges)
        for name, bounds in self.sensor_ranges.items():
            if not _is_number_pair(bounds) or bounds[0] >= bounds[1]:
                raise ConfigError(f"runtime.sensor_ranges.{name} needs finite increasing bounds.")
            if name in {"battery", "speech", "light", "glucose"}:
                lower, upper = ranges[name]
                if bounds[0] < lower or bounds[1] > upper:
                    raise ConfigError(f"runtime.sensor_ranges.{name} must stay inside its variable universe.")

        self.sensor_defaults = _bounded_settings(settings, "sensor_defaults", SENSOR_DEFAULTS, self.sensor_ranges)
        state_ranges = {
            name: (getattr(self.specs, name.upper()).universe[0], getattr(self.specs, name.upper()).universe[1] - 1)
            for name in INITIAL_STATE_VALUES
        }
        self.initial_state_values = _bounded_settings(settings, "initial_states", INITIAL_STATE_VALUES, state_ranges)
        self.delays = _settings(settings, "delays", DELAY_CONSTANTS)
        self.sensor_weights = _settings(settings, "sensor_weights", SENSOR_WEIGHTS)
        processing = _settings(settings, "processing", PROCESSING_DEFAULTS)
        for group, values in (("delays", self.delays), ("sensor_weights", self.sensor_weights), ("processing", processing)):
            for name, value in values.items():
                if not _is_finite_number(value) or value < 0:
                    raise ConfigError(f"runtime.{group}.{name} must be finite and non-negative.")
        for name in ("flashlights_time", "flashlights_threshold_value", "antennas_frequency_time", "head_buttons_frequency_time", "flashlights_debounce_steps"):
            value = processing[name]
            minimum = 0 if name == "flashlights_debounce_steps" else 1
            if not isinstance(value, int) or value < minimum:
                raise ConfigError(f"runtime.processing.{name} must be an integer >= {minimum}.")
        if processing["frequency_scale"] <= 0:
            raise ConfigError("runtime.processing.frequency_scale must be positive.")
        _set_attrs(self, processing)

    def _initialize_delayed_states(self) -> None:
        for state_name, initial_value in self.initial_state_values.items():
            setattr(self, f"{state_name}_initial_value", initial_value)
            setattr(self, f"{state_name}_base_value", initial_value)
            setattr(self, f"{state_name}_delay", [[initial_value], [initial_value]])

        for state_name, delay_const in self.delays.items():
            setattr(self, f"{state_name}_delay_const", delay_const)

    def _initialize_frequency_windows(self) -> None:
        """Initialize event windows whose duration is window_size * step duration."""

        self.flashlights_stack = [False] * self.flashlights_time
        self.flashlights_count = 0
        self.light_previous_values = [0] * self.flashlights_threshold_value
        self.flashlights_debounce = 0

        self.antennas_frequency_stack = [False] * self.antennas_frequency_time
        self.antennas_frequency_count = 0
        self.antennas_frequency_current_value = 0

        self.head_buttons_frequency_stack = [False] * self.head_buttons_frequency_time
        self.head_buttons_frequency_count = 0


def _settings(settings: Mapping, name: str, defaults: dict) -> dict:
    overrides = settings.get(name, {})
    if not isinstance(overrides, Mapping) or set(overrides) - set(defaults):
        raise ConfigError(f"runtime.{name} must be a mapping with known parameter names.")
    return {**defaults, **overrides}


def _bounded_settings(settings: Mapping, name: str, defaults: dict, ranges: dict) -> dict:
    adapted = dict(defaults)
    for key, value in adapted.items():
        lower, upper = ranges[key]
        if not lower <= value <= upper:
            adapted[key] = (lower + upper) / 2
    values = _settings(settings, name, adapted)
    for key, value in values.items():
        lower, upper = ranges[key]
        if not _is_finite_number(value) or not lower <= value <= upper:
            raise ConfigError(f"runtime.{name}.{key} must be finite and inside its configured range.")
    return values


def _set_attrs(target: object, values: dict[str, object]) -> None:
    for name, value in values.items():
        setattr(target, name, value)
