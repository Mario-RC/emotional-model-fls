"""Load fuzzy-model specifications from a public-safe config file.

The loader supports two rule styles:

- ``table``: a fully expanded nested table, useful for small examples.
- ``default`` + ``overrides``: a compact public format that avoids shipping
  large proprietary rule matrices.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from emotional_model_fls.fuzzy_engine import RuleSpec, VariableSpec, rule, rules_from_table


class ConfigError(ValueError):
    """Raised when a fuzzy-model config is malformed."""


def load_spec_bundle(source: str | Path | Mapping[str, Any] | Any) -> SimpleNamespace:
    """Load a complete fuzzy-model spec bundle from a path or mapping."""

    config = _read_config(source)
    variables = _build_variables(config)
    rules = _build_rule_sets(config, variables)

    attributes: dict[str, Any] = {
        "variables": variables,
        "rules": rules,
        "config": config,
    }
    attributes.update({_constant_name(name): spec for name, spec in variables.items()})
    attributes.update({f"{_constant_name(name)}_RULES": specs for name, specs in rules.items()})
    return SimpleNamespace(**attributes)


def _read_config(source: str | Path | Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source

    text: str
    if hasattr(source, "read_text") and not isinstance(source, (str, Path)):
        text = source.read_text(encoding="utf-8")
    else:
        text = Path(source).read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "PyYAML is required for non-JSON YAML files. Install the optional "
                "config dependency or keep the config in JSON-compatible YAML."
            ) from exc

    else:
        data = yaml.safe_load(text)
    if not isinstance(data, Mapping):
        raise ConfigError("Config root must be a mapping.")
    return data


def _build_variables(config: Mapping[str, Any]) -> dict[str, VariableSpec]:
    raw_variables = _require_mapping(config, "variables")
    variables = {
        key: _build_variable(key, raw_spec)
        for key, raw_spec in raw_variables.items()
    }

    for alias_key, raw_alias in config.get("input_aliases", {}).items():
        if not isinstance(raw_alias, Mapping):
            raise ConfigError(f"input_aliases.{alias_key} must be a mapping.")
        source = _require_string(raw_alias, "source", f"input_aliases.{alias_key}")
        control_name = _require_string(raw_alias, "control_name", f"input_aliases.{alias_key}")
        try:
            base = variables[source]
        except KeyError as exc:
            raise ConfigError(f"Unknown alias source: {source}") from exc
        variables[alias_key] = VariableSpec(
            key=source,
            control_name=control_name,
            universe=base.universe,
            terms=base.terms,
        )

    return variables


def _build_variable(key: str, raw_spec: Any) -> VariableSpec:
    if not isinstance(raw_spec, Mapping):
        raise ConfigError(f"variables.{key} must be a mapping.")

    universe = raw_spec.get("universe")
    if not _is_number_pair(universe):
        raise ConfigError(f"variables.{key}.universe must be a two-item numeric list.")
    if any(value != int(value) for value in universe) or universe[1] - universe[0] < 2:
        raise ConfigError(f"variables.{key}.universe needs integer bounds spanning at least two samples.")

    raw_terms = raw_spec.get("terms")
    if not isinstance(raw_terms, Sequence) or isinstance(raw_terms, (str, bytes)) or not raw_terms:
        raise ConfigError(f"variables.{key}.terms must be a non-empty list.")

    terms = []
    for index, raw_term in enumerate(raw_terms):
        if not isinstance(raw_term, Mapping):
            raise ConfigError(f"variables.{key}.terms[{index}] must be a mapping.")
        name = _require_string(raw_term, "name", f"variables.{key}.terms[{index}]")
        kind = _require_string(raw_term, "kind", f"variables.{key}.terms[{index}]")
        points = raw_term.get("points")
        if not isinstance(points, Sequence) or isinstance(points, (str, bytes)):
            raise ConfigError(f"variables.{key}.terms[{index}].points must be a list.")
        if not all(_is_finite_number(point) for point in points):
            raise ConfigError(f"variables.{key}.terms[{index}].points must contain finite numbers.")
        terms.append((name, kind, tuple(float(point) for point in points)))

    return VariableSpec(
        key=key,
        control_name=str(raw_spec.get("control_name", key)),
        universe=(int(universe[0]), int(universe[1])),
        terms=tuple(
            _term_spec(name=name, kind=kind, points=points)
            for name, kind, points in terms
        ),
    )


def _build_rule_sets(
    config: Mapping[str, Any],
    variables: Mapping[str, VariableSpec],
) -> dict[str, tuple[RuleSpec, ...]]:
    raw_rules = _require_mapping(config, "rules")
    return {
        key: _build_rules(key, raw_spec, variables)
        for key, raw_spec in raw_rules.items()
    }


def _build_rules(
    name: str,
    raw_spec: Any,
    variables: Mapping[str, VariableSpec],
) -> tuple[RuleSpec, ...]:
    if not isinstance(raw_spec, Mapping):
        raise ConfigError(f"rules.{name} must be a mapping.")

    output_key = _require_string(raw_spec, "output", f"rules.{name}")
    if output_key not in variables:
        raise ConfigError(f"rules.{name}.output references unknown variable {output_key!r}.")
    output_terms = {term.name for term in variables[output_key].terms}

    dimensions = _parse_dimensions(name, raw_spec, variables)
    if "table" in raw_spec:
        rules = rules_from_table(dimensions, raw_spec["table"])
    elif "default" in raw_spec:
        rules = _rules_from_default_and_overrides(name, raw_spec, dimensions)
    elif "items" in raw_spec:
        rules = _rules_from_items(name, raw_spec["items"], dimensions)
    else:
        raise ConfigError(f"rules.{name} needs one of: table, default, items.")

    for spec in rules:
        if spec.output not in output_terms:
            raise ConfigError(
                f"rules.{name} emits {spec.output!r}, but {output_key!r} has no such term."
            )
    return tuple(rules)


def _parse_dimensions(
    name: str,
    raw_spec: Mapping[str, Any],
    variables: Mapping[str, VariableSpec],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    raw_dimensions = raw_spec.get("dimensions")
    if not isinstance(raw_dimensions, Sequence) or isinstance(raw_dimensions, (str, bytes)):
        raise ConfigError(f"rules.{name}.dimensions must be a list.")

    parsed = []
    for index, item in enumerate(raw_dimensions):
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) != 2:
            raise ConfigError(f"rules.{name}.dimensions[{index}] must be [variable, terms].")
        key = str(item[0])
        if key not in variables:
            raise ConfigError(f"rules.{name} references unknown variable {key!r}.")
        if key in dict(parsed):
            raise ConfigError(f"rules.{name} repeats dimension {key!r}.")
        if not isinstance(item[1], Sequence) or isinstance(item[1], (str, bytes)) or not item[1]:
            raise ConfigError(f"rules.{name}.dimensions[{index}] needs a non-empty term list.")
        terms = tuple(str(term) for term in item[1])
        known_terms = {term.name for term in variables[key].terms}
        missing = sorted(set(terms) - known_terms)
        if missing:
            raise ConfigError(f"rules.{name} references unknown terms for {key}: {missing}")
        parsed.append((key, terms))
    return tuple(parsed)


def _rules_from_default_and_overrides(
    name: str,
    raw_spec: Mapping[str, Any],
    dimensions: Sequence[tuple[str, Sequence[str]]],
) -> tuple[RuleSpec, ...]:
    default_output = _require_string(raw_spec, "default", f"rules.{name}")
    outputs: dict[tuple[tuple[str, str], ...], str] = {
        tuple((key, term) for (key, _), term in zip(dimensions, terms, strict=True)): default_output
        for terms in product(*(terms for _, terms in dimensions))
    }

    raw_overrides = raw_spec.get("overrides", ())
    if not isinstance(raw_overrides, Sequence) or isinstance(raw_overrides, (str, bytes)):
        raise ConfigError(f"rules.{name}.overrides must be a list.")
    for index, override in enumerate(raw_overrides):
        if not isinstance(override, Mapping):
            raise ConfigError(f"rules.{name}.overrides[{index}] must be a mapping.")
        output = _require_string(override, "then", f"rules.{name}.overrides[{index}]")
        raw_when = _require_mapping(override, "when")
        _validate_conditions(name, raw_when, dimensions, allow_wildcards=True)
        for conditions in _expand_conditions(dimensions, raw_when):
            outputs[conditions] = output

    return tuple(rule(conditions, output) for conditions, output in outputs.items())


def _rules_from_items(
    name: str, raw_items: Any, dimensions: Sequence[tuple[str, Sequence[str]]],
) -> tuple[RuleSpec, ...]:
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
        raise ConfigError(f"rules.{name}.items must be a list.")

    rules = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            raise ConfigError(f"rules.{name}.items[{index}] must be a mapping.")
        raw_when = _require_mapping(item, "when")
        _validate_conditions(name, raw_when, dimensions, allow_wildcards=False)
        output = _require_string(item, "then", f"rules.{name}.items[{index}]")
        rules.append(rule(tuple((str(key), str(value)) for key, value in raw_when.items()), output))
    return tuple(rules)


def _validate_conditions(
    name: str,
    raw_when: Mapping[str, Any],
    dimensions: Sequence[tuple[str, Sequence[str]]],
    *,
    allow_wildcards: bool,
) -> None:
    known = dict(dimensions)
    unknown = set(raw_when) - set(known)
    if unknown:
        raise ConfigError(f"rules.{name}.when references unknown dimensions: {sorted(map(str, unknown))}")
    if not raw_when and not allow_wildcards:
        raise ConfigError(f"rules.{name}.when needs at least one condition.")
    for key, value in raw_when.items():
        if value is None and allow_wildcards:
            continue
        if isinstance(value, str):
            selected = [value]
        elif allow_wildcards and isinstance(value, Sequence) and not isinstance(value, bytes):
            selected = value
        else:
            raise ConfigError(f"rules.{name}.when.{key} has an invalid term selection.")
        if not selected or any(not isinstance(term, str) or term not in known[key] for term in selected):
            raise ConfigError(f"rules.{name}.when.{key} references unknown or empty terms.")


def _expand_conditions(
    dimensions: Sequence[tuple[str, Sequence[str]]],
    raw_when: Mapping[str, Any],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    choices: list[tuple[str, tuple[str, ...]]] = []
    for key, terms in dimensions:
        raw_value = raw_when.get(key)
        if raw_value is None:
            choices.append((key, tuple(terms)))
        elif isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes)):
            choices.append((key, tuple(str(value) for value in raw_value)))
        else:
            choices.append((key, (str(raw_value),)))

    return tuple(
        tuple((key, term) for (key, _), term in zip(choices, selected_terms, strict=True))
        for selected_terms in product(*(terms for _, terms in choices))
    )


def _require_mapping(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise ConfigError(f"{key} must be a mapping.")
    return value


def _require_string(mapping: Mapping[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{context}.{key} must be a non-empty string.")
    return value


def _is_number_pair(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == 2
        and all(_is_finite_number(item) for item in value)
    )


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _constant_name(name: str) -> str:
    return name.upper()


def _term_spec(name: str, kind: str, points: tuple[float, ...]):
    from emotional_model_fls.fuzzy_engine import TermSpec

    if kind not in {"tri", "trap"}:
        raise ConfigError(f"Unsupported membership function: {kind}")
    expected_points = 3 if kind == "tri" else 4
    if len(points) != expected_points:
        raise ConfigError(f"{kind!r} membership functions need {expected_points} points.")
    if points[0] >= points[-1] or any(left > right for left, right in zip(points, points[1:], strict=False)):
        raise ConfigError(f"Membership function {name!r} needs ordered points with a non-zero span.")
    return TermSpec(name=name, kind=kind, points=points)
