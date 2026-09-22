import shutil
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "samfunnsdata"
DATA_DIR = Path(user_data_dir(APP_NAME))
LEGACY_DATA_DIR = Path(user_data_dir("political-analysis"))

# Preserve existing caches and any database created by earlier versions.
# Keep the legacy directory as a backup rather than deleting user data.
if LEGACY_DATA_DIR.is_dir() and not DATA_DIR.exists():
    shutil.copytree(LEGACY_DATA_DIR, DATA_DIR)

CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "samfunnsdata.duckdb"
LEGACY_DB_PATH = DATA_DIR / "political.duckdb"

if LEGACY_DB_PATH.is_file() and not DB_PATH.exists():
    shutil.copy2(LEGACY_DB_PATH, DB_PATH)

for path in (DATA_DIR, CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)
