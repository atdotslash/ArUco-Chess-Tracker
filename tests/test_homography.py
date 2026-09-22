"""Unit tests for homography computation and board square coordinates."""

import cv2
import numpy as np
import pytest

from src.homography import (
    compute_board_homography,
    pixel_to_board,
    board_to_pixel,
    board_to_square,
    square_to_board_center,
    HomographyManager,
)
from src.config import CORNER_ID_A1, CORNER_ID_H1, CORNER_ID_A8, CORNER_ID_H8


def test_board_to_square_conversions():
    """Verify specific required coordinate conversions from specification."""
    # Top-left corner square
    assert board_to_square((0.5, 0.5)) == "a8"
    # Bottom-right corner square
    assert board_to_square((7.5, 7.5)) == "h1"

    # White starting squares
    assert board_to_square((4.5, 4.5)) == "e4"
    assert board_to_square((3.5, 4.5)) == "d4"
    assert board_to_square((4.5, 7.5)) == "e1"
    assert board_to_square((0.5, 7.5)) == "a1"

    # Boundaries and out of bounds
    assert board_to_square((0.0, 0.0)) == "a8"
    assert board_to_square((7.99, 7.99)) == "h1"
    assert board_to_square((-0.1, 4.0)) is None
    assert board_to_square((8.0, 4.0)) is None
    assert board_to_square((4.0, -0.1)) is None
    assert board_to_square((4.0, 8.0)) is None


def test_identity_homography_mandatory_points():
    """Mandatory audit test: verify identity homography maps (0,0)->a8, (7.5,7.5)->h1, (0.5,0.5)->a8."""
    H = np.eye(3, dtype=np.float32)

    bx0, by0 = pixel_to_board((0.0, 0.0), H)
    assert board_to_square((bx0, by0)) == "a8"

    bx1, by1 = pixel_to_board((0.5, 0.5), H)
    assert board_to_square((bx1, by1)) == "a8"

    bx2, by2 = pixel_to_board((7.5, 7.5), H)
    assert board_to_square((bx2, by2)) == "h1"


def test_square_to_board_center():
    """Verify reverse mapping from algebraic square string to center (x, y)."""
    assert square_to_board_center("a8") == (0.5, 0.5)
    assert square_to_board_center("h1") == (7.5, 7.5)
    assert square_to_board_center("e4") == (4.5, 4.5)
    assert square_to_board_center("d5") == (3.5, 3.5)
    assert square_to_board_center("z9") is None
    assert square_to_board_center("") is None


def test_homography_computation_and_bidirectional_transform():
    """Verify pixel to board and board to pixel transformations under known geometry."""
    # Define a 800x800 pixel image where board corners are located at:
    # a8 (0, 0) -> (100, 100)
    # h8 (8, 0) -> (700, 100)
    # a1 (0, 8) -> (100, 700)
    # h1 (8, 8) -> (700, 700)
    corner_pixels = {
        CORNER_ID_A8: (100.0, 100.0),
        CORNER_ID_H8: (700.0, 100.0),
        CORNER_ID_A1: (100.0, 700.0),
        CORNER_ID_H1: (700.0, 700.0),
    }

    H = compute_board_homography(corner_pixels)
    assert H is not None

    # Center of board (400, 400) should map to continuous board coordinates (4.0, 4.0)
    bx, by = pixel_to_board((400.0, 400.0), H)
    assert abs(bx - 4.0) < 1e-4
    assert abs(by - 4.0) < 1e-4

    # Reverse transformation: (4.0, 4.0) -> (400.0, 400.0)
    px, py = board_to_pixel((4.0, 4.0), H)
    assert abs(px - 400.0) < 1e-4
    assert abs(py - 400.0) < 1e-4

    # Center of square e4 is (4.5, 4.5)
    # In pixel space: x = 100 + 4.5 * (600/8) = 437.5, y = 100 + 4.5 * (600/8) = 437.5
    bx, by = pixel_to_board((437.5, 437.5), H)
    sq = board_to_square((bx, by))
    assert sq == "e4"


def test_homography_manager_caching():
    """Verify HomographyManager caches matrix and updates when corners move."""
    manager = HomographyManager(movement_recompute_threshold_px=5.0)

    corners1 = {
        CORNER_ID_A8: (100.0, 100.0),
        CORNER_ID_H8: (700.0, 100.0),
        CORNER_ID_A1: (100.0, 700.0),
        CORNER_ID_H1: (700.0, 700.0),
    }
    H1 = manager.update(corners1)
    assert H1 is not None

    # Slight jitter (< 5px) should return cached matrix H1
    corners_jitter = {
        CORNER_ID_A8: (101.0, 101.0),
        CORNER_ID_H8: (700.5, 100.2),
        CORNER_ID_A1: (100.0, 700.8),
        CORNER_ID_H1: (699.5, 700.0),
    }
    H2 = manager.update(corners_jitter)
    assert H2 is H1  # Same cached instance

    # Missing a corner should still return cached H
    corners_partial = {
        CORNER_ID_A8: (100.0, 100.0),
        CORNER_ID_H8: (700.0, 100.0),
    }
    H3 = manager.update(corners_partial)
    assert H3 is H1
