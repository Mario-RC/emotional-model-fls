"""Runtime API for stepping and running the emotional model."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from emotional_model_fls.config_loader import load_spec_bundle
from emotional_model_fls.fuzzy_logic import FuzzyLogic
from emotional_model_fls.sensors import SENSOR_FIELDS, SENSOR_RANGES, SensorInputs


@dataclass(slots=True)
class ModelOutputs:
    """Current model outputs and internal emotional labels."""

    general_state: str
    general_state_value: float
    heartbeat: float
    body_speed: float
    mood: float
    mood_label: str
    alertness: float
    alertness_label: str
    interest: float
    interest_label: str
    affective: float
    affective_label: str
    expectancy: float
    expectancy_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


shared_data: dict[str, Any] = {field: None for field in SENSOR_FIELDS}
shared_data.update({"heartbeat": None, "body_speed": None, "general_state": None})


class EmotionalModel:
    """High-level API around the fuzzy logic model."""

    def __init__(
        self,
        fuzzy_logic: FuzzyLogic | None = None,
        *,
        config_path: str | Path | None = None,
        specs: Any | None = None,
    ):
        if fuzzy_logic is not None and (config_path is not None or specs is not None):
            raise ValueError("Pass either fuzzy_logic or config_path/specs, not both.")
        if config_path is not None and specs is not None:
            raise ValueError("Pass either config_path or specs, not both.")

        loaded_specs = load_spec_bundle(config_path) if config_path is not None else specs
        self.fuzzy_logic = fuzzy_logic or FuzzyLogic(specs=loaded_specs)
        self.fuzzyLogic = self.fuzzy_logic  # Backwards-compatible attribute.
        self.shared_data = dict(shared_data)
        self.general_state = "UNKNOWN"

    def apply_inputs(self, inputs: SensorInputs | Mapping[str, Any] | None = None) -> None:
        if inputs is None:
            return
        values = asdict(inputs) if isinstance(inputs, SensorInputs) else dict(inputs)
        for name, value in values.items():
            if value is None:
                continue
            if name not in SENSOR_FIELDS:
                raise KeyError(f"Unknown sensor field: {name}")
            self._validate_sensor_value(name, value)
            setattr(self.fuzzy_logic, name, value)

    def update_from_shared_data(self) -> None:
        for name in SENSOR_FIELDS:
            value = self.shared_data.get(name)
            if value is None:
                continue
            self._validate_sensor_value(name, value)
            setattr(self.fuzzy_logic, name, value)
            self.shared_data[name] = None

    def step(self, inputs: SensorInputs | Mapping[str, Any] | None = None) -> ModelOutputs:
        self.apply_inputs(inputs)
        self.update_from_shared_data()
        self._refresh_derived_inputs()
        self.fuzzy_logic.doFuzzyLogic()
        outputs = self._collect_outputs()
        self._publish_outputs(outputs)
        return outputs

    def run(
        self,
        interval: float = 0.1,
        steps: int | None = 1,
        print_outputs: bool = True,
    ) -> None:
        count = 0
        while steps is None or count < steps:
            outputs = self.step()
            if print_outputs:
                print(outputs.to_json())
            count += 1
            if steps is None or count < steps:
                time.sleep(interval)

    def handle_msg(self) -> None:
        """Compatibility shim for the original shared-data workflow."""
        self.update_from_shared_data()
        self._refresh_derived_inputs()

    def update(self) -> ModelOutputs:
        """Compatibility shim for the original one-step update method."""
        return self.step()

    def onRun(self, interval: float = 0.1) -> None:
        """Compatibility shim for the original long-running method."""
        self.run(interval=interval, steps=None, print_outputs=True)

    def _refresh_derived_inputs(self) -> None:
        model = self.fuzzy_logic
        model.antennas = model.setAntennas(model.right_antenna, model.left_antenna)
        model.antennas_frequency = model.setAntennasFrequency(model.antennas)
        model.head_buttons = model.setHeadButtons(
            model.front_button,
            model.right_ear_button,
            model.left_ear_button,
        )
        model.head_buttons_frequency = model.setHeadButtonsFrequency(model.head_buttons)
        model.body_buttons = model.setBodyButton(
            model.right_body_button,
            model.left_body_button,
        )
        model.flashlights_frequency = model.setFlashlightsFrequency(model.light)
        model.setHeadState()

    def _collect_outputs(self) -> ModelOutputs:
        model = self.fuzzy_logic
        general_state_value = float(model.general_state.output["general_state"])
        self.general_state = model.mapGeneralState(general_state_value)
        return ModelOutputs(
            general_state=self.general_state,
            general_state_value=general_state_value,
            heartbeat=float(model.heartbeat.output["heartbeat"]),
            body_speed=float(model.body_speed.output["body_speed"]),
            mood=float(model.mood.output["mood"]),
            mood_label=model.mapMood(model.mood.output["mood"]),
            alertness=float(model.alertness.output["alertness"]),
            alertness_label=model.mapAlertness(model.alertness.output["alertness"]),
            interest=float(model.interest.output["interest"]),
            interest_label=model.mapInterest(model.interest.output["interest"]),
            affective=float(model.affective.output["affective"]),
            affective_label=model.mapAffective(model.affective.output["affective"]),
            expectancy=float(model.expectancy.output["expectancy"]),
            expectancy_label=model.mapExpectancy(model.expectancy.output["expectancy"]),
        )

    def _publish_outputs(self, outputs: ModelOutputs) -> None:
        self.shared_data["general_state"] = outputs.general_state
        self.shared_data["heartbeat"] = outputs.heartbeat
        self.shared_data["body_speed"] = outputs.body_speed

    def _validate_sensor_value(self, name: str, value: Any) -> None:
        minimum, maximum = getattr(self.fuzzy_logic, "sensor_ranges", SENSOR_RANGES)[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
        if value < minimum or value > maximum:
            raise ValueError(f"{name} must be in [{minimum}, {maximum}], got {value!r}")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite, got {value!r}")
