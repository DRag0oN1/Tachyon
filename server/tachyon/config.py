from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import TachyonError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_SOURCE_BYTES = 256 * 1024 * 1024


@dataclass
class Settings:
    root: Path
    data_dir: Path
    ui_origin: str = "http://127.0.0.1:8000"
    cad_dir: Path | None = None
    rights_dir: Path | None = None

    def __post_init__(self):
        self.root = Path(self.root).expanduser().resolve()
        self.data_dir = Path(self.data_dir).expanduser().resolve()
        if self.data_dir == self.root or not self.data_dir.is_relative_to(self.root):
            raise ValueError("Local data directory must be inside the project")
        for field in ("cad_dir", "rights_dir"):
            value = getattr(self, field)
            if value is None:
                continue
            lexical = Path(os.path.abspath(Path(value).expanduser()))
            resolved = lexical.resolve()
            for path in (lexical, resolved):
                if ((path.is_relative_to(self.root) and not path.is_relative_to(self.data_dir))
                        or self.root.is_relative_to(path)):
                    raise ValueError("External CAD and rights roots must be outside the public project or inside private data")
            setattr(self, field, resolved)
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
        return cls(PROJECT_ROOT, PROJECT_ROOT / Path(os.getenv("TACHYON_DATA_DIR", ".local")).expanduser(),
                   os.getenv("TACHYON_UI_ORIGIN", "http://127.0.0.1:8000"),
                   Path(os.getenv("TACHYON_CAD_DIR", "~/Documents/TachyonCAD/step")).expanduser(),
                   Path(os.getenv("TACHYON_RIGHTS_DIR", "~/Documents/TachyonCAD/rights")).expanduser())

    def local_path(self, value: str, *, must_exist: bool = True) -> Path:
        return self._role_path(value, {"data": self.data_dir}, must_exist)

    def source_path(self, value: str, *, must_exist: bool = True) -> Path:
        """Originals: private data or the explicitly configured CAD root only."""
        return self._role_path(value, {"data": self.data_dir, "cad": self.cad_dir}, must_exist)

    def rights_path(self, value: str, *, must_exist: bool = True) -> Path:
        """Catalogs, permission manifests and evidence never use the CAD root."""
        return self._role_path(value, {"data": self.data_dir, "rights": self.rights_dir}, must_exist)

    def _role_path(self, value, roots, must_exist):
        # Unprefixed relative paths retain their historical data_dir meaning.
        # A symlink must remain within its own selected root, even if its target
        # happens to be in another otherwise allowed root.
        try:
            value = os.fspath(value)
            prefix, separator, tail = value.partition(":")
            if separator and prefix in ("data", "cad", "rights"):
                root = roots.get(prefix)
                if root is None or not tail or Path(tail).is_absolute():
                    raise ValueError()
                lexical = Path(os.path.abspath(root / tail))
            else:
                path = Path(value).expanduser()
                lexical = Path(os.path.abspath(path if path.is_absolute() else self.data_dir / path))
                root = next((r for r in roots.values() if r is not None and lexical.is_relative_to(r)), None)
            if root is None or not lexical.is_relative_to(root):
                raise ValueError()
            candidate = lexical.resolve()
            if not candidate.is_relative_to(root):
                raise ValueError()
            if must_exist and not candidate.is_file():
                raise TachyonError("LOCAL_FILE_MISSING", "A required local input is missing")
            return candidate
        except (ValueError, TypeError, OSError, RuntimeError):
            raise TachyonError("INVALID_LOCAL_PATH", "The supplied path must remain inside its configured private root") from None
