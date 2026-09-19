"""Mutable input, controller and history state for the fuzzy model."""

from __future__ import annotations

from typing import Any

from emotional_model_fls.example_specs import DEFAULT_SPECS

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


class Stimuli:
    """Container for sensor defaults and stateful event-frequency windows."""

    def __init__(self, specs: Any | None = None):
        self.specs = specs or DEFAULT_SPECS
        _set_attrs(self, SENSOR_DEFAULTS)
        _set_attrs(self, DERIVED_DEFAULTS)
        _set_attrs(self, CONTROLLER_DEFAULTS)
        self._initialize_delayed_states()
        self._initialize_frequency_windows()

    def _initialize_delayed_states(self) -> None:
        for state_name, initial_value in INITIAL_STATE_VALUES.items():
            setattr(self, f"{state_name}_initial_value", initial_value)
            setattr(self, f"{state_name}_base_value", initial_value)
            setattr(self, f"{state_name}_delay", [[initial_value], [initial_value]])

        for state_name, delay_const in DELAY_CONSTANTS.items():
            setattr(self, f"{state_name}_delay_const", delay_const)

    def _initialize_frequency_windows(self) -> None:
        """Initialize event windows whose duration is window_size * step duration."""

        self.flashlights_time = 8
        self.flashlights_stack = [False] * self.flashlights_time
        self.flashlights_threshold = 4
        self.flashlights_threshold_value = 8
        self.flashlights_count = 0
        self.light_previous_values = [0] * self.flashlights_threshold_value
        self.flashlights_debounce = 0

        self.antennas_frequency_time = 8
        self.antennas_frequency_stack = [False] * self.antennas_frequency_time
        self.antennas_frequency_count = 0
        self.antennas_frequency_current_value = 0

        self.head_buttons_frequency_time = 8
        self.head_buttons_frequency_stack = [False] * self.head_buttons_frequency_time
        self.head_buttons_frequency_count = 0


def _set_attrs(target: object, values: dict[str, object]) -> None:
    for name, value in values.items():
        setattr(target, name, value)
