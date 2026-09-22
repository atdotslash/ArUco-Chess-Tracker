"""Tests for configuration, preferences persistence, and path resolution."""

import json
from pathlib import Path
import pytest

from src.config import (
    __version__,
    APP_NAME,
    AUTHOR,
    PIECE_ID_MIN,
    PIECE_ID_MAX,
    CORNER_ID_A1,
    CORNER_ID_H1,
    CORNER_ID_A8,
    CORNER_ID_H8,
    DEFAULT_MARKER_TO_PIECE,
    STANDARD_STARTING_SQUARES,
)
from src.preferences import Preferences
from src.utils.paths import (
    get_base_dir,
    get_assets_dir,
    get_markers_dir,
    get_icons_dir,
    get_calibration_dir,
    get_default_calibration_path,
    get_config_dir,
    get_config_file_path,
)


def test_config_constants():
    """Verify essential configuration constants."""
    assert __version__ == "0.1.0"
    assert APP_NAME == "ArUco Chess Tracker"
    assert AUTHOR == "atdotslash"
    assert PIECE_ID_MIN == 0
    assert PIECE_ID_MAX == 31
    assert CORNER_ID_A1 == 100
    assert CORNER_ID_H1 == 101
    assert CORNER_ID_A8 == 102
    assert CORNER_ID_H8 == 103

    # Check piece mapping has exactly 32 pieces
    assert len(DEFAULT_MARKER_TO_PIECE) == 32
    assert DEFAULT_MARKER_TO_PIECE[0] == "P"
    assert DEFAULT_MARKER_TO_PIECE[15] == "K"
    assert DEFAULT_MARKER_TO_PIECE[31] == "k"

    # Check starting squares mapping has all 32 pieces
    assert len(STANDARD_STARTING_SQUARES) == 32
    assert STANDARD_STARTING_SQUARES[8] == "a1"
    assert STANDARD_STARTING_SQUARES[15] == "e1"
    assert STANDARD_STARTING_SQUARES[31] == "e8"


def test_paths():
    """Verify directory and file path helper functions."""
    base = get_base_dir()
    assert base.exists()

    assets = get_assets_dir()
    assert assets.name == "assets"

    markers = get_markers_dir()
    assert markers.exists()
    assert markers.name == "markers"

    icons = get_icons_dir()
    assert icons.exists()

    calibration = get_calibration_dir()
    assert calibration.exists()

    calib_file = get_default_calibration_path()
    assert calib_file.name == "camera_params.npz"

    config_dir = get_config_dir()
    assert config_dir.exists()
    assert "ArUcoChessTracker" in str(config_dir)

    config_file = get_config_file_path()
    assert config_file.name == "config.json"


def test_preferences_lifecycle(tmp_path: Path):
    """Test loading, updating, saving, and defaults reset for preferences."""
    test_file = tmp_path / "test_config.json"
    pref = Preferences(config_path=test_file)

    # Initial load writes defaults
    assert test_file.exists()
    assert pref.get("camera", "width") == 1280

    # Modify and save
    pref.set("camera", "width", 1920)
    assert pref.save() is True

    # Reload from file and verify update persisted
    pref2 = Preferences(config_path=test_file)
    assert pref2.get("camera", "width") == 1920

    # Test marker mapping helper
    mapping = pref2.get_marker_mapping()
    assert len(mapping) == 32
    assert mapping[0] == "P"
    mapping[0] = "Q"  # Promote pawn 0
    pref2.set_marker_mapping(mapping)
    pref2.save()

    pref3 = Preferences(config_path=test_file)
    assert pref3.get_marker_mapping()[0] == "Q"

    # Test reset to defaults
    pref3.reset_to_defaults()
    assert pref3.get("camera", "width") == 1280
    assert pref3.get_marker_mapping()[0] == "P"


def test_preferences_corruption_fallback(tmp_path: Path):
    """Test graceful handling and backup of corrupted JSON."""
    test_file = tmp_path / "corrupted_config.json"
    # Write invalid JSON content
    test_file.write_text("{ incomplete json: true, bad: ", encoding="utf-8")

    # Creating Preferences instance should not crash, but back up and restore defaults
    pref = Preferences(config_path=test_file)
    assert pref.get("camera", "width") == 1280

    # Check backup file was created
    backup_file = test_file.with_suffix(".json.bak")
    assert backup_file.exists()
    assert "{ incomplete json" in backup_file.read_text(encoding="utf-8")
