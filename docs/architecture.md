# Architecture

This repository publishes a framework around a fuzzy-logic emotional model. The
engine and runtime are public; calibrated rules and membership values are meant
to live in private configuration files.

## Runtime Flow

1. Receive optional sensor updates through `SensorInputs` or CLI flags.
2. Validate sensor ranges.
3. Derive aggregate inputs such as antenna activity, button state and event
   frequencies.
4. Build fuzzy controllers from the loaded spec bundle.
5. Run internal states in dependency order: alertness, interest, mood,
   affective and expectancy.
6. Run expression controllers: heartbeat, body speed and general state.
7. Return numeric values and labels in a `ModelOutputs` object.

## Public Modules

- `fuzzy_engine.py`: small wrappers around `scikit-fuzzy` variables, rules and
  simulations.
- `config_loader.py`: converts YAML/JSON-compatible model configs into runtime
  specs.
- `example_specs.py`: loads the bundled toy model.
- `state.py`: internal state controllers.
- `expressions.py`: externally visible expression controllers.
- `runtime.py`: high-level API for one-step or continuous execution.
- `cli.py`: command-line entrypoint.

## Public Diagram

The model architecture diagram in `docs/ray_emotional_model.pdf` is included
because the architecture is public. The numeric configuration behind the private
model is not included.
