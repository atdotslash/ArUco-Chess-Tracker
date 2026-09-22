"""Application coordinator binding camera, vision pipeline, game state, UI, and TCP API."""

import logging
import queue
import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np
import customtkinter as ctk

from src.api import ChessTrackerAPI, TCPServerManager
from src.aruco_detector import ArucoDetectorWrapper
from src.board_mapper import BoardMapper
from src.calibration import CharucoCalibrator
from src.camera import Camera
from src.config import APP_NAME
from src.game_state import GameState
from src.homography import HomographyManager
from src.move_detector import MoveDetector
from src.preferences import Preferences
from src.ui.about_dialog import AboutDialog
from src.ui.calibration_dialog import CalibrationDialog
from src.ui.main_window import MainWindow
from src.ui.marker_config_dialog import MarkerConfigDialog
from src.ui.preferences_dialog import PreferencesDialog
from src.utils.paths import get_default_calibration_path

logger = logging.getLogger(__name__)


class App:
    """Core application coordinator."""

    def __init__(self) -> None:
        # 1. Preferences and Theme
        self.preferences = Preferences()
        theme = self.preferences.get("appearance", "theme", "Dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        # 2. Vision & Board Pipeline components
        self.detector = ArucoDetectorWrapper(
            dict_name=self.preferences.get("detection", "dictionary", "DICT_4X4_250"),
            lost_frames_threshold=self.preferences.get("stability", "lost_marker_frames", 5),
        )
        self.homography_mgr = HomographyManager()
        self.board_mapper = BoardMapper()
        self.game_state = GameState(marker_to_piece=self.preferences.get_marker_mapping())
        self.move_detector = MoveDetector(
            stable_frames_threshold=self.preferences.get("stability", "stable_frames_threshold", 5)
        )

        # 3. Calibration parameters
        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None
        self.calibration_rms: Optional[float] = None
        self._load_calibration()

        # 4. Camera instance
        cam_idx = self.preferences.get("camera", "index", 0)
        cam_w = self.preferences.get("camera", "width", 1280)
        cam_h = self.preferences.get("camera", "height", 720)
        cam_fps = self.preferences.get("camera", "fps", 30)
        cam_backend = self.preferences.get("camera", "backend", "DSHOW")
        cam_synthetic = self.preferences.get("camera", "synthetic_mode", False)

        self.camera = Camera(
            source=cam_idx,
            width=cam_w,
            height=cam_h,
            fps=cam_fps,
            backend=cam_backend,
            synthetic=cam_synthetic,
        )

        # 5. External API & TCP Server
        self.api = ChessTrackerAPI(self.game_state)
        self.tcp_manager = TCPServerManager(
            api=self.api,
            host=self.preferences.get("network", "tcp_host", "127.0.0.1"),
            port=self.preferences.get("network", "tcp_port", 5555),
        )

        # 6. UI Main Window
        self.window = MainWindow(
            on_toggle_camera=self.toggle_camera,
            on_open_calibration=self.open_calibration,
            on_open_marker_config=self.open_marker_config,
            on_reset_game=self.reset_game,
            on_open_preferences=self.open_preferences,
            on_open_about=self.open_about,
        )
        self.window.protocol("WM_DELETE_WINDOW", self.shutdown)

        # State tracking for UI
        self._last_move_squares: Optional[Tuple[str, str]] = None
        self._last_detected_squares: dict[int, str] = {}
        self._running = False

    def _load_calibration(self) -> None:
        """Load stored camera calibration parameters if present."""
        calib_params = CharucoCalibrator.load_calibration(get_default_calibration_path())
        if calib_params:
            self.camera_matrix, self.dist_coeffs, self.calibration_rms = calib_params
            logger.info("Loaded camera calibration (RMS: %.4f px)", self.calibration_rms)

    def start(self) -> None:
        """Start hardware threads, network server, and enter GUI event loop."""
        self._running = True

        # Start Camera
        self.camera.start()

        # Start TCP API server if enabled
        if self.preferences.get("network", "tcp_enabled", True):
            self.tcp_manager.start()

        # Initial 2D board render
        self.window.board_view.update_board(self.game_state)

        # Schedule vision processing tick
        self.window.after(30, self._vision_tick)

        # Enter Tkinter main loop
        self.window.mainloop()

    def _vision_tick(self) -> None:
        """Periodic vision processing tick on main GUI thread."""
        if not self._running:
            return

        ret, frame = self.camera.read()
        if ret and frame is not None:
            # Undistort if calibrated
            if self.camera_matrix is not None and self.dist_coeffs is not None:
                proc_frame = CharucoCalibrator.undistort(frame, self.camera_matrix, self.dist_coeffs)
            else:
                proc_frame = frame

            # 1. Detect ArUco markers
            markers = self.detector.detect_markers(
                proc_frame, self.camera_matrix, self.dist_coeffs
            )

            # 2. Extract corner markers (100, 101, 102, 103) and compute homography
            corner_pixels = {m.id: m.center for m in markers if m.id in (100, 101, 102, 103)}
            H = self.homography_mgr.update(corner_pixels)

            # 3. Map piece markers (0-31) to board squares
            mapping_result = self.board_mapper.map_markers_to_board(markers, H)
            self._last_detected_squares = mapping_result.marker_to_square

            # 4. Check move detection if board mapping succeeded
            move_res = None
            if H is not None and len(mapping_result.square_to_marker) > 0:
                move_res = self.move_detector.process_frame(
                    mapping_result.square_to_marker, self.game_state
                )

                if move_res.move and move_res.is_legal:
                    # Apply move to game state
                    self.game_state.apply_move(move_res.move)
                    self._last_move_squares = (move_res.from_square, move_res.to_square)
                    self.window.board_view.update_board(self.game_state, self._last_move_squares)

            # 5. Update Camera Preview with HUD overlays
            is_stable = move_res.is_stable if move_res else True
            status_text = move_res.status_message if move_res else ("Homography active" if H is not None else "Waiting for 4 corner markers")
            self.window.camera_view.update_frame(
                frame=proc_frame,
                markers=markers,
                H=H,
                last_move=self._last_move_squares,
                is_stable=is_stable,
                status_text=status_text,
                fps=self.camera.get_fps(),
            )

            # 6. Update Status Telemetry Bar
            self.window.update_telemetry(
                camera_connected=self.camera.is_opened(),
                fps=self.camera.get_fps(),
                is_calibrated=(self.camera_matrix is not None),
                rms=self.calibration_rms,
                turn=self.game_state.get_turn(),
                game_status=self.game_state.get_status_text(),
                fen=self.game_state.get_fen(),
            )

        # Schedule next tick (~30 FPS)
        self.window.after(30, self._vision_tick)

    def toggle_camera(self) -> None:
        """Start or stop camera capture."""
        if self.camera.is_opened():
            self.camera.stop()
        else:
            self.camera.start()

    def open_calibration(self) -> None:
        """Open the ChArUco camera lens calibration wizard."""
        def on_calibrated(K: np.ndarray, dist: np.ndarray, rms: float) -> None:
            self.camera_matrix = K
            self.dist_coeffs = dist
            self.calibration_rms = rms

        CalibrationDialog(self.window, self.camera, on_calibrated=on_calibrated)

    def open_marker_config(self) -> None:
        """Open the ArUco marker piece assignment dialog."""
        def on_saved() -> None:
            self.game_state.marker_to_piece = self.preferences.get_marker_mapping()

        MarkerConfigDialog(
            self.window,
            self.preferences,
            current_detected_squares=self._last_detected_squares,
            on_saved=on_saved,
        )

    def reset_game(self) -> None:
        """Reset game to starting chess position and reset baseline move detector."""
        self.game_state.reset()
        self._last_move_squares = None
        self.move_detector.reset_baseline({})
        self.window.board_view.update_board(self.game_state)
        logger.info("Game and baseline reset by user.")

    def open_preferences(self) -> None:
        """Open settings dialog."""
        def on_saved() -> None:
            # Update detector lost threshold
            self.detector.lost_frames_threshold = self.preferences.get("stability", "lost_marker_frames", 5)
            self.move_detector.stable_frames_threshold = self.preferences.get("stability", "stable_frames_threshold", 5)
            # Update board colors
            self.window.board_view.light_color = self.preferences.get("board", "light_square_color", "#EEEED2")
            self.window.board_view.dark_color = self.preferences.get("board", "dark_square_color", "#769656")
            self.window.board_view.update_board(self.game_state, self._last_move_squares)

        PreferencesDialog(self.window, self.preferences, on_saved=on_saved)

    def open_about(self) -> None:
        """Open About dialog."""
        AboutDialog(self.window)

    def shutdown(self) -> None:
        """Gracefully release camera, network server, and exit."""
        self._running = False
        try:
            self.camera.stop()
        except Exception as e:
            logger.error("Error stopping camera: %s", e)

        try:
            self.tcp_manager.stop()
        except Exception as e:
            logger.error("Error stopping TCP server: %s", e)

        self.window.destroy()
