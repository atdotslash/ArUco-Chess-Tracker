"""Cross-platform path resolution for assets, calibration, and configuration."""

import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Return the base directory for the application.

    Handles PyInstaller frozen environments (sys._MEIPASS) and source trees.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # When running from source, repo root is the parent of src/
    return Path(__file__).resolve().parent.parent.parent


def get_assets_dir() -> Path:
    """Return the assets directory path."""
    return get_base_dir() / "assets"


def get_markers_dir() -> Path:
    """Return the markers directory path."""
    markers_path = get_assets_dir() / "markers"
    markers_path.mkdir(parents=True, exist_ok=True)
    return markers_path


def get_icons_dir() -> Path:
    """Return the icons directory path."""
    icons_path = get_assets_dir() / "icons"
    icons_path.mkdir(parents=True, exist_ok=True)
    return icons_path


def get_calibration_dir() -> Path:
    """Return the calibration directory path."""
    calib_path = get_base_dir() / "calibration"
    calib_path.mkdir(parents=True, exist_ok=True)
    return calib_path


def get_default_calibration_path() -> Path:
    """Return path to the default camera_params.npz file."""
    return get_calibration_dir() / "camera_params.npz"


def get_config_dir() -> Path:
    """Return platform-specific user configuration directory.

    Windows: %APPDATA%/ArUcoChessTracker
    Linux/macOS: ~/.config/ArUcoChessTracker
    """
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"

    config_dir = base / "ArUcoChessTracker"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file_path() -> Path:
    """Return full path to user configuration JSON file."""
    return get_config_dir() / "config.json"
