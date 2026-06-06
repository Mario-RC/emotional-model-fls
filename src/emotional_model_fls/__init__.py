"""Emotional Model FLS package."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "EmotionalModel",
    "FuzzyLogic",
    "load_spec_bundle",
    "ModelOutputs",
    "SensorInputs",
]


def __getattr__(name: str):
    if name == "FuzzyLogic":
        from emotional_model_fls.fuzzy_logic import FuzzyLogic

        return FuzzyLogic
    if name == "load_spec_bundle":
        from emotional_model_fls.config_loader import load_spec_bundle

        return load_spec_bundle
    if name == "SensorInputs":
        from emotional_model_fls.sensors import SensorInputs

        return SensorInputs
    if name in {"EmotionalModel", "ModelOutputs"}:
        from emotional_model_fls.runtime import EmotionalModel, ModelOutputs

        return {
            "EmotionalModel": EmotionalModel,
            "ModelOutputs": ModelOutputs,
        }[name]
    raise AttributeError(name)
