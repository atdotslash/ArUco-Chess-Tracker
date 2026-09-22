"""Homography calculation between image pixels and 8x8 chessboard coordinates."""

import logging
import math
from typing import Dict, Optional, Tuple
import cv2
import numpy as np

from src.config import (
    CORNER_ID_A1,
    CORNER_ID_H1,
    CORNER_ID_A8,
    CORNER_ID_H8,
)

logger = logging.getLogger(__name__)


def compute_board_homography(
    corner_pixels: Dict[int, Tuple[float, float]],
    margin_squares: float = 0.0,
) -> Optional[np.ndarray]:
    """Compute the 3x3 homography matrix H from pixel space to board coordinate space [0, 8] x [0, 8].

    Corner world targets:
        - Marker 102 (a8 outer corner): (0 - margin, 0 - margin)
        - Marker 103 (h8 outer corner): (8 + margin, 0 - margin)
        - Marker 100 (a1 outer corner): (0 - margin, 8 + margin)
        - Marker 101 (h1 outer corner): (8 + margin, 8 + margin)

    Args:
        corner_pixels: Dict mapping marker ID (100, 101, 102, 103) to (x, y) center pixel.
        margin_squares: Optional board border offset in units of squares.

    Returns:
        3x3 Homography matrix H mapping pixels -> board coords, or None if not all 4 corners exist.
    """
    required_corners = (CORNER_ID_A8, CORNER_ID_H8, CORNER_ID_A1, CORNER_ID_H1)
    if not all(cid in corner_pixels for cid in required_corners):
        return None

    src_pts = np.float32([
        corner_pixels[CORNER_ID_A8],
        corner_pixels[CORNER_ID_H8],
        corner_pixels[CORNER_ID_A1],
        corner_pixels[CORNER_ID_H1],
    ])

    m = margin_squares
    dst_pts = np.float32([
        [0.0 - m, 0.0 - m],  # a8 corner
        [8.0 + m, 0.0 - m],  # h8 corner
        [0.0 - m, 8.0 + m],  # a1 corner
        [8.0 + m, 8.0 + m],  # h1 corner
    ])

    try:
        H = cv2.getPerspectiveTransform(src_pts, dst_pts)
        return H
    except Exception as e:
        logger.error("Failed to compute perspective transform: %s", e)
        return None


def pixel_to_board(pixel: Tuple[float, float], H: np.ndarray) -> Tuple[float, float]:
    """Transform pixel coordinates (px, py) to continuous board coordinates (bx, by)."""
    pt = np.float32([[[pixel[0], pixel[1]]]])
    res = cv2.perspectiveTransform(pt, H)
    bx = float(res[0, 0, 0])
    by = float(res[0, 0, 1])
    return bx, by


def board_to_pixel(board_coord: Tuple[float, float], H: np.ndarray) -> Tuple[float, float]:
    """Transform continuous board coordinates (bx, by) to pixel coordinates (px, py)."""
    H_inv = np.linalg.inv(H)
    pt = np.float32([[[board_coord[0], board_coord[1]]]])
    res = cv2.perspectiveTransform(pt, H_inv)
    px = float(res[0, 0, 0])
    py = float(res[0, 0, 1])
    return px, py


def board_to_square(board_coord: Tuple[float, float]) -> Optional[str]:
    """Convert continuous board coordinate (x, y) to algebraic square notation (e.g. 'e4').

    Returns None if the coordinate lies outside the 8x8 chessboard [0, 8) x [0, 8).
    """
    x, y = board_coord
    if not (0.0 <= x < 8.0 and 0.0 <= y < 8.0):
        return None

    col_idx = int(math.floor(x))
    row_idx = int(math.floor(y))

    # Column: a=0, b=1, ..., h=7
    file_char = chr(ord("a") + col_idx)
    # Row: rank 8 is top (row_idx=0), rank 1 is bottom (row_idx=7)
    rank_char = str(8 - row_idx)

    return f"{file_char}{rank_char}"


def square_to_board_center(square: str) -> Optional[Tuple[float, float]]:
    """Convert algebraic square notation (e.g. 'e4') to continuous center coordinates."""
    if len(square) != 2:
        return None

    file_char = square[0].lower()
    rank_char = square[1]

    if not ("a" <= file_char <= "h" and "1" <= rank_char <= "8"):
        return None

    col_idx = ord(file_char) - ord("a")
    row_idx = 8 - int(rank_char)

    return (col_idx + 0.5, row_idx + 0.5)


class HomographyManager:
    """Maintains cached homography and tracks corner stability to minimize recomputation."""

    def __init__(self, movement_recompute_threshold_px: float = 3.0) -> None:
        self.threshold_px = movement_recompute_threshold_px
        self._cached_H: Optional[np.ndarray] = None
        self._last_corner_centers: Dict[int, Tuple[float, float]] = {}

    def update(
        self,
        corner_pixels: Dict[int, Tuple[float, float]],
        margin_squares: float = 0.0,
    ) -> Optional[np.ndarray]:
        """Update homography if corner positions changed or if none is currently cached."""
        required = (CORNER_ID_A8, CORNER_ID_H8, CORNER_ID_A1, CORNER_ID_H1)
        if not all(cid in corner_pixels for cid in required):
            # Not all 4 corners detected in this frame; return existing cached H if available
            return self._cached_H

        # Check if corners have moved significantly compared to last computation
        if self._cached_H is not None and len(self._last_corner_centers) == 4:
            max_dist = max(
                math.hypot(
                    corner_pixels[cid][0] - self._last_corner_centers[cid][0],
                    corner_pixels[cid][1] - self._last_corner_centers[cid][1],
                )
                for cid in required
            )
            if max_dist < self.threshold_px:
                return self._cached_H

        # Compute fresh homography
        H = compute_board_homography(corner_pixels, margin_squares)
        if H is not None:
            self._cached_H = H
            self._last_corner_centers = {cid: corner_pixels[cid] for cid in required}

        return self._cached_H

    @property
    def current_homography(self) -> Optional[np.ndarray]:
        """Return currently cached homography matrix."""
        return self._cached_H
