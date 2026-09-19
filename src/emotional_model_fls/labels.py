"""Numeric-to-label mappings for loaded fuzzy specs."""

from __future__ import annotations

from math import isfinite
from typing import Any

from emotional_model_fls.example_specs import DEFAULT_SPECS
from emotional_model_fls.fuzzy_engine import TermSpec, VariableSpec


def _require_non_negative(value: float, name: str) -> float:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value!r}")
    return value


def map_from_spec(value: float, spec: VariableSpec, name: str | None = None) -> str:
    """Return the strongest membership label for a loaded variable spec."""

    value = _require_non_negative(value, name or spec.key)
    scores = [(term.name, _membership(value, term), _center(term)) for term in spec.terms]
    best_name, best_score, _ = max(scores, key=lambda item: (item[1], -abs(value - item[2])))
    if best_score > 0:
        return best_name
    return min(scores, key=lambda item: abs(value - item[2]))[0]


def map_mood(value: float, specs: Any | None = None) -> str:
    value = _require_non_negative(value, "mood")
    return map_from_spec(value, (specs or DEFAULT_SPECS).MOOD, "mood")


def map_alertness(value: float, specs: Any | None = None) -> str:
    value = _require_non_negative(value, "alertness")
    return map_from_spec(value, (specs or DEFAULT_SPECS).ALERTNESS, "alertness")


def map_interest(value: float, specs: Any | None = None) -> str:
    value = _require_non_negative(value, "interest")
    return map_from_spec(value, (specs or DEFAULT_SPECS).INTEREST, "interest")


def map_affective(value: float, specs: Any | None = None) -> str:
    value = _require_non_negative(value, "affective")
    return map_from_spec(value, (specs or DEFAULT_SPECS).AFFECTIVE, "affective")


def map_expectancy(value: float, specs: Any | None = None) -> str:
    value = _require_non_negative(value, "expectancy")
    return map_from_spec(value, (specs or DEFAULT_SPECS).EXPECTANCY, "expectancy")


def map_general_state(value: float, specs: Any | None = None) -> str:
    value = _require_non_negative(value, "general_state")
    return map_from_spec(value, (specs or DEFAULT_SPECS).GENERAL_STATE, "general_state")


def _membership(value: float, term: TermSpec) -> float:
    if term.kind == "tri":
        left, peak, right = term.points
        if value == peak:
            return 1.0
        if value <= left or value >= right:
            return 0.0
        if value < peak:
            return _ratio(value - left, peak - left)
        return _ratio(right - value, right - peak)

    left, left_top, right_top, right = term.points
    if left_top <= value <= right_top:
        return 1.0
    if value <= left or value >= right:
        return 0.0
    if value < left_top:
        return _ratio(value - left, left_top - left)
    return _ratio(right - value, right - right_top)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    return max(0.0, min(1.0, numerator / denominator))


def _center(term: TermSpec) -> float:
    return sum(term.points) / len(term.points)
