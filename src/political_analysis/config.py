from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "political-analysis"
DATA_DIR = Path(user_data_dir(APP_NAME))
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "political.duckdb"

for path in (DATA_DIR, CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)
