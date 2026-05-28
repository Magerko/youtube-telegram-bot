import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def storage(tmp_path: Path):
    from services.storage import Storage
    return Storage(tmp_path / "pydata")
