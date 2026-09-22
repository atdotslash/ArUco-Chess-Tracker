"""Camera preview widget with rich HUD overlays for markers, grid, and moves."""

import tkinter as tk
from typing import List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk

from src.aruco_detector import DetectedMarker
from src.homography import board_to_pixel, square_to_board_center
from src.utils.image_io import bgr_to_pil


class CameraView(ctk.CTkFrame):
    """Camera canvas displaying live video stream with augmented reality overlays."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self.canvas = tk.Canvas(self, bg="#1a1d24", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._current_photo: Optional[ImageTk.PhotoImage] = None
        self._image_on_canvas: Optional[int] = None
        self.canvas.bind("<Configure>", self._on_resize)
        self._view_width = 640
        self._view_height = 480

    def _on_resize(self, event) -> None:
        self._view_width = max(100, event.width)
        self._view_height = max(100, event.height)

    def update_frame(
        self,
        frame: np.ndarray,
        markers: List[DetectedMarker],
        H: Optional[np.ndarray] = None,
        last_move: Optional[Tuple[str, str]] = None,
        is_stable: bool = True,
        status_text: str = "",
        fps: float = 0.0,
    ) -> None:
        """Render frame with overlays scaled to the current widget size."""
        if frame is None:
            return

        display_frame = frame.copy()
        h, w = display_frame.shape[:2]

        # 1. Draw ArUco marker boundaries and IDs
        for m in markers:
            pts = m.corners.astype(np.int32)
            color = (0, 165, 255) if m.id >= 100 else (0, 255, 0)
            cv2.polylines(display_frame, [pts], True, color, 2, cv2.LINE_AA)
            cx, cy = int(m.center[0]), int(m.center[1])
            cv2.circle(display_frame, (cx, cy), 3, (0, 0, 255), -1)
            cv2.putText(
                display_frame,
                f"#{m.id}",
                (cx - 15, cy - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 2. Draw 8x8 Chessboard Grid and Border if Homography is valid
        if H is not None:
            self._draw_board_grid(display_frame, H)

            # Draw Last Move Highlight
            if last_move and len(last_move) == 2:
                from_sq, to_sq = last_move
                self._draw_square_highlight(display_frame, H, from_sq, color=(0, 200, 255))  # Orange/Yellow
                self._draw_square_highlight(display_frame, H, to_sq, color=(0, 255, 100))    # Green
                self._draw_move_arrow(display_frame, H, from_sq, to_sq)

        # 3. Draw Top Status HUD
        self._draw_hud(display_frame, fps, len(markers), is_stable, status_text)

        # 4. Scale and present onto Canvas preserving aspect ratio
        pil_img = bgr_to_pil(display_frame)
        canvas_w, canvas_h = self._view_width, self._view_height

        # Calculate aspect-ratio preserving dimensions
        img_aspect = w / h
        canvas_aspect = canvas_w / canvas_h

        if canvas_aspect > img_aspect:
            new_h = canvas_h
            new_w = int(canvas_h * img_aspect)
        else:
            new_w = canvas_w
            new_h = int(canvas_w / img_aspect)

        new_w = max(1, new_w)
        new_h = max(1, new_h)

        resized_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self._current_photo = ImageTk.PhotoImage(resized_img)

        x_offset = (canvas_w - new_w) // 2
        y_offset = (canvas_h - new_h) // 2

        if self._image_on_canvas is None:
            self._image_on_canvas = self.canvas.create_image(
                x_offset, y_offset, anchor="nw", image=self._current_photo
            )
        else:
            self.canvas.coords(self._image_on_canvas, x_offset, y_offset)
            self.canvas.itemconfig(self._image_on_canvas, image=self._current_photo)

    def _draw_board_grid(self, frame: np.ndarray, H: np.ndarray) -> None:
        """Project and draw 8x8 chessboard lines and coordinates using inverse homography."""
        grid_color = (180, 180, 180)
        border_color = (255, 200, 0)  # Cyan/Blue in BGR

        # Draw 9 vertical rank lines
        for c in range(9):
            p1 = board_to_pixel((float(c), 0.0), H)
            p2 = board_to_pixel((float(c), 8.0), H)
            cv2.line(
                frame,
                (int(p1[0]), int(p1[1])),
                (int(p2[0]), int(p2[1])),
                border_color if c in (0, 8) else grid_color,
                2 if c in (0, 8) else 1,
                cv2.LINE_AA,
            )

        # Draw 9 horizontal file lines
        for r in range(9):
            p1 = board_to_pixel((0.0, float(r)), H)
            p2 = board_to_pixel((8.0, float(r)), H)
            cv2.line(
                frame,
                (int(p1[0]), int(p1[1])),
                (int(p2[0]), int(p2[1])),
                border_color if r in (0, 8) else grid_color,
                2 if r in (0, 8) else 1,
                cv2.LINE_AA,
            )

    def _draw_square_highlight(
        self,
        frame: np.ndarray,
        H: np.ndarray,
        square: str,
        color: Tuple[int, int, int],
    ) -> None:
        """Highlight a specific square with a tinted polygon."""
        center = square_to_board_center(square)
        if center is None:
            return

        cx, cy = center
        pts_board = [
            (cx - 0.48, cy - 0.48),
            (cx + 0.48, cy - 0.48),
            (cx + 0.48, cy + 0.48),
            (cx - 0.48, cy + 0.48),
        ]
        pixel_pts = np.int32([board_to_pixel(pt, H) for pt in pts_board])

        overlay = frame.copy()
        cv2.fillPoly(overlay, [pixel_pts], color)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.polylines(frame, [pixel_pts], True, color, 2, cv2.LINE_AA)

    def _draw_move_arrow(
        self, frame: np.ndarray, H: np.ndarray, from_sq: str, to_sq: str
    ) -> None:
        """Draw an arrow from from_sq to to_sq."""
        c1 = square_to_board_center(from_sq)
        c2 = square_to_board_center(to_sq)
        if c1 and c2:
            p1 = board_to_pixel(c1, H)
            p2 = board_to_pixel(c2, H)
            pt1 = (int(p1[0]), int(p1[1]))
            pt2 = (int(p2[0]), int(p2[1]))
            cv2.arrowedLine(frame, pt1, pt2, (0, 240, 255), 3, cv2.LINE_AA, tipLength=0.25)

    def _draw_hud(
        self,
        frame: np.ndarray,
        fps: float,
        marker_count: int,
        is_stable: bool,
        status: str,
    ) -> None:
        """Render semi-transparent telemetry ribbon at the top of camera feed."""
        # Top HUD banner
        h, w = frame.shape[:2]
        hud_bg = frame.copy()
        cv2.rectangle(hud_bg, (0, 0), (w, 36), (18, 22, 28), -1)
        cv2.addWeighted(hud_bg, 0.85, frame, 0.15, 0, frame)

        # Status text
        status_color = (80, 220, 80) if is_stable else (80, 180, 240)
        circle_color = (0, 220, 0) if is_stable else (0, 165, 255)
        cv2.circle(frame, (16, 18), 6, circle_color, -1)

        text = f"FPS: {fps:.1f} | Markers: {marker_count} | {status}"
        cv2.putText(
            frame,
            text,
            (32, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (240, 240, 240),
            1,
            cv2.LINE_AA,
        )
