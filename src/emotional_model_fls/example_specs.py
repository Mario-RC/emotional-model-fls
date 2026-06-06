"""Public demo fuzzy specs.

These values are intentionally synthetic. They make the framework executable
out of the box without publishing the private model configuration.
"""

from __future__ import annotations

from importlib.resources import files

from emotional_model_fls.config_loader import load_spec_bundle

DEFAULT_CONFIG_RESOURCE = files(__package__).joinpath("example_specs.yaml")
DEFAULT_SPECS = load_spec_bundle(DEFAULT_CONFIG_RESOURCE)

for _name, _value in vars(DEFAULT_SPECS).items():
    if _name.isupper():
        globals()[_name] = _value

__all__ = [
    "DEFAULT_CONFIG_RESOURCE",
    "DEFAULT_SPECS",
    *sorted(name for name in globals() if name.isupper()),
]
