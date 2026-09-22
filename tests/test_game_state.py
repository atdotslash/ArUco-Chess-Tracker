"""Unit tests for GameState logic, move validation, and FEN tracking."""

import chess
import pytest

from src.game_state import GameState
from src.config import STANDARD_STARTING_SQUARES


def test_game_state_initialization():
    """Verify standard game state initialization."""
    gs = GameState()
    assert gs.get_turn() == "white"
    assert gs.is_game_over() is False
    assert len(gs.move_history) == 0
    assert len(gs.captured) == 0
    assert gs.get_fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_auto_assign_markers():
    """Verify auto-assignment of marker IDs based on standard initial positions."""
    gs = GameState()
    # Invert STANDARD_STARTING_SQUARES to marker_to_square
    marker_to_square = dict(STANDARD_STARTING_SQUARES)

    assigned_count, unassigned = gs.auto_assign_from_standard_position(marker_to_square)
    assert assigned_count == 32
    assert len(unassigned) == 0

    # Marker 8 was on a1 -> White Rook ('R')
    assert gs.marker_to_piece[8] == "R"
    # Marker 15 was on e1 -> White King ('K')
    assert gs.marker_to_piece[15] == "K"
    # Marker 31 was on e8 -> Black King ('k')
    assert gs.marker_to_piece[31] == "k"


def test_move_validation_and_application():
    """Verify legal move validation, application, and illegal rejection."""
    gs = GameState()

    # e2 -> e4 is legal for White
    m = gs.validate_move("e2", "e4")
    assert m is not None
    assert m.uci() == "e2e4"
    assert gs.apply_move(m) is True
    assert gs.get_turn() == "black"
    assert gs.get_last_move() == "e4"

    # e7 -> e5 is legal for Black
    m2 = gs.validate_move("e7", "e5")
    assert m2 is not None
    assert gs.apply_move(m2) is True
    assert gs.get_turn() == "white"
    assert gs.get_last_move() == "e5"

    # e4 -> e5 is illegal (pawn cannot move into occupied square)
    assert gs.validate_move("e4", "e5") is None

    # Knight jump
    m3 = gs.validate_move("g1", "f3")
    assert m3 is not None
    assert gs.apply_move(m3) is True
    assert gs.get_last_move() == "Nf3"


def test_capture_tracking():
    """Verify captured pieces are recorded."""
    gs = GameState()
    # 1. e4 d5 2. exd5
    gs.apply_move_san("e4")
    gs.apply_move_san("d5")
    gs.apply_move_san("exd5")

    assert len(gs.captured) == 1
    assert gs.captured[0] == "p"  # Black pawn captured


def test_status_text():
    """Verify status text generation for normal, check, and checkmate."""
    gs = GameState()
    assert "White's turn" in gs.get_status_text()

    # Scholar's mate
    gs.apply_move_san("e4")
    gs.apply_move_san("e5")
    gs.apply_move_san("Bc4")
    gs.apply_move_san("Nc6")
    gs.apply_move_san("Qh5")
    gs.apply_move_san("Nf6")
    gs.apply_move_san("Qxf7#")

    assert gs.is_game_over() is True
    assert "Checkmate" in gs.get_status_text()
