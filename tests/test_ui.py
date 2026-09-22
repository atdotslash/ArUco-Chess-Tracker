"""Unit tests for UI component instantiation and App wiring."""

import pytest
import customtkinter as ctk

from src.app import App
from src.ui.about_dialog import AboutDialog
from src.ui.preferences_dialog import PreferencesDialog
from src.ui.marker_config_dialog import MarkerConfigDialog


def test_app_instantiation_and_wiring():
    """Verify App initializes all subcomponents and releases resources cleanly."""
    app = App()
    assert app.window is not None
    assert app.game_state is not None
    assert app.camera is not None
    assert app.tcp_manager is not None
    assert app.board_mapper is not None

    # Test toggling camera
    app.toggle_camera()
    assert app.camera.is_opened() is True
    app.toggle_camera()
    assert app.camera.is_opened() is False

    # Clean shutdown
    app.shutdown()


def test_dialogs_instantiation():
    """Verify modal dialogs can be instantiated without errors."""
    app = App()

    # About Dialog
    about = AboutDialog(app.window)
    assert about.title() == "About ArUco Chess Tracker"
    about.destroy()

    # Preferences Dialog
    prefs = PreferencesDialog(app.window, app.preferences)
    assert prefs.title() == "Preferences"
    prefs.destroy()

    # Marker Config Dialog
    marker_cfg = MarkerConfigDialog(app.window, app.preferences)
    assert marker_cfg.title() == "ArUco Marker Assignment"
    marker_cfg.destroy()

    app.shutdown()
