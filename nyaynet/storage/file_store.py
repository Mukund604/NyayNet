"""Local file storage for evidence artifacts."""

import shutil
from pathlib import Path

from config.logging_config import get_logger

log = get_logger(__name__)


class FileStore:
    """Manages local file storage for evidence artifacts."""

    def __init__(self, base_dir: str = "data/evidence"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, username: str) -> Path:
        user_dir = self._base_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def save_screenshot(self, username: str, filename: str, data: bytes) -> str:
        """Save a screenshot and return the file path."""
        user_dir = self._get_user_dir(username)
        file_path = user_dir / filename
        file_path.write_bytes(data)
        log.info("screenshot_saved", path=str(file_path))
        return str(file_path)

    def save_report(self, username: str, filename: str, data: bytes) -> str:
        """Save a PDF report and return the file path."""
        user_dir = self._get_user_dir(username)
        file_path = user_dir / filename
        file_path.write_bytes(data)
        log.info("report_saved", path=str(file_path))
        return str(file_path)

    def save_file(self, username: str, filename: str, data: bytes) -> str:
        """Save an arbitrary file and return the file path."""
        user_dir = self._get_user_dir(username)
        file_path = user_dir / filename
        file_path.write_bytes(data)
        return str(file_path)

    def get_file(self, file_path: str) -> bytes | None:
        """Read a file by path."""
        path = Path(file_path)
        if path.exists():
            return path.read_bytes()
        return None

    def list_files(self, username: str) -> list[str]:
        """List all files for a user."""
        user_dir = self._get_user_dir(username)
        return [str(f) for f in user_dir.iterdir() if f.is_file()]

    def delete_user_files(self, username: str) -> None:
        """Delete all files for a user."""
        user_dir = self._base_dir / username
        if user_dir.exists():
            shutil.rmtree(user_dir)
            log.info("user_files_deleted", username=username)
