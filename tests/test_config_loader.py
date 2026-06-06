from emotional_model_fls.config_loader import load_spec_bundle
from emotional_model_fls.example_specs import DEFAULT_SPECS


def test_default_specs_are_available():
    assert DEFAULT_SPECS.MOOD.key == "mood"
    assert DEFAULT_SPECS.MOOD_RULES


def test_example_config_loads_from_file():
    specs = load_spec_bundle("examples/toy_emotional_model.yaml")

    assert specs.HEARTBEAT.key == "heartbeat"
    assert specs.HEARTBEAT_RULES
