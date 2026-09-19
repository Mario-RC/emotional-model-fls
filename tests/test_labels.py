from functools import partial

import pytest

from emotional_model_fls import labels
from emotional_model_fls.example_specs import DEFAULT_SPECS
from emotional_model_fls.fuzzy_engine import VariableSpec, tri


@pytest.mark.parametrize("mapper", [
    labels.map_mood,
    labels.map_alertness,
    labels.map_interest,
    labels.map_affective,
    labels.map_expectancy,
    labels.map_general_state,
    pytest.param(partial(labels.map_from_spec, spec=DEFAULT_SPECS.MOOD), id="map_from_spec"),
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_label_mappers_reject_non_finite_values(mapper, value):
    with pytest.raises(ValueError, match="must be finite"):
        mapper(value)


@pytest.mark.parametrize("value, expected", [
    (0, "low"),
    (2.5, "low"),
    (7.5, "high"),
    (10, "high"),
])
def test_finite_values_keep_their_membership_label(value, expected):
    spec = VariableSpec(
        key="test_value",
        control_name="test_value",
        universe=(0, 11),
        terms=(tri("low", 0, 0, 10), tri("high", 0, 10, 10)),
    )
    assert labels.map_from_spec(value, spec) == expected
