from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import TachyonError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    root: Path
    data_dir: Path
    ui_origin: str = "http://127.0.0.1:8000"

    def __post_init__(self):
        self.root = self.root.resolve()
        self.data_dir = self.data_dir.resolve()
        if not self.data_dir.is_relative_to(self.root):
            raise ValueError("Local data directory must be inside the project")
        parsed = urlparse(self.ui_origin)
        if parsed.scheme not in ("http", "https") or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("UI origin must be a local HTTP origin")
        host = parsed.hostname or ""
        if host != "localhost" and not host.endswith(".local"):
            address = ipaddress.ip_address(host)
            if not (address.is_private or address.is_loopback) or address.is_unspecified:
                raise ValueError("Public CAD hosting is unavailable")
        self.ui_origin = self.ui_origin.rstrip("/")

    @classmethod
    def environment(cls):
        profile = os.getenv("TACHYON_CAD_PROFILE", "user_provided_local")
        if profile != "user_provided_local":
            raise ValueError("Only the user_provided_local CAD profile is supported")
        return cls(PROJECT_ROOT, PROJECT_ROOT / os.getenv("TACHYON_DATA_DIR", ".local"),
                   os.getenv("TACHYON_UI_ORIGIN", "http://127.0.0.1:8000"))

    def local_path(self, value: str, *, must_exist: bool = True) -> Path:
        path = Path(value)
        if path.is_absolute():
            candidate = path.resolve()
        else:
            candidate = (self.data_dir / path).resolve()
        if not candidate.is_relative_to(self.data_dir):
            raise TachyonError("INVALID_LOCAL_PATH", "The supplied file must be inside the local data directory")
        if must_exist and not candidate.is_file():
            raise TachyonError("LOCAL_FILE_MISSING", "A required local input is missing")
        return candidate
