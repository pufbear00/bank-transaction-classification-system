"""Local-only settings. Deliberately ignores environment and .env files."""
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
_local_dir = _backend_dir / ".local"


class Settings:
    DATABASE_URL = f"sqlite+aiosqlite:///{_local_dir / 'bank-demo.sqlite3'}"
    UPLOAD_DIR = str(_local_dir / "uploads")
    cors_origins_list = ["http://127.0.0.1:5193", "http://localhost:5193"]
    OFFLINE_DEMO = True


settings = Settings()
