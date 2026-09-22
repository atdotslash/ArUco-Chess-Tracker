"""Chess game state management and move validation using python-chess."""

import copy
import logging
from typing import Dict, List, Optional, Tuple
import chess

from src.config import (
    DEFAULT_MARKER_TO_PIECE,
    STANDARD_STARTING_SQUARES,
    PIECE_NAMES,
)

logger = logging.getLogger(__name__)


class GameState:
    """Manages the chess board rules, move legality, FEN generation, and marker-piece bindings."""

    def __init__(
        self,
        marker_to_piece: Optional[Dict[int, str]] = None,
        initial_fen: Optional[str] = None,
    ) -> None:
        self.board: chess.Board = chess.Board(fen=initial_fen) if initial_fen else chess.Board()
        self.marker_to_piece: Dict[int, str] = (
            copy.deepcopy(marker_to_piece) if marker_to_piece is not None else copy.deepcopy(DEFAULT_MARKER_TO_PIECE)
        )
        self.captured: List[str] = []
        self.move_history: List[str] = []  # SAN moves

    def reset(self, fen: Optional[str] = None) -> None:
        """Reset game to starting standard position or custom FEN."""
        self.board = chess.Board(fen=fen) if fen else chess.Board()
        self.captured.clear()
        self.move_history.clear()
        logger.info("GameState reset. FEN: %s", self.board.fen())

    def auto_assign_from_standard_position(
        self, marker_to_square: Dict[int, str]
    ) -> Tuple[int, List[int]]:
        """Assign marker IDs to pieces based on current marker squares and standard chess layout.

        Returns:
            Tuple of (assigned_count, unassigned_markers_list)
        """
        # Map starting square to piece symbol from a fresh chess board
        std_board = chess.Board()
        square_to_piece: Dict[str, str] = {}
        for sq_idx in chess.SQUARES:
            piece = std_board.piece_at(sq_idx)
            if piece:
                sq_name = chess.square_name(sq_idx)
                square_to_piece[sq_name] = piece.symbol()

        assigned_count = 0
        unassigned: List[int] = []

        for mid, sq in marker_to_square.items():
            if sq in square_to_piece:
                piece_sym = square_to_piece[sq]
                self.marker_to_piece[mid] = piece_sym
                assigned_count += 1
            else:
                unassigned.append(mid)

        logger.info(
            "Auto-assigned %d markers to pieces. %d unassigned.",
            assigned_count,
            len(unassigned),
        )
        return assigned_count, unassigned

    def validate_move(
        self, from_sq: str, to_sq: str, promotion: Optional[str] = None
    ) -> Optional[chess.Move]:
        """Validate whether a move from from_sq to to_sq is legal under current chess rules.

        Returns:
            chess.Move object if legal, None otherwise.
        """
        try:
            from_idx = chess.parse_square(from_sq.lower())
            to_idx = chess.parse_square(to_sq.lower())
        except ValueError:
            return None

        # Check if piece is moving
        piece = self.board.piece_at(from_idx)
        if piece is None:
            return None

        # Check for promotion if a pawn reaches the last rank
        is_pawn = piece.piece_type == chess.PAWN
        is_promo_rank = (piece.color == chess.WHITE and chess.square_rank(to_idx) == 7) or (
            piece.color == chess.BLACK and chess.square_rank(to_idx) == 0
        )

        promo_type = None
        if is_pawn and is_promo_rank:
            if promotion:
                promo_char = promotion.lower()[0]
                promo_map = {
                    "q": chess.QUEEN,
                    "r": chess.ROOK,
                    "b": chess.BISHOP,
                    "n": chess.KNIGHT,
                }
                promo_type = promo_map.get(promo_char, chess.QUEEN)
            else:
                promo_type = chess.QUEEN  # Default queen promotion

        candidate_move = chess.Move(from_idx, to_idx, promotion=promo_type)
        if self.board.is_legal(candidate_move):
            return candidate_move

        return None

    def apply_move(self, move: chess.Move) -> bool:
        """Push a legal move to the chess board, updating history and captured pieces."""
        if not self.board.is_legal(move):
            logger.warning("Attempted to apply illegal move: %s", move)
            return False

        # Check if target square was occupied (capture)
        target_piece = self.board.piece_at(move.to_square)
        if target_piece:
            self.captured.append(target_piece.symbol())
        elif self.board.is_en_passant(move):
            # En passant capture
            captured_pawn = "p" if self.board.turn == chess.WHITE else "P"
            self.captured.append(captured_pawn)

        san = self.board.san(move)
        self.move_history.append(san)
        self.board.push(move)
        logger.info("Move applied: %s (%s). New FEN: %s", san, move.uci(), self.board.fen())
        return True

    def apply_move_san(self, san: str) -> Optional[chess.Move]:
        """Parse SAN move string, validate, and apply to board."""
        try:
            move = self.board.parse_san(san)
            if self.apply_move(move):
                return move
        except Exception as e:
            logger.warning("Failed to parse/apply SAN move '%s': %s", san, e)
        return None

    def get_fen(self) -> str:
        """Return the current Forsyth-Edwards Notation (FEN) string."""
        return self.board.fen()

    def get_last_move(self) -> Optional[str]:
        """Return the last played move in SAN format, or None."""
        return self.move_history[-1] if self.move_history else None

    def get_turn(self) -> str:
        """Return 'white' or 'black' representing the active player's turn."""
        return "white" if self.board.turn == chess.WHITE else "black"

    def is_game_over(self) -> bool:
        """Return True if checkmate, stalemate, or draw."""
        return self.board.is_game_over()

    def get_captured_pieces(self) -> List[str]:
        """Return list of captured piece symbols ('P', 'r', etc.)."""
        return list(self.captured)

    def get_status_text(self) -> str:
        """Return human-readable game state description."""
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"Checkmate! {winner} wins."
        if self.board.is_stalemate():
            return "Draw by stalemate."
        if self.board.is_insufficient_material():
            return "Draw by insufficient material."
        if self.board.is_fivefold_repetition() or self.board.is_seventyfive_moves():
            return "Draw by repetition / 75-move rule."
        if self.board.is_check():
            turn_str = "White" if self.board.turn == chess.WHITE else "Black"
            return f"Check! {turn_str}'s turn."

        turn_str = "White" if self.board.turn == chess.WHITE else "Black"
        return f"{turn_str}'s turn"

    def get_piece_at_square(self, square: str) -> Optional[str]:
        """Return piece symbol at square (e.g. 'P', 'k') or None."""
        try:
            sq_idx = chess.parse_square(square.lower())
            piece = self.board.piece_at(sq_idx)
            return piece.symbol() if piece else None
        except ValueError:
            return None

    def get_board_state_dict(self) -> Dict[str, str]:
        """Return dictionary mapping square names ('e4') to piece symbols ('P')."""
        state: Dict[str, str] = {}
        for sq_idx in chess.SQUARES:
            piece = self.board.piece_at(sq_idx)
            if piece:
                state[chess.square_name(sq_idx)] = piece.symbol()
        return state
