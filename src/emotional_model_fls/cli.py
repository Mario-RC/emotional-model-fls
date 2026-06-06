"""Command-line interface for the emotional model."""

from __future__ import annotations

import argparse
import logging
from typing import Any

from emotional_model_fls.sensors import SENSOR_FIELDS, SensorInputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fuzzy emotional model.")
    parser.add_argument("--steps", type=int, default=1, help="Number of model steps to run.")
    parser.add_argument("--forever", action="store_true", help="Run until interrupted.")
    parser.add_argument("--interval", type=float, default=0.1, help="Seconds between steps.")
    parser.add_argument("--config", default=None, help="Path to a custom fuzzy-model config.")
    parser.add_argument("--log-level", default="WARNING", help="Python logging level.")
    parser.add_argument("--no-json", action="store_true", help="Print compact human output.")
    for field in SENSOR_FIELDS:
        parser.add_argument(f"--{field.replace('_', '-')}", type=float, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.WARNING))

    updates: dict[str, Any] = {
        field: getattr(args, field)
        for field in SENSOR_FIELDS
        if getattr(args, field) is not None
    }

    try:
        from emotional_model_fls.runtime import EmotionalModel
    except ModuleNotFoundError as exc:
        if exc.name == "skfuzzy":
            parser.error(
                "missing dependency 'scikit-fuzzy'. Install the project with "
                '`python -m pip install -e ".[dev]"` or install requirements.txt.'
            )
        raise

    model = EmotionalModel(config_path=args.config)
    if updates:
        model.apply_inputs(SensorInputs(**updates))

    steps = None if args.forever else args.steps
    try:
        if args.no_json:
            _run_human(model, steps=steps, interval=args.interval)
        else:
            model.run(interval=args.interval, steps=steps, print_outputs=True)
    except KeyboardInterrupt:
        return 130
    return 0


def _run_human(model, steps: int | None, interval: float) -> None:
    import time

    count = 0
    while steps is None or count < steps:
        outputs = model.step()
        print(
            f"state={outputs.general_state} "
            f"heartbeat={outputs.heartbeat:.2f} "
            f"body_speed={outputs.body_speed:.2f}"
        )
        count += 1
        if steps is None or count < steps:
            time.sleep(interval)
