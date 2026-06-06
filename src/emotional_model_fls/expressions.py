"""Expression controllers derived from the internal emotional states."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from emotional_model_fls.fuzzy_engine import (
    VariableSpec,
    assign_inputs,
    build_simulation,
    spec_map,
)
from emotional_model_fls.state import State


class Expressions(State):
    """Build and run fuzzy controllers for externally visible expressions."""

    def setHeartbeat(self):
        self.heartbeat = build_simulation(
            [self.specs.ALERTNESS_INPUT],
            self.specs.HEARTBEAT,
            self.specs.HEARTBEAT_RULES,
        )

    def doHeartbeat(self):
        self._ensure_expression_controller(
            "heartbeat",
            self.setHeartbeat,
            [self.specs.ALERTNESS_INPUT],
            {"alertness": self.alertness.output["alertness"]},
        )
        self._compute_expression(
            "heartbeat",
            [self.specs.ALERTNESS_INPUT],
            {"alertness": self.alertness_base_value},
        )

    def setBodySpeed(self):
        self.body_speed = build_simulation(
            [self.specs.MOOD_INPUT, self.specs.INTEREST_INPUT],
            self.specs.BODY_SPEED,
            self.specs.BODY_SPEED_RULES,
        )

    def doBodySpeed(self):
        self._ensure_expression_controller(
            "body_speed",
            self.setBodySpeed,
            [self.specs.MOOD_INPUT, self.specs.INTEREST_INPUT],
            {
                "mood": self.mood.output["mood"],
                "interest": self.interest.output["interest"],
            },
        )
        self._compute_expression(
            "body_speed",
            [self.specs.MOOD_INPUT, self.specs.INTEREST_INPUT],
            {
                "mood": self.mood_base_value,
                "interest": self.interest_base_value,
            },
        )

    def setGeneralState(self):
        self.general_state = build_simulation(
            [self.specs.MOOD_INPUT, self.specs.ALERTNESS_INPUT, self.specs.AFFECTIVE_INPUT, self.specs.EXPECTANCY_INPUT],
            self.specs.GENERAL_STATE,
            self.specs.GENERAL_STATE_RULES,
        )

    def doGeneralState(self):
        self._ensure_expression_controller(
            "general_state",
            self.setGeneralState,
            [self.specs.MOOD_INPUT, self.specs.ALERTNESS_INPUT, self.specs.AFFECTIVE_INPUT, self.specs.EXPECTANCY_INPUT],
            {
                "mood": self.mood.output["mood"],
                "alertness": self.alertness.output["alertness"],
                "affective": self.affective.output["affective"],
                "expectancy": self.expectancy.output["expectancy"],
            },
        )
        self._compute_expression(
            "general_state",
            [self.specs.MOOD_INPUT, self.specs.ALERTNESS_INPUT, self.specs.AFFECTIVE_INPUT, self.specs.EXPECTANCY_INPUT],
            {
                "mood": self.mood_base_value,
                "alertness": self.alertness_base_value,
                "affective": self.affective_base_value,
                "expectancy": self.expectancy_base_value,
            },
        )

    def _ensure_expression_controller(
        self,
        controller_name: str,
        setup: Callable[[], None],
        input_specs: Sequence[VariableSpec],
        initial_inputs: Mapping[str, float],
    ) -> None:
        if getattr(self, controller_name) is not None:
            return
        setup()
        self._compute_expression(controller_name, input_specs, initial_inputs)

    def _compute_expression(
        self,
        controller_name: str,
        input_specs: Sequence[VariableSpec],
        values: Mapping[str, float],
    ) -> None:
        simulation = getattr(self, controller_name)
        assign_inputs(simulation, spec_map(input_specs), values)
        simulation.compute()
