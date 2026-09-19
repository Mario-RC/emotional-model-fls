import pytest

pytest.importorskip("skfuzzy")

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
