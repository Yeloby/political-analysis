import hashlib
import json
from pathlib import Path
from typing import Any

from .config import CACHE_DIR


class JsonCache:
    def __init__(self, root: Path = CACHE_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(namespace: str, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        return f"{namespace}-{digest}.json"

    def get(self, namespace: str, payload: Any):
        path = self.root / self._key(namespace, payload)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, namespace: str, payload: Any, value: Any):
        path = self.root / self._key(namespace, payload)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
