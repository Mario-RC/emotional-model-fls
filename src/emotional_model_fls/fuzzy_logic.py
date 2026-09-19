"""Orchestration and derived-input helpers for the fuzzy emotional model."""

from emotional_model_fls.expressions import Expressions
from emotional_model_fls.labels import (
    map_affective,
    map_alertness,
    map_expectancy,
    map_general_state,
    map_interest,
    map_mood,
)


# Weights, frequency scales and debounce values below are fictitious demo parameters.
class FuzzyLogic(Expressions):
    """Run the emotional fuzzy subsystems and maintain derived sensor inputs."""

    def doFuzzyLogic(self):
        """Run all fuzzy controllers in dependency order."""

        self.doAlertness()
        self.doInterest()
        self.doMood()
        self.doAffective(self.head_state)
        self.doExpectancy()
        self.doHeartbeat()
        self.doBodySpeed()
        self.doGeneralState()
        return self

    def setHeadState(self):
        """Select the affective controller based on active buttons."""

        if self.head_buttons != 0:
            self.head_state = "HEAD BUTTON"
        elif self.body_buttons != 0:
            self.head_state = "BODY BUTTON"
        else:
            self.head_state = "NULL BUTTON"
        return self.head_state

    def mapMood(self, mood_value):
        return map_mood(mood_value, self.specs)

    def mapAlertness(self, alertness_value):
        return map_alertness(alertness_value, self.specs)

    def mapInterest(self, interest_value):
        return map_interest(interest_value, self.specs)

    def mapAffective(self, affective_value):
        return map_affective(affective_value, self.specs)

    def mapExpectancy(self, expectancy_value):
        return map_expectancy(expectancy_value, self.specs)

    def mapGeneralState(self, general_state_value):
        return map_general_state(general_state_value, self.specs)

    def setAntennas(self, _right_antenna_value, _left_antenna_value):
        """Combine left and right antenna touches into the model input scale."""

        return (_right_antenna_value * 0.5) + (_left_antenna_value * 0.5)

    def setAntennasFrequency(self, _antennas_value):
        """Return antenna-touch frequency over a rolling window."""

        self.antennas_frequency_stack[self.antennas_frequency_count] = _antennas_value != 0
        if self.antennas_frequency_count >= self.antennas_frequency_time - 1:
            touches = sum(self.antennas_frequency_stack)
            self.antennas_frequency_current_value = (
                touches / self.antennas_frequency_time
            ) * 16
            self.antennas_frequency_count = 0
        else:
            self.antennas_frequency_count += 1
        return self.antennas_frequency_current_value

    def setHeadButtons(self, _front_button_value, _right_ear_button_value, _left_ear_button_value):
        """Combine head-button inputs into the model input scale."""

        return (_front_button_value * 0.25) + (_right_ear_button_value * 0.25) + (
            _left_ear_button_value * 0.25
        )

    def setHeadButtonsFrequency(self, _head_buttons_value):
        """Return head-button press frequency over a rolling window."""

        self.head_buttons_frequency_stack[
            self.head_buttons_frequency_count
        ] = _head_buttons_value != 0
        if self.head_buttons_frequency_count >= self.head_buttons_frequency_time - 1:
            self.head_buttons_frequency_count = 0
        else:
            self.head_buttons_frequency_count += 1
        presses = sum(self.head_buttons_frequency_stack)
        return (presses / self.head_buttons_frequency_time) * 16

    def setBodyButton(self, _right_body_button_value, _left_body_button_value):
        """Combine left and right body-button inputs into the model input scale."""

        return (_right_body_button_value * 0.5) + (_left_body_button_value * 0.5)

    def setFlashlightsFrequency(self, _lights_value):
        """Return detected light-flash frequency over a rolling window."""

        for i in reversed(range(self.flashlights_threshold_value - 1)):
            self.light_previous_values[i + 1] = self.light_previous_values[i]
        self.light_previous_values[0] = _lights_value

        oldest_value = self.light_previous_values[self.flashlights_threshold_value - 1]
        detected_flash = (
            abs(self.light_previous_values[0] - oldest_value) > self.flashlights_threshold
            and self.flashlights_debounce == 0
        )
        self.flashlights_stack[self.flashlights_count] = detected_flash
        if detected_flash:
            self.flashlights_debounce = 2
        elif self.flashlights_debounce > 0:
            self.flashlights_debounce -= 1

        if self.flashlights_count >= self.flashlights_time - 1:
            self.flashlights_count = 0
        else:
            self.flashlights_count += 1

        flashes = sum(self.flashlights_stack)
        return (flashes / self.flashlights_time) * 16
