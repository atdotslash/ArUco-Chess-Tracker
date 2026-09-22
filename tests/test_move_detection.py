"""Unit tests for frame-difference move detection and stability filtering."""

import pytest

from src.game_state import GameState
from src.move_detector import MoveDetector
from src.config import STANDARD_STARTING_SQUARES


@pytest.fixture
def starting_square_layout():
    """Initial square -> marker ID mapping."""
    return {sq: mid for mid, sq in STANDARD_STARTING_SQUARES.items()}


def test_stability_buffer(starting_square_layout):
    """Verify that a move is only processed after consecutive stable frames."""
    gs = GameState()
    detector = MoveDetector(stable_frames_threshold=3)

    # Initialize baseline
    detector.reset_baseline(starting_square_layout)

    # Simulate White playing e2 -> e4: marker on e2 (mid=4) moved to e4
    mid_e2 = starting_square_layout["e2"]
    moved_layout = dict(starting_square_layout)
    del moved_layout["e2"]
    moved_layout["e4"] = mid_e2

    # Frame 1 with new layout: unstable
    res1 = detector.process_frame(moved_layout, gs)
    assert res1.is_stable is False
    assert res1.move is None

    # Frame 2 with new layout: still unstable
    res2 = detector.process_frame(moved_layout, gs)
    assert res2.is_stable is False
    assert res2.move is None

    # Frame 3 with new layout: stability threshold reached!
    res3 = detector.process_frame(moved_layout, gs)
    assert res3.is_stable is True
    assert res3.is_legal is True
    assert res3.move is not None
    assert res3.move.uci() == "e2e4"
    assert res3.san == "e4"


def test_capture_detection(starting_square_layout):
    """Verify detection of a capture where target square piece is replaced."""
    gs = GameState()
    detector = MoveDetector(stable_frames_threshold=2)
    detector.reset_baseline(starting_square_layout)

    # 1. White plays e4 (mid 4)
    layout1 = dict(starting_square_layout)
    mid_e2 = layout1.pop("e2")
    layout1["e4"] = mid_e2
    for _ in range(2):
        r = detector.process_frame(layout1, gs)
    gs.apply_move(r.move)

    # 2. Black plays d5 (mid 19)
    layout2 = dict(layout1)
    mid_d7 = layout2.pop("d7")
    layout2["d5"] = mid_d7
    for _ in range(2):
        r = detector.process_frame(layout2, gs)
    gs.apply_move(r.move)

    # 3. White captures exd5: marker from e4 moves to d5, replacing Black's marker
    layout3 = dict(layout2)
    mid_white_pawn = layout3.pop("e4")
    layout3["d5"] = mid_white_pawn  # Black's pawn on d5 removed!

    for _ in range(2):
        r_capture = detector.process_frame(layout3, gs)

    assert r_capture.is_legal is True
    assert r_capture.move is not None
    assert r_capture.move.uci() == "e4d5"
    assert r_capture.san == "exd5"


def test_castling_detection():
    """Verify castling detection where King and Rook both move."""
    # Custom game state with path cleared for White kingside castling
    # FEN with e1 king, h1 rook, empty f1 and g1
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK2R w KQkq - 0 1"
    gs = GameState(initial_fen=fen)

    layout = {
        "e1": 15,  # King
        "h1": 9,   # Rook
        "a1": 8,   # Queenside Rook
    }
    detector = MoveDetector(stable_frames_threshold=2)
    detector.reset_baseline(layout)

    # Castling O-O: King moves e1 -> g1, Rook moves h1 -> f1
    castle_layout = {
        "g1": 15,
        "f1": 9,
        "a1": 8,
    }

    for _ in range(2):
        r = detector.process_frame(castle_layout, gs)

    assert r.is_legal is True
    assert r.move is not None
    assert r.move.uci() == "e1g1"
    assert r.san == "O-O"


def test_illegal_move_rejection(starting_square_layout):
    """Verify illegal move attempts are flagged without updating confirmed baseline."""
    gs = GameState()
    detector = MoveDetector(stable_frames_threshold=2)
    detector.reset_baseline(starting_square_layout)

    # Attempt illegal move: White pawn e2 -> e5 (can only move e3 or e4 on first turn)
    illegal_layout = dict(starting_square_layout)
    mid_e2 = illegal_layout.pop("e2")
    illegal_layout["e5"] = mid_e2

    for _ in range(2):
        r = detector.process_frame(illegal_layout, gs)

    assert r.is_stable is True
    assert r.is_legal is False
    assert r.move is None
    assert "Illegal move" in r.status_message
