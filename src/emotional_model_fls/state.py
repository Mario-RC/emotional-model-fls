"""Internal emotional-state controllers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from skfuzzy import control as ctrl

from emotional_model_fls.fuzzy_engine import (
    VariableSpec,
    assign_inputs,
    build_control_system,
    build_simulation,
    compute_delayed_feedback,
    spec_map,
)
from emotional_model_fls.stimuli import Stimuli


class State(Stimuli):
    """Build and run the fuzzy controllers for internal emotional states."""

    def setMood(self):
        self.mood = build_simulation(
            [self.specs.BATTERY, self.specs.ANTENNAS, self.specs.MOOD_INPUT],
            self.specs.MOOD,
            self.specs.MOOD_RULES,
        )

    def doMood(self):
        self._ensure_delayed_controller(
            "mood",
            self.setMood,
            [self.specs.BATTERY, self.specs.ANTENNAS, self.specs.MOOD_INPUT],
            {
                "battery": self.battery,
                "antennas": self.antennas,
                "mood": self.mood_initial_value,
            },
        )
        self._compute_delayed_state(
            controller_name="mood",
            input_specs=[self.specs.BATTERY, self.specs.ANTENNAS, self.specs.MOOD_INPUT],
            live_inputs={"battery": self.battery, "antennas": self.antennas},
            feedback_spec=self.specs.MOOD_INPUT,
            output_key="mood",
            base_attr="mood_base_value",
            delay_const=self.mood_delay_const,
            delay_history=self.mood_delay,
        )

    def setAlertness(self):
        self.alertness = build_simulation(
            [self.specs.LIGHT, self.specs.GLUCOSE, self.specs.ALERTNESS_INPUT],
            self.specs.ALERTNESS,
            self.specs.ALERTNESS_RULES,
        )

    def doAlertness(self):
        self._ensure_delayed_controller(
            "alertness",
            self.setAlertness,
            [self.specs.LIGHT, self.specs.GLUCOSE, self.specs.ALERTNESS_INPUT],
            {
                "glucose": self.glucose,
                "light": self.light,
                "alertness": self.alertness_initial_value,
            },
        )
        self._compute_delayed_state(
            controller_name="alertness",
            input_specs=[self.specs.LIGHT, self.specs.GLUCOSE, self.specs.ALERTNESS_INPUT],
            live_inputs={"glucose": self.glucose, "light": self.light},
            feedback_spec=self.specs.ALERTNESS_INPUT,
            output_key="alertness",
            base_attr="alertness_base_value",
            delay_const=self.alertness_delay_const,
            delay_history=self.alertness_delay,
        )

    def setInterest(self):
        self.interest = build_simulation(
            [self.specs.SPEECH, self.specs.INTEREST_INPUT],
            self.specs.INTEREST,
            self.specs.INTEREST_RULES,
        )

    def doInterest(self):
        self._ensure_delayed_controller(
            "interest",
            self.setInterest,
            [self.specs.SPEECH, self.specs.INTEREST_INPUT],
            {"speech": self.speech, "interest": self.interest_initial_value},
        )
        self._compute_delayed_state(
            controller_name="interest",
            input_specs=[self.specs.SPEECH, self.specs.INTEREST_INPUT],
            live_inputs={"speech": self.speech},
            feedback_spec=self.specs.INTEREST_INPUT,
            output_key="interest",
            base_attr="interest_base_value",
            delay_const=self.interest_delay_const,
            delay_history=self.interest_delay,
        )

    def setAffectiveHeadButton(self):
        self.affective_head_button_ctrl = build_control_system(
            [self.specs.HEAD_BUTTONS, self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.FLASHLIGHTS_FREQUENCY, self.specs.AFFECTIVE_INPUT],
            self.specs.AFFECTIVE,
            self.specs.AFFECTIVE_HEAD_RULES,
        )

    def setAffectiveBodyButton(self):
        self.affective_body_button_ctrl = build_control_system(
            [self.specs.BODY_BUTTONS, self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.FLASHLIGHTS_FREQUENCY, self.specs.AFFECTIVE_INPUT],
            self.specs.AFFECTIVE,
            self.specs.AFFECTIVE_BODY_RULES,
        )

    def setAffectiveNullButton(self):
        self.affective_null_buttons_ctrl = build_control_system(
            [self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.FLASHLIGHTS_FREQUENCY, self.specs.AFFECTIVE_INPUT],
            self.specs.AFFECTIVE,
            self.specs.AFFECTIVE_NULL_RULES,
        )

    def doAffective(self, head_state):
        if self.affective is None:
            self._initialize_affective_controllers()

        controller, input_specs, live_inputs = self._active_affective_controller(head_state)
        self.affective = ctrl.ControlSystemSimulation(controller)
        assign_inputs(
            self.affective,
            spec_map(input_specs),
            {
                "flashlights_frequency": self.flashlights_frequency,
                "head_buttons_frequency": self.head_buttons_frequency,
                **live_inputs,
            },
        )

        delayed = (
            self.affective_base_value * self.affective_delay_const + self.affective_aux
        ) / (self.affective_delay_const + 1)
        self.affective.input[self.specs.AFFECTIVE_INPUT.control_name] = delayed
        self.affective_base_value = delayed
        self.affective_delay[0].append(self.affective_aux)
        self.affective_delay[1].append(delayed)

        self.affective.compute()
        self.affective_aux = self.affective.output["affective"]

    def setExpectancy(self):
        self.expectancy = build_simulation(
            [self.specs.ANTENNAS_FREQUENCY, self.specs.EXPECTANCY_INPUT],
            self.specs.EXPECTANCY,
            self.specs.EXPECTANCY_RULES,
        )

    def doExpectancy(self):
        self._ensure_delayed_controller(
            "expectancy",
            self.setExpectancy,
            [self.specs.ANTENNAS_FREQUENCY, self.specs.EXPECTANCY_INPUT],
            {
                "antennas_frequency": self.antennas_frequency,
                "expectancy": self.expectancy_initial_value,
            },
        )
        self._compute_delayed_state(
            controller_name="expectancy",
            input_specs=[self.specs.ANTENNAS_FREQUENCY, self.specs.EXPECTANCY_INPUT],
            live_inputs={"antennas_frequency": self.antennas_frequency},
            feedback_spec=self.specs.EXPECTANCY_INPUT,
            output_key="expectancy",
            base_attr="expectancy_base_value",
            delay_const=self.expectancy_delay_const,
            delay_history=self.expectancy_delay,
        )

    def _ensure_delayed_controller(
        self,
        controller_name: str,
        setup: Callable[[], None],
        input_specs: Sequence[VariableSpec],
        initial_inputs: Mapping[str, float],
    ) -> None:
        if getattr(self, controller_name) is not None:
            return
        setup()
        simulation = getattr(self, controller_name)
        assign_inputs(simulation, spec_map(input_specs), initial_inputs)
        simulation.compute()

    def _compute_delayed_state(
        self,
        controller_name: str,
        input_specs: Sequence[VariableSpec],
        live_inputs: Mapping[str, float],
        feedback_spec: VariableSpec,
        output_key: str,
        base_attr: str,
        delay_const: float,
        delay_history: list[list[float]],
    ) -> None:
        simulation = getattr(self, controller_name)
        assign_inputs(simulation, spec_map(input_specs), live_inputs)
        raw_output, delayed = compute_delayed_feedback(
            simulation=simulation,
            feedback_spec=feedback_spec,
            output_key=output_key,
            current_base=getattr(self, base_attr),
            delay_const=delay_const,
        )
        setattr(self, base_attr, delayed)
        delay_history[0].append(raw_output)
        delay_history[1].append(delayed)
        simulation.compute()

    def _initialize_affective_controllers(self) -> None:
        self.setAffectiveHeadButton()
        self.setAffectiveBodyButton()
        self.setAffectiveNullButton()
        self.affective = ctrl.ControlSystemSimulation(self.affective_null_buttons_ctrl)
        assign_inputs(
            self.affective,
            spec_map([self.specs.FLASHLIGHTS_FREQUENCY, self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.AFFECTIVE_INPUT]),
            {
                "flashlights_frequency": self.flashlights_frequency,
                "head_buttons_frequency": self.head_buttons_frequency,
                "affective": self.affective_initial_value,
            },
        )
        self.affective.compute()
        self.affective_aux = self.affective.output["affective"]

    def _active_affective_controller(self, head_state):
        if head_state == "HEAD BUTTON":
            return (
                self.affective_head_button_ctrl,
                [self.specs.HEAD_BUTTONS, self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.FLASHLIGHTS_FREQUENCY, self.specs.AFFECTIVE_INPUT],
                {"head_buttons": self.head_buttons},
            )
        if head_state == "BODY BUTTON":
            return (
                self.affective_body_button_ctrl,
                [self.specs.BODY_BUTTONS, self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.FLASHLIGHTS_FREQUENCY, self.specs.AFFECTIVE_INPUT],
                {"body_buttons": self.body_buttons},
            )
        return (
            self.affective_null_buttons_ctrl,
            [self.specs.HEAD_BUTTONS_FREQUENCY, self.specs.FLASHLIGHTS_FREQUENCY, self.specs.AFFECTIVE_INPUT],
            {},
        )
