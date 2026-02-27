from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "linamp"
CONFIG_PATH = CONFIG_DIR / "config.json"
QUEUE_PATH = CONFIG_DIR / "queue.json"


@dataclass
class AppConfig:
    """Application-wide configuration."""

    music_root: str = "~/Music"

    @property
    def music_root_path(self) -> Path:
        """Return music_root as an expanded Path."""
        return Path(self.music_root).expanduser()


def load_config() -> AppConfig:
    """Load config from disk, returning defaults if missing or invalid."""
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})
        except Exception as exc:
            log.warning("Failed to load config from %s: %s", CONFIG_PATH, exc)
    return AppConfig()


def save_config(config: AppConfig) -> None:
    """Persist config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(config), indent=2) + "\n")
