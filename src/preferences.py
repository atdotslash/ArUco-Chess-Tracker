"""User preferences persistence and schema management with corruption tolerance."""

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from src.config import DEFAULT_PREFERENCES
from src.utils.paths import get_config_file_path

logger = logging.getLogger(__name__)


class Preferences:
    """Manages reading, writing, and validating user configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path: Path = config_path or get_config_file_path()
        self._data: Dict[str, Any] = copy.deepcopy(DEFAULT_PREFERENCES)
        self.load()

    def load(self) -> None:
        """Load configuration from disk. If missing or corrupted, load defaults."""
        if not self.config_path.exists():
            logger.info("Config file not found at %s. Using default preferences.", self.config_path)
            self._data = copy.deepcopy(DEFAULT_PREFERENCES)
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                raise ValueError("Config root is not a dictionary.")
            self._merge_defaults(loaded)
        except Exception as e:
            logger.warning(
                "Error reading preferences from %s: %s. Falling back to defaults.",
                self.config_path,
                e,
            )
            # Create a backup of the corrupted file for safety
            try:
                corrupted_backup = self.config_path.with_suffix(".json.bak")
                if self.config_path.exists():
                    os.replace(self.config_path, corrupted_backup)
                    logger.info("Corrupted config backed up to %s", corrupted_backup)
            except Exception as backup_err:
                logger.error("Failed to backup corrupted config: %s", backup_err)

            self._data = copy.deepcopy(DEFAULT_PREFERENCES)
            self.save()

    def _merge_defaults(self, loaded: Dict[str, Any]) -> None:
        """Deeply merge loaded data over default values to ensure all keys exist."""
        merged = copy.deepcopy(DEFAULT_PREFERENCES)
        for section, values in loaded.items():
            if section in merged and isinstance(merged[section], dict) and isinstance(values, dict):
                merged[section].update(values)
            else:
                merged[section] = values
        self._data = merged

    def save(self) -> bool:
        """Atomically persist current preferences to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.config_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.config_path)
            return True
        except Exception as e:
            logger.error("Failed to save preferences to %s: %s", self.config_path, e)
            return False

    def reset_to_defaults(self) -> None:
        """Reset all configuration values to defaults and save."""
        self._data = copy.deepcopy(DEFAULT_PREFERENCES)
        self.save()

    def get(self, section: str, key: str | None = None, default: Any = None) -> Any:
        """Retrieve a section or specific key within a section."""
        if section not in self._data:
            return default
        if key is None:
            return self._data[section]
        return self._data[section].get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Update a key in a section."""
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value

    def get_marker_mapping(self) -> Dict[int, str]:
        """Return marker ID -> chess piece mapping with integer keys."""
        raw = self.get("marker_mapping", default={})
        mapping: Dict[int, str] = {}
        for k, v in raw.items():
            try:
                mapping[int(k)] = str(v)
            except (ValueError, TypeError):
                continue
        return mapping

    def set_marker_mapping(self, mapping: Dict[int, str]) -> None:
        """Save marker ID -> chess piece mapping."""
        self._data["marker_mapping"] = {str(k): str(v) for k, v in mapping.items()}

    @property
    def data(self) -> Dict[str, Any]:
        """Direct access to preferences data copy."""
        return copy.deepcopy(self._data)
