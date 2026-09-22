"""Unit tests for mapping detected markers to chessboard squares."""

import numpy as np
import pytest

from src.aruco_detector import DetectedMarker
from src.board_mapper import BoardMapper
from src.homography import compute_board_homography
from src.config import CORNER_ID_A1, CORNER_ID_H1, CORNER_ID_A8, CORNER_ID_H8


@pytest.fixture
def standard_homography() -> np.ndarray:
    """Fixture providing a known 800x800 pixel to 8x8 board homography."""
    corner_pixels = {
        CORNER_ID_A8: (0.0, 0.0),
        CORNER_ID_H8: (800.0, 0.0),
        CORNER_ID_A1: (0.0, 800.0),
        CORNER_ID_H1: (800.0, 800.0),
    }
    H = compute_board_homography(corner_pixels)
    assert H is not None
    return H


def make_dummy_marker(marker_id: int, center: tuple[float, float], area: float = 100.0) -> DetectedMarker:
    """Helper to instantiate a DetectedMarker for tests."""
    corners = np.zeros((4, 2), dtype=np.float32)
    return DetectedMarker(id=marker_id, corners=corners, center=center, area=area)


def test_board_mapping_standard_positions(standard_homography):
    """Verify pieces placed at centers of squares map to expected algebraic notation."""
    mapper = BoardMapper()

    # Square e4 is (4.5, 4.5) -> (450, 450) in pixel space
    m_pawn = make_dummy_marker(0, (450.0, 450.0))
    # Square e1 is (4.5, 7.5) -> (450, 750)
    m_king = make_dummy_marker(15, (450.0, 750.0))
    # Square a8 is (0.5, 0.5) -> (50, 50)
    m_black_rook = make_dummy_marker(24, (50.0, 50.0))

    result = mapper.map_markers_to_board([m_pawn, m_king, m_black_rook], standard_homography)

    assert result.marker_to_square[0] == "e4"
    assert result.marker_to_square[15] == "e1"
    assert result.marker_to_square[24] == "a8"
    assert result.square_to_marker["e4"] == 0
    assert result.square_to_marker["e1"] == 15
    assert result.square_to_marker["a8"] == 24
    assert len(result.offboard_markers) == 0


def test_board_mapping_out_of_bounds(standard_homography):
    """Verify markers outside [0, 8) x [0, 8) are recorded as offboard."""
    mapper = BoardMapper()
    # Negative pixel coordinate (-50, 100) -> outside board
    m_captured = make_dummy_marker(1, (-50.0, 100.0))

    result = mapper.map_markers_to_board([m_captured], standard_homography)
    assert 1 not in result.marker_to_square
    assert 1 in result.offboard_markers


def test_board_mapping_conflict_resolution(standard_homography):
    """Verify two markers claiming the same square are resolved by distance to center."""
    mapper = BoardMapper()
    # Square d4 center is (3.5, 3.5) -> (350, 350)
    # Marker 2 is at (352, 351) -> dist ~2.2px
    m_winner = make_dummy_marker(2, (352.0, 351.0))
    # Marker 3 is at (380, 380) -> dist ~42px
    m_loser = make_dummy_marker(3, (380.0, 380.0))

    result = mapper.map_markers_to_board([m_winner, m_loser], standard_homography)

    assert result.square_to_marker["d5"] == 2
    assert result.marker_to_square[2] == "d5"
    assert 3 not in result.marker_to_square
    assert 3 in result.offboard_markers
    assert "d5" in result.conflicts
