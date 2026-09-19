from collections import Counter

import pytest

from emotional_model_fls.config_loader import ConfigError, load_spec_bundle
from emotional_model_fls.example_specs import DEFAULT_SPECS


def test_default_specs_are_available():
    assert DEFAULT_SPECS.MOOD.key == "mood"
    assert DEFAULT_SPECS.MOOD_RULES


def test_example_config_loads_from_file():
    specs = load_spec_bundle("examples/toy_emotional_model.yaml")

    assert specs.HEARTBEAT.key == "heartbeat"
    assert specs.HEARTBEAT_RULES


@pytest.mark.parametrize("style", ["overrides", "items"])
@pytest.mark.parametrize("when", [{"batery": "DEMO_1"}, {"battery": "MISSING"}])
def test_rule_conditions_reject_unknown_names(demo_config, style, when):
    rules = demo_config["rules"]["mood"]
    rules[style] = [{"when": when, "then": "DEMO_1"}]
    if style == "items":
        del rules["default"]
        del rules["overrides"]
    with pytest.raises(ConfigError, match="unknown"):
        load_spec_bundle(demo_config)


def test_override_lists_and_omitted_dimensions_still_work(demo_config):
    demo_config["rules"]["mood"]["overrides"] = [
        {"when": {"battery": ["DEMO_1", "DEMO_2"]}, "then": "DEMO_1"},
    ]
    rules = load_spec_bundle(demo_config).MOOD_RULES
    assert Counter(rule.output for rule in rules) == {"DEMO_1": 30, "DEMO_3": 15}


@pytest.mark.parametrize("universe", [[0, float("nan")], [0, float("inf")], [5, 0], [2, 2], [0, 1], [0, 2.5], [False, 17]])
def test_invalid_universes_are_rejected(demo_config, universe):
    demo_config["variables"]["battery"]["universe"] = universe
    with pytest.raises(ConfigError, match="universe"):
        load_spec_bundle(demo_config)


@pytest.mark.parametrize("points", [[0, 0, 1, float("nan")], [0, 0, 1, float("inf")], [4, 3, 2, 1], [2, 2, 2, 2]])
def test_invalid_membership_points_are_rejected(demo_config, points):
    demo_config["variables"]["battery"]["terms"][0]["points"] = points
    with pytest.raises(ConfigError, match="points"):
        load_spec_bundle(demo_config)


def test_json_root_is_validated_without_pyyaml(tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "yaml", None)
    path = tmp_path / "invalid.json"
    path.write_text("[]")
    with pytest.raises(ConfigError, match="root must be a mapping"):
        load_spec_bundle(path)
