import pytest

pytest.importorskip("skfuzzy")

from emotional_model_fls.config_loader import ConfigError, load_spec_bundle
from emotional_model_fls.runtime import EmotionalModel, SensorInputs


def test_runtime_step_returns_outputs():
    model = EmotionalModel()
    outputs = model.step(SensorInputs(speech=8, battery=16))

    assert outputs.general_state
    assert outputs.heartbeat > 0
    assert outputs.body_speed >= 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("shared", [False, True])
def test_non_finite_sensor_values_are_rejected(value, shared):
    model = EmotionalModel()
    with pytest.raises(ValueError):
        if shared:
            model.shared_data["battery"] = value
            model.update_from_shared_data()
        else:
            model.apply_inputs({"battery": value})


def test_sensor_validation_rejects_out_of_range_values():
    model = EmotionalModel()

    with pytest.raises(ValueError):
        model.step(SensorInputs(battery=17))


def test_runtime_accepts_custom_config_path():
    model = EmotionalModel(config_path="examples/toy_emotional_model.yaml")
    outputs = model.step(SensorInputs(speech=12))

    assert outputs.general_state


@pytest.mark.parametrize("shared", [False, True])
def test_custom_sensor_universe_is_used(demo_config, shared):
    battery = demo_config["variables"]["battery"]
    battery["universe"] = [0, 41]
    for term in battery["terms"]:
        term["points"] = [point * 2.5 for point in term["points"]]
    model = EmotionalModel(specs=load_spec_bundle(demo_config))
    if shared:
        model.shared_data["battery"] = 32
        model.update_from_shared_data()
    else:
        model.apply_inputs({"battery": 32})
    assert model.fuzzy_logic.battery == 32
    with pytest.raises(ValueError):
        model.apply_inputs({"battery": 41})
    assert model.step().general_state


def test_optional_runtime_settings_drive_processing(demo_config):
    demo_config["runtime"] = {
        "sensor_ranges": {"right_antenna": [0, 32]},
        "sensor_defaults": {"right_antenna": 12},
        "initial_states": {"mood": 6},
        "delays": {"mood": 4},
        "sensor_weights": {"right_antenna": 0.25},
        "processing": {
            "antennas_frequency_time": 3,
            "head_buttons_frequency_time": 4,
            "flashlights_time": 4,
            "flashlights_threshold_value": 2,
            "flashlights_threshold": 3,
            "flashlights_debounce_steps": 1,
            "frequency_scale": 12,
        },
    }
    model = EmotionalModel(specs=load_spec_bundle(demo_config))
    logic = model.fuzzy_logic
    assert logic.right_antenna == 12
    assert logic.mood_initial_value == 6
    assert logic.mood_delay_const == 4
    assert logic.setAntennas(20, 0) == 5
    assert [logic.setAntennasFrequency(1) for _ in range(3)] == [0, 0, 12]
    assert logic.setHeadButtonsFrequency(1) == 3
    assert logic.setFlashlightsFrequency(12) == 3
    assert logic.flashlights_debounce == 1
    assert model.step().general_state
    assert EmotionalModel().fuzzy_logic.right_antenna == 0


def test_default_state_adapts_to_custom_universe(demo_config):
    mood = demo_config["variables"]["mood"]
    mood["universe"] = [20, 37]
    for term in mood["terms"]:
        term["points"] = [point + 20 for point in term["points"]]
    model = EmotionalModel(specs=load_spec_bundle(demo_config))
    assert model.fuzzy_logic.mood_initial_value == 28
    assert 20 <= model.step().mood <= 36


@pytest.mark.parametrize("settings", [
    {"unknown": {}},
    {"sensor_ranges": {"batery": [0, 32]}},
    {"sensor_ranges": {"battery": [0, 32]}},
    {"sensor_defaults": {"battery": float("nan")}},
    {"initial_states": {"mood": 17}},
    {"delays": {"mood": -1}},
    {"sensor_weights": {"right_antenna": float("inf")}},
    {"processing": {"antennas_frequency_time": 0}},
    {"processing": {"flashlights_time": 2.5}},
    {"processing": {"frequency_scale": 0}},
])
def test_invalid_runtime_settings_are_rejected(demo_config, settings):
    demo_config["runtime"] = settings
    with pytest.raises(ConfigError, match="runtime"):
        EmotionalModel(specs=load_spec_bundle(demo_config))
