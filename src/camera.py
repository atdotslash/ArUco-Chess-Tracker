"""Threaded camera capture module supporting USB webcams, video files, and synthetic board generation."""

import logging
import platform
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Union
import cv2
import numpy as np

from src.markers import generate_marker, get_aruco_dict
from src.config import CORNER_ID_A1, CORNER_ID_H1, CORNER_ID_A8, CORNER_ID_H8, STANDARD_STARTING_SQUARES

logger = logging.getLogger(__name__)


class SyntheticBoardGenerator:
    """Generates synthetic perspective-projected chessboard frames with ArUco markers for testing and offline demo."""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self.width = width
        self.height = height
        self._cache: Optional[np.ndarray] = None
        self._last_time = time.time()
        self.piece_positions = dict(STANDARD_STARTING_SQUARES)  # marker_id -> square

    def set_piece_position(self, marker_id: int, square: str) -> None:
        """Move a marker to a new square (e.g. 0 to 'e4')."""
        self.piece_positions[marker_id] = square
        self._cache = None

    def remove_piece(self, marker_id: int) -> None:
        """Simulate capturing a piece."""
        self.piece_positions.pop(marker_id, None)
        self._cache = None

    def render_frame(self) -> np.ndarray:
        """Render a full synthetic frame."""
        frame = np.full((self.height, self.width, 3), 40, dtype=np.uint8)

        # Chessboard dimensions in pixels
        board_size = 560
        sq_size = board_size // 8
        board_canvas = np.full((board_size + 160, board_size + 160, 3), 30, dtype=np.uint8)
        offset = 80

        # Draw 8x8 squares
        light_color = (210, 236, 235)  # BGR
        dark_color = (86, 150, 118)
        for r in range(8):
            for c in range(8):
                x0 = offset + c * sq_size
                y0 = offset + r * sq_size
                color = light_color if (r + c) % 2 == 0 else dark_color
                cv2.rectangle(board_canvas, (x0, y0), (x0 + sq_size, y0 + sq_size), color, -1)

        # Draw Corner ArUcos at outer margins
        # a8 corner: top-left (offset, offset)
        # h8 corner: top-right (offset + board_size, offset)
        # a1 corner: bottom-left (offset, offset + board_size)
        # h1 corner: bottom-right (offset + board_size, offset + board_size)
        corner_specs = [
            (CORNER_ID_A8, offset - 40, offset - 40),
            (CORNER_ID_H8, offset + board_size - 10, offset - 40),
            (CORNER_ID_A1, offset - 40, offset + board_size - 10),
            (CORNER_ID_H1, offset + board_size - 10, offset + board_size - 10),
        ]
        aruco_dict = get_aruco_dict("DICT_4X4_250")
        for cid, cx, cy in corner_specs:
            m_img = cv2.aruco.generateImageMarker(aruco_dict, cid, 50)
            m_bgr = cv2.cvtColor(m_img, cv2.COLOR_GRAY2BGR)
            board_canvas[cy : cy + 50, cx : cx + 50] = m_bgr

        # Draw piece ArUcos inside their assigned squares
        for marker_id, sq in self.piece_positions.items():
            if len(sq) != 2:
                continue
            col_idx = ord(sq[0].lower()) - ord("a")
            row_idx = 8 - int(sq[1])
            if 0 <= col_idx < 8 and 0 <= row_idx < 8:
                px = offset + col_idx * sq_size + (sq_size - 40) // 2
                py = offset + row_idx * sq_size + (sq_size - 40) // 2
                m_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, 40)
                m_bgr = cv2.cvtColor(m_img, cv2.COLOR_GRAY2BGR)
                board_canvas[py : py + 40, px : px + 40] = m_bgr

        # Place onto full frame with mild perspective
        canvas_h, canvas_w = board_canvas.shape[:2]
        src_pts = np.float32([[0, 0], [canvas_w, 0], [canvas_w, canvas_h], [0, canvas_h]])
        dst_pts = np.float32([
            [self.width * 0.22, self.height * 0.08],
            [self.width * 0.78, self.height * 0.08],
            [self.width * 0.88, self.height * 0.92],
            [self.width * 0.12, self.height * 0.92],
        ])
        H = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(board_canvas, H, (self.width, self.height))

        # Combine with frame background
        mask = (warped > 0).any(axis=2)
        frame[mask] = warped[mask]
        return frame


class Camera:
    """Threaded camera capture supporting USB webcams, video files, and synthetic feed."""

    def __init__(
        self,
        source: Union[int, str, Path] = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        backend: str = "DSHOW",
        synthetic: bool = False,
    ) -> None:
        self.source = source
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.backend = backend
        self.synthetic_mode = synthetic

        self._cap: Optional[cv2.VideoCapture] = None
        self._synthetic_gen = SyntheticBoardGenerator(width, height)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._has_new_frame = False

        self._actual_fps: float = 0.0
        self._frame_count = 0
        self._fps_start_time = time.time()

    def start(self) -> bool:
        """Start camera capture in background thread."""
        if self._running:
            return True

        if not self.synthetic_mode:
            try:
                # DirectShow backend is fastest and most reliable on Windows
                backend_flag = cv2.CAP_DSHOW if (platform.system() == "Windows" and self.backend == "DSHOW") else cv2.CAP_ANY
                if isinstance(self.source, int):
                    self._cap = cv2.VideoCapture(self.source, backend_flag)
                else:
                    self._cap = cv2.VideoCapture(str(self.source))

                if self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                    self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                else:
                    logger.warning("Failed to open camera %s. Falling back to synthetic mode.", self.source)
                    self.synthetic_mode = True
                    if self._cap:
                        self._cap.release()
                    self._cap = None
            except Exception as e:
                logger.error("Camera open exception: %s. Using synthetic mode.", e)
                self.synthetic_mode = True

        self._running = True
        self._fps_start_time = time.time()
        self._frame_count = 0

        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraCaptureThread")
        self._thread.start()
        return True

    def _capture_loop(self) -> None:
        """Continuous frame grabber thread."""
        target_interval = 1.0 / max(1, self.target_fps)

        while self._running:
            t0 = time.time()

            if self.synthetic_mode or self._cap is None:
                frame = self._synthetic_gen.render_frame()
                ret = True
            else:
                ret, frame = self._cap.read()
                if not ret:
                    # If reading a video file, loop to beginning
                    if isinstance(self.source, (str, Path)):
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self._cap.read()
                    if not ret:
                        time.sleep(0.05)
                        continue

            if ret and frame is not None:
                with self._lock:
                    self._latest_frame = frame
                    self._has_new_frame = True

                self._frame_count += 1
                elapsed = time.time() - self._fps_start_time
                if elapsed >= 1.0:
                    self._actual_fps = self._frame_count / elapsed
                    self._frame_count = 0
                    self._fps_start_time = time.time()

            # Throttle if needed to match target FPS
            work_time = time.time() - t0
            sleep_time = target_interval - work_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Return the latest grabbed frame (or a copy) without blocking."""
        with self._lock:
            if self._latest_frame is None:
                return False, None
            return True, self._latest_frame.copy()

    def is_opened(self) -> bool:
        """Check if camera is active."""
        if self.synthetic_mode:
            return self._running
        return self._cap is not None and self._cap.isOpened() and self._running

    def get_fps(self) -> float:
        """Return current measured FPS."""
        return self._actual_fps if self._actual_fps > 0 else float(self.target_fps)

    def stop(self) -> None:
        """Stop capture thread and release hardware resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def synthetic_generator(self) -> SyntheticBoardGenerator:
        """Access the underlying synthetic generator for test manipulation."""
        return self._synthetic_gen
