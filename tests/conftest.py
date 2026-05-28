"""Общие фикстуры pytest."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Чтобы тесты могли импортировать модули проекта без install.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def storage(tmp_path: Path):
    """Свежий Storage в изолированной временной папке."""
    from services.storage import Storage
    return Storage(tmp_path / "pydata")
