import json
from pathlib import Path

import pytest


@pytest.fixture
def demo_config():
    return json.loads(Path("examples/toy_emotional_model.yaml").read_text())
