"""Reusable helpers for building scikit-fuzzy controllers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import reduce
from operator import and_

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


@dataclass(frozen=True)
class TermSpec:
    name: str
    kind: str
    points: tuple[float, ...]


@dataclass(frozen=True)
class VariableSpec:
    key: str
    control_name: str
    universe: tuple[int, int]
    terms: tuple[TermSpec, ...]


@dataclass(frozen=True)
class RuleSpec:
    conditions: tuple[tuple[str, str], ...]
    output: str


def trap(name: str, *points: float) -> TermSpec:
    return TermSpec(name=name, kind="trap", points=tuple(points))


def tri(name: str, *points: float) -> TermSpec:
    return TermSpec(name=name, kind="tri", points=tuple(points))


def rule(conditions: Sequence[tuple[str, str]], output: str) -> RuleSpec:
    return RuleSpec(conditions=tuple(conditions), output=output)


def rules_from_table(
    dimensions: Sequence[tuple[str, Sequence[str]]],
    table: Sequence,
) -> tuple[RuleSpec, ...]:
    """Create rules from a nested table ordered like the given dimensions."""

    generated: list[RuleSpec] = []

    def walk(depth: int, prefix: list[tuple[str, str]], node: Sequence | str) -> None:
        key, terms = dimensions[depth]
        if depth == len(dimensions) - 1:
            for term, output in zip(terms, node, strict=True):
                generated.append(rule([*prefix, (key, term)], output))
            return

        for term, child in zip(terms, node, strict=True):
            walk(depth + 1, [*prefix, (key, term)], child)

    walk(0, [], table)
    return tuple(generated)


def make_antecedent(spec: VariableSpec) -> ctrl.Antecedent:
    variable = ctrl.Antecedent(np.arange(*spec.universe, 1), spec.control_name)
    _add_terms(variable, spec)
    return variable


def make_consequent(spec: VariableSpec) -> ctrl.Consequent:
    variable = ctrl.Consequent(np.arange(*spec.universe, 1), spec.control_name)
    _add_terms(variable, spec)
    return variable


def build_simulation(
    inputs: Sequence[VariableSpec],
    output: VariableSpec,
    rules: Iterable[RuleSpec],
) -> ctrl.ControlSystemSimulation:
    return ctrl.ControlSystemSimulation(build_control_system(inputs, output, rules))


def build_control_system(
    inputs: Sequence[VariableSpec],
    output: VariableSpec,
    rules: Iterable[RuleSpec],
) -> ctrl.ControlSystem:
    antecedents = {spec.key: make_antecedent(spec) for spec in inputs}
    consequent = make_consequent(output)
    control_rules = [
        ctrl.Rule(_combine_terms(antecedents, spec.conditions), consequent[spec.output])
        for spec in rules
    ]
    return ctrl.ControlSystem(control_rules)


def assign_inputs(
    simulation: ctrl.ControlSystemSimulation,
    specs: Mapping[str, VariableSpec],
    values: Mapping[str, float],
) -> None:
    for key, value in values.items():
        simulation.input[specs[key].control_name] = value


def spec_map(specs: Sequence[VariableSpec]) -> dict[str, VariableSpec]:
    return {spec.key: spec for spec in specs}


def compute_delayed_feedback(
    simulation: ctrl.ControlSystemSimulation,
    feedback_spec: VariableSpec,
    output_key: str,
    current_base: float,
    delay_const: float,
) -> tuple[float, float]:
    raw_output = simulation.output[output_key]
    delayed = (current_base * delay_const + raw_output) / (delay_const + 1)
    simulation.input[feedback_spec.control_name] = delayed
    return raw_output, delayed


def _add_terms(variable: ctrl.Antecedent | ctrl.Consequent, spec: VariableSpec) -> None:
    universe = np.arange(*spec.universe, 1)
    for term in spec.terms:
        if term.kind == "trap":
            variable[term.name] = fuzz.trapmf(universe, term.points)
        elif term.kind == "tri":
            variable[term.name] = fuzz.trimf(universe, term.points)
        else:
            raise ValueError(f"Unsupported membership function: {term.kind}")


def _combine_terms(
    variables: Mapping[str, ctrl.Antecedent],
    conditions: Sequence[tuple[str, str]],
):
    selected_terms = [variables[key][term] for key, term in conditions]
    return reduce(and_, selected_terms)
