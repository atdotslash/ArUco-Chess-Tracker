"""Camera calibration wizard dialog using ChArUco board detection."""

import time
import tkinter as tk
from typing import Callable, Optional
import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk

from src.calibration import CharucoCalibrator
from src.camera import Camera
from src.config import RECOMMENDED_CALIBRATION_FRAMES, MAX_ACCEPTABLE_RMS_ERROR
from src.utils.image_io import bgr_to_pil
from src.utils.paths import get_default_calibration_path


class CalibrationDialog(ctk.CTkToplevel):
    """Interactive dialog for capturing ChArUco calibration frames and computing camera parameters."""

    def __init__(
        self,
        parent,
        camera: Camera,
        on_calibrated: Optional[Callable[[np.ndarray, np.ndarray, float], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.camera = camera
        self.on_calibrated = on_calibrated

        self.calibrator = CharucoCalibrator()
        self.title("Camera Lens Calibration (ChArUco)")
        self.geometry("760x680")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 760) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 680) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self.transient(parent)
        self.grab_set()

        self._running = True
        self._last_captured_frame: Optional[np.ndarray] = None
        self._computed_params: Optional[tuple[np.ndarray, np.ndarray, float]] = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        self._build_ui()
        self._schedule_preview()

    def _build_ui(self) -> None:
        # Header instructions
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(12, 6))

        lbl_title = ctk.CTkLabel(header, text="ChArUco Camera Calibration", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            header,
            text="Hold the printed ChArUco board at different angles, distances, and tilt orientations.\n"
                 "Capture at least 15-20 frames with good coverage, then click 'Calibrate'.",
            font=("Segoe UI", 11),
            text_color="#9aa4b2",
            justify="left",
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Camera preview canvas
        preview_container = ctk.CTkFrame(self, fg_color="#14171d", corner_radius=8)
        preview_container.pack(fill="both", expand=True, padx=20, pady=6)

        self.canvas = tk.Canvas(preview_container, bg="#14171d", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._photo: Optional[ImageTk.PhotoImage] = None

        # Progress bar & Status Ribbon
        status_bar = ctk.CTkFrame(self, fg_color="#1e222b", corner_radius=6)
        status_bar.pack(fill="x", padx=20, pady=6)

        self.lbl_detection_status = ctk.CTkLabel(
            status_bar,
            text="Corners Detected: 0  |  Frame Status: Hold board steady",
            font=("Segoe UI", 12),
            text_color="#ced4da",
        )
        self.lbl_detection_status.pack(side="left", padx=12, pady=6)

        self.lbl_counter = ctk.CTkLabel(
            status_bar,
            text=f"Frames: 0 / {RECOMMENDED_CALIBRATION_FRAMES}",
            font=("Segoe UI", 12, "bold"),
            text_color="#339af0",
        )
        self.lbl_counter.pack(side="right", padx=12, pady=6)

        self.progress_bar = ctk.CTkProgressBar(self, height=8)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 6))
        self.progress_bar.set(0.0)

        # Control Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(6, 14))

        self.btn_clear = ctk.CTkButton(
            btn_frame,
            text="Clear Frames",
            fg_color="#495057",
            hover_color="#343a40",
            width=110,
            command=self._on_clear,
        )
        self.btn_clear.pack(side="left")

        self.btn_capture = ctk.CTkButton(
            btn_frame,
            text="Capture Frame (Space)",
            fg_color="#1971c2",
            hover_color="#1864ab",
            width=160,
            command=self._on_capture,
        )
        self.btn_capture.pack(side="left", padx=10)
        self.bind("<space>", lambda e: self._on_capture())

        self.btn_calibrate = ctk.CTkButton(
            btn_frame,
            text="Compute Calibration",
            fg_color="#2b8a3e",
            hover_color="#237032",
            width=160,
            state="disabled",
            command=self._on_calibrate,
        )
        self.btn_calibrate.pack(side="left")

        self.btn_close = ctk.CTkButton(
            btn_frame,
            text="Close",
            fg_color="#6c757d",
            hover_color="#5a6268",
            width=100,
            command=self._on_close,
        )
        self.btn_close.pack(side="right")

    def _schedule_preview(self) -> None:
        """Update live camera preview and overlay corner detection."""
        if not self._running:
            return

        ret, frame = self.camera.read()
        if ret and frame is not None:
            self._last_captured_frame = frame.copy()
            corners, ids, count = self.calibrator.detect_charuco(frame)

            preview_frame = frame.copy()
            if count > 0 and corners is not None and ids is not None:
                cv2.aruco.drawDetectedCornersCharuco(preview_frame, corners, ids, (0, 255, 0))
                status_msg = f"Valid Frame! ({count} corners)"
                status_color = "#40c057"
            else:
                status_msg = "Looking for ChArUco board..."
                status_color = "#fcc419"

            self.lbl_detection_status.configure(
                text=f"Corners: {count}  |  {status_msg}",
                text_color=status_color,
            )

            # Draw onto canvas
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw > 50 and ch > 50:
                h, w = preview_frame.shape[:2]
                aspect = w / h
                canvas_aspect = cw / ch
                if canvas_aspect > aspect:
                    nw = int(ch * aspect)
                    nh = ch
                else:
                    nw = cw
                    nh = int(cw / aspect)

                pil_img = bgr_to_pil(preview_frame).resize((max(1, nw), max(1, nh)), Image.Resampling.BILINEAR)
                self._photo = ImageTk.PhotoImage(pil_img)
                self.canvas.delete("all")
                self.canvas.create_image(cw // 2, ch // 2, anchor="center", image=self._photo)

        self.after(30, self._schedule_preview)

    def _on_capture(self) -> None:
        """Capture the current frame if it contains sufficient ChArUco corners."""
        if self._last_captured_frame is None:
            return

        ok, count = self.calibrator.add_frame(self._last_captured_frame)
        if ok:
            frames_count = self.calibrator.get_frame_count()
            self.lbl_counter.configure(text=f"Frames: {frames_count} / {RECOMMENDED_CALIBRATION_FRAMES}")
            progress = min(1.0, frames_count / float(RECOMMENDED_CALIBRATION_FRAMES))
            self.progress_bar.set(progress)

            if frames_count >= 5:
                self.btn_calibrate.configure(state="normal")
        else:
            self.lbl_detection_status.configure(
                text=f"Frame rejected! Found only {count} corners (minimum {self.calibrator.min_corners})",
                text_color="#ff6b6b",
            )

    def _on_clear(self) -> None:
        """Clear captured frames."""
        self.calibrator.reset()
        self.lbl_counter.configure(text=f"Frames: 0 / {RECOMMENDED_CALIBRATION_FRAMES}")
        self.progress_bar.set(0.0)
        self.btn_calibrate.configure(state="disabled")

    def _on_calibrate(self) -> None:
        """Run camera matrix calibration."""
        try:
            self.btn_calibrate.configure(state="disabled", text="Computing...")
            self.update_idletasks()

            rms, camera_matrix, dist_coeffs = self.calibrator.calibrate()
            self._computed_params = (camera_matrix, dist_coeffs, rms)

            # Save to default calibration path
            save_path = get_default_calibration_path()
            saved = CharucoCalibrator.save_calibration(save_path, camera_matrix, dist_coeffs, rms)

            if rms <= MAX_ACCEPTABLE_RMS_ERROR:
                msg = f"Calibration Successful!\nRMS Error: {rms:.4f} px (Excellent: < {MAX_ACCEPTABLE_RMS_ERROR} px)"
                color = "#40c057"
            else:
                msg = f"Calibration Suboptimal!\nRMS Error: {rms:.4f} px (> {MAX_ACCEPTABLE_RMS_ERROR} px). Consider repeating."
                color = "#fcc419"

            self.lbl_detection_status.configure(text=msg, text_color=color)

            if self.on_calibrated:
                self.on_calibrated(camera_matrix, dist_coeffs, rms)

            self.btn_calibrate.configure(state="normal", text="Re-Calibrate")
        except Exception as e:
            self.lbl_detection_status.configure(text=f"Calibration Error: {e}", text_color="#ff6b6b")
            self.btn_calibrate.configure(state="normal", text="Compute Calibration")

    def _on_close(self) -> None:
        self._running = False
        self.destroy()
