import os
import tempfile

# 必须在导入 app.* 之前指定独立数据目录，避免污染开发库
_TMP = tempfile.mkdtemp(prefix="ladderbill-test-")
os.environ["DATA_DIR"] = _TMP

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
