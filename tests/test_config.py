import os
import subprocess
import sys
from pathlib import Path


def test_legacy_data_is_copied_to_new_directory(tmp_path: Path):
    legacy = tmp_path / "political-analysis"
    legacy_cache = legacy / "cache"
    legacy_cache.mkdir(parents=True)
    (legacy_cache / "cached.json").write_text("{}", encoding="utf-8")
    (legacy / "political.duckdb").write_bytes(b"database")

    environment = os.environ.copy()
    environment["XDG_DATA_HOME"] = str(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from samfunnsdata.config import CACHE_DIR, DB_PATH; "
                "print(CACHE_DIR); print(DB_PATH)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    new = tmp_path / "samfunnsdata"
    assert result.stdout.splitlines() == [
        str(new / "cache"),
        str(new / "samfunnsdata.duckdb"),
    ]
    assert (new / "cache" / "cached.json").read_text() == "{}"
    assert (new / "samfunnsdata.duckdb").read_bytes() == b"database"
    assert (legacy / "political.duckdb").read_bytes() == b"database"


def test_existing_new_data_directory_is_not_overwritten(tmp_path: Path):
    legacy = tmp_path / "political-analysis"
    current = tmp_path / "samfunnsdata"
    legacy.mkdir()
    current.mkdir()
    (legacy / "marker").write_text("legacy", encoding="utf-8")
    (current / "marker").write_text("current", encoding="utf-8")

    environment = os.environ.copy()
    environment["XDG_DATA_HOME"] = str(tmp_path)

    subprocess.run(
        [sys.executable, "-c", "import samfunnsdata.config"],
        check=True,
        env=environment,
    )

    assert (current / "marker").read_text(encoding="utf-8") == "current"
