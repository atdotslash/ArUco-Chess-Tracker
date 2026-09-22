"""Main application window uniting camera stream HUD, 2D board view, and toolbar controls."""

import tkinter as tk
from typing import Callable, Optional
import customtkinter as ctk

from src.config import APP_NAME, __version__
from src.ui.camera_view import CameraView
from src.ui.board_view import BoardView


class MainWindow(ctk.CTk):
    """Primary application GUI window."""

    def __init__(
        self,
        on_toggle_camera: Callable[[], None],
        on_open_calibration: Callable[[], None],
        on_open_marker_config: Callable[[], None],
        on_reset_game: Callable[[], None],
        on_open_preferences: Callable[[], None],
        on_open_about: Callable[[], None],
    ) -> None:
        super().__init__()

        self.on_toggle_camera = on_toggle_camera
        self.on_open_calibration = on_open_calibration
        self.on_open_marker_config = on_open_marker_config
        self.on_reset_game = on_reset_game
        self.on_open_preferences = on_open_preferences
        self.on_open_about = on_open_about

        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("1280x820")
        self.minsize(960, 640)

        # Keyboard shortcuts
        self.bind("<F1>", lambda e: self.on_open_about())
        self.bind("<Control-r>", lambda e: self.on_reset_game())
        self.bind("<Control-comma>", lambda e: self.on_open_preferences())

        self._build_layout()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Top Header Toolbar
        self.toolbar = ctk.CTkFrame(self, fg_color="#181b22", corner_radius=0, height=52)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        # Left toolbar items
        self.btn_camera = ctk.CTkButton(
            self.toolbar,
            text="Disconnect Camera",
            fg_color="#2b8a3e",
            hover_color="#237032",
            width=140,
            command=self.on_toggle_camera,
        )
        self.btn_camera.pack(side="left", padx=(12, 6), pady=8)

        self.btn_calibrate = ctk.CTkButton(
            self.toolbar,
            text="Calibrate Lens",
            fg_color="#1971c2",
            hover_color="#1864ab",
            width=120,
            command=self.on_open_calibration,
        )
        self.btn_calibrate.pack(side="left", padx=6, pady=8)

        self.btn_markers = ctk.CTkButton(
            self.toolbar,
            text="Marker Config",
            fg_color="#495057",
            hover_color="#343a40",
            width=120,
            command=self.on_open_marker_config,
        )
        self.btn_markers.pack(side="left", padx=6, pady=8)

        self.btn_reset = ctk.CTkButton(
            self.toolbar,
            text="Reset Game",
            fg_color="#c92a2a",
            hover_color="#a61e1e",
            width=110,
            command=self.on_reset_game,
        )
        self.btn_reset.pack(side="left", padx=6, pady=8)

        # Right toolbar items
        self.btn_about = ctk.CTkButton(
            self.toolbar,
            text="About (F1)",
            fg_color="#343a40",
            hover_color="#212529",
            width=90,
            command=self.on_open_about,
        )
        self.btn_about.pack(side="right", padx=(6, 12), pady=8)

        self.btn_prefs = ctk.CTkButton(
            self.toolbar,
            text="Preferences",
            fg_color="#343a40",
            hover_color="#212529",
            width=100,
            command=self.on_open_preferences,
        )
        self.btn_prefs.pack(side="right", padx=6, pady=8)

        # 2. Central Split: Camera (Left) | 2D Board (Right)
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=1, column=0, sticky="nsew", padx=12, pady=10)
        self.main_content.grid_columnconfigure((0, 1), weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        # Left: Live Camera View
        self.camera_view = CameraView(self.main_content, corner_radius=8, fg_color="#14171d")
        self.camera_view.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        # Right: 2D Rendered Board
        self.board_view = BoardView(self.main_content, corner_radius=8, fg_color="#14171d")
        self.board_view.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        # 3. Bottom Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color="#14171d", corner_radius=0, height=36)
        self.status_bar.grid(row=2, column=0, sticky="ew")

        self.lbl_status_cam = ctk.CTkLabel(
            self.status_bar,
            text="Camera: Connected (30 FPS)",
            font=("Segoe UI", 11),
            text_color="#9aa4b2",
        )
        self.lbl_status_cam.pack(side="left", padx=12, pady=4)

        self.lbl_status_calib = ctk.CTkLabel(
            self.status_bar,
            text="Calibration: Loaded",
            font=("Segoe UI", 11),
            text_color="#9aa4b2",
        )
        self.lbl_status_calib.pack(side="left", padx=12, pady=4)

        self.lbl_status_game = ctk.CTkLabel(
            self.status_bar,
            text="Turn: White | Status: Ready",
            font=("Segoe UI", 11, "bold"),
            text_color="#4dabf7",
        )
        self.lbl_status_game.pack(side="left", padx=12, pady=4)

        # FEN display and copy button on bottom-right
        self.btn_copy_fen = ctk.CTkButton(
            self.status_bar,
            text="Copy FEN",
            width=70,
            height=22,
            font=("Segoe UI", 10),
            command=self._on_copy_fen,
        )
        self.btn_copy_fen.pack(side="right", padx=(4, 12), pady=6)

        self.lbl_fen = ctk.CTkLabel(
            self.status_bar,
            text="FEN: -",
            font=("Consolas", 10),
            text_color="#adb5bd",
        )
        self.lbl_fen.pack(side="right", padx=6, pady=4)

    def update_telemetry(
        self,
        camera_connected: bool,
        fps: float,
        is_calibrated: bool,
        rms: Optional[float],
        turn: str,
        game_status: str,
        fen: str,
    ) -> None:
        """Update status bar indicators."""
        cam_text = f"Camera: {'Active' if camera_connected else 'Disconnected'} ({fps:.1f} FPS)"
        self.lbl_status_cam.configure(
            text=cam_text,
            text_color="#40c057" if camera_connected else "#fa5252",
        )
        self.btn_camera.configure(
            text="Disconnect Camera" if camera_connected else "Connect Camera",
            fg_color="#c92a2a" if camera_connected else "#2b8a3e",
            hover_color="#a61e1e" if camera_connected else "#237032",
        )

        calib_text = f"Calibrated (RMS {rms:.3f}px)" if is_calibrated and rms is not None else ("Calibrated" if is_calibrated else "No Calibration")
        self.lbl_status_calib.configure(
            text=f"Calibration: {calib_text}",
            text_color="#40c057" if is_calibrated else "#fcc419",
        )

        self.lbl_status_game.configure(
            text=f"Turn: {turn.capitalize()}  |  {game_status}",
        )
        self.lbl_fen.configure(text=f"FEN: {fen}")

    def _on_copy_fen(self) -> None:
        """Copy FEN to clipboard."""
        raw_text = self.lbl_fen.cget("text")
        if raw_text.startswith("FEN: "):
            fen_val = raw_text[5:]
            self.clipboard_clear()
            self.clipboard_append(fen_val)
            self.btn_copy_fen.configure(text="Copied!")
            self.after(1500, lambda: self.btn_copy_fen.configure(text="Copy FEN"))
