"""Move detection from successive board frames with stability verification and legality checks."""

from dataclasses import dataclass
import logging
from typing import Dict, List, Optional, Set, Tuple
import chess
import numpy as np

from src.aruco_detector import DetectedMarker
from src.game_state import GameState

logger = logging.getLogger(__name__)


@dataclass
class MoveDetectionResult:
    """Result of analyzing a frame for move occurrences."""

    move: Optional[chess.Move] = None
    san: Optional[str] = None
    is_legal: bool = False
    is_stable: bool = False
    status_message: str = "Awaiting move"
    from_square: Optional[str] = None
    to_square: Optional[str] = None


class MoveDetector:
    """Detects moves by tracking frame-by-frame stability and resolving square state deltas."""

    def __init__(self, stable_frames_threshold: int = 5) -> None:
        self.stable_frames_threshold = stable_frames_threshold

        self._consecutive_stable_count = 0
        self._last_detected_layout: Optional[Dict[str, int]] = None  # square -> marker_id
        self._confirmed_layout: Optional[Dict[str, int]] = None
        self._last_processed_move_uci: Optional[str] = None

    def reset_baseline(self, current_square_to_marker: Dict[str, int]) -> None:
        """Explicitly set the confirmed baseline layout (e.g. at game start or board reset)."""
        self._confirmed_layout = dict(current_square_to_marker)
        self._last_detected_layout = dict(current_square_to_marker)
        self._consecutive_stable_count = self.stable_frames_threshold
        self._last_processed_move_uci = None

    def process_frame(
        self,
        current_square_to_marker: Dict[str, int],
        game_state: GameState,
    ) -> MoveDetectionResult:
        """Evaluate current frame's detected markers against previous frames and GameState.

        Args:
            current_square_to_marker: Mapping of algebraic square ('e4') -> marker ID.
            game_state: Current GameState instance.

        Returns:
            MoveDetectionResult detailing stability and detected move if any.
        """
        if self._confirmed_layout is None:
            self.reset_baseline(current_square_to_marker)
            return MoveDetectionResult(
                is_stable=True,
                status_message="Baseline initialized",
            )

        # Check frame stability: does current layout exactly match the previous frame's layout?
        if current_square_to_marker == self._last_detected_layout:
            self._consecutive_stable_count += 1
        else:
            self._consecutive_stable_count = 1
            self._last_detected_layout = dict(current_square_to_marker)

        is_stable = self._consecutive_stable_count >= self.stable_frames_threshold

        if not is_stable:
            return MoveDetectionResult(
                is_stable=False,
                status_message=f"Board in motion ({self._consecutive_stable_count}/{self.stable_frames_threshold} stable frames)",
            )

        # If stable and layout is identical to our confirmed baseline, no move has occurred
        if current_square_to_marker == self._confirmed_layout:
            return MoveDetectionResult(
                is_stable=True,
                status_message="Board stable, awaiting move",
            )

        # Board is stable and differs from confirmed baseline! Analyze the diff:
        diff_result = self._analyze_difference(
            old_layout=self._confirmed_layout,
            new_layout=current_square_to_marker,
            game_state=game_state,
        )

        if diff_result.move and diff_result.is_legal:
            # Legal move detected: update confirmed baseline layout
            self._confirmed_layout = dict(current_square_to_marker)
            self._last_processed_move_uci = diff_result.move.uci()
            logger.info("Confirmed stable move: %s (%s)", diff_result.san, diff_result.move.uci())

        return diff_result

    def _analyze_difference(
        self,
        old_layout: Dict[str, int],
        new_layout: Dict[str, int],
        game_state: GameState,
    ) -> MoveDetectionResult:
        """Classify changes between old and new stable layouts into candidate chess moves."""
        old_squares = set(old_layout.keys())
        new_squares = set(new_layout.keys())

        # Squares that lost their pieces
        vacated_squares = list(old_squares - new_squares)
        # Squares that gained a piece
        newly_occupied_squares = list(new_squares - old_squares)
        # Squares that kept a piece, but the marker ID changed (e.g. piece captured and replaced)
        replaced_squares = [sq for sq in (old_squares & new_squares) if old_layout[sq] != new_layout[sq]]

        # Candidate from/to squares
        from_candidates = list(vacated_squares)
        to_candidates = list(newly_occupied_squares) + list(replaced_squares)

        # 1. Check Castling (King moves 2 squares, Rook moves across)
        castling_move = self._check_castling(from_candidates, to_candidates, old_layout, new_layout, game_state)
        if castling_move:
            san = game_state.board.san(castling_move)
            return MoveDetectionResult(
                move=castling_move,
                san=san,
                is_legal=True,
                is_stable=True,
                status_message=f"Castling detected: {san}",
                from_square=chess.square_name(castling_move.from_square),
                to_square=chess.square_name(castling_move.to_square),
            )

        # 2. Check Standard Move or Capture (1 from square, 1 to square)
        if len(from_candidates) == 1 and len(to_candidates) == 1:
            from_sq = from_candidates[0]
            to_sq = to_candidates[0]

            candidate_move = game_state.validate_move(from_sq, to_sq)
            if candidate_move:
                san = game_state.board.san(candidate_move)
                return MoveDetectionResult(
                    move=candidate_move,
                    san=san,
                    is_legal=True,
                    is_stable=True,
                    status_message=f"Move detected: {san}",
                    from_square=from_sq,
                    to_square=to_sq,
                )
            else:
                return MoveDetectionResult(
                    is_legal=False,
                    is_stable=True,
                    status_message=f"Illegal move attempted: {from_sq} -> {to_sq}",
                    from_square=from_sq,
                    to_square=to_sq,
                )

        # 3. Check En Passant (Pawn moved diagonally to empty square, enemy pawn vacated adjacent square)
        if len(from_candidates) == 2 and len(to_candidates) == 1:
            ep_move = self._check_en_passant(from_candidates, to_candidates[0], game_state)
            if ep_move:
                san = game_state.board.san(ep_move)
                return MoveDetectionResult(
                    move=ep_move,
                    san=san,
                    is_legal=True,
                    is_stable=True,
                    status_message=f"En passant detected: {san}",
                    from_square=chess.square_name(ep_move.from_square),
                    to_square=chess.square_name(ep_move.to_square),
                )

        return MoveDetectionResult(
            is_legal=False,
            is_stable=True,
            status_message=f"Ambiguous board change (vacated={from_candidates}, occupied={to_candidates})",
        )

    def _check_castling(
        self,
        from_candidates: List[str],
        to_candidates: List[str],
        old_layout: Dict[str, int],
        new_layout: Dict[str, int],
        game_state: GameState,
    ) -> Optional[chess.Move]:
        """Verify if layout delta matches White or Black castling."""
        castling_definitions = [
            # (king_from, king_to, rook_from, rook_to)
            ("e1", "g1", "h1", "f1"),  # White kingside
            ("e1", "c1", "a1", "d1"),  # White queenside
            ("e8", "g8", "h8", "f8"),  # Black kingside
            ("e8", "c8", "a8", "d8"),  # Black queenside
        ]

        from_set = set(from_candidates)
        to_set = set(to_candidates)

        for k_from, k_to, r_from, r_to in castling_definitions:
            if {k_from, r_from} == from_set and {k_to, r_to} == to_set:
                candidate = game_state.validate_move(k_from, k_to)
                if candidate and game_state.board.is_castling(candidate):
                    return candidate

        return None

    def _check_en_passant(
        self,
        from_candidates: List[str],
        to_sq: str,
        game_state: GameState,
    ) -> Optional[chess.Move]:
        """Verify if layout delta matches en passant pawn capture."""
        for from_sq in from_candidates:
            candidate = game_state.validate_move(from_sq, to_sq)
            if candidate and game_state.board.is_en_passant(candidate):
                return candidate
        return None


def detect_move(
    prev_markers: List["DetectedMarker"],
    curr_markers: List["DetectedMarker"],
    H: Optional[np.ndarray] = None,
    game_state: Optional[GameState] = None,
) -> Optional[chess.Move]:
    """Compare two frames of detected markers and return the legal chess move detected, or None.

    Specified in section 8.2 of the project specification.
    """
    from src.board_mapper import BoardMapper
    from src.homography import compute_board_homography

    if H is None:
        corner_pixels = {m.id: m.center for m in curr_markers if m.id in (100, 101, 102, 103)}
        if len(corner_pixels) < 4:
            corner_pixels = {m.id: m.center for m in prev_markers if m.id in (100, 101, 102, 103)}
        H = compute_board_homography(corner_pixels)

    if H is None:
        return None

    mapper = BoardMapper()
    prev_map = mapper.map_markers_to_board(prev_markers, H)
    curr_map = mapper.map_markers_to_board(curr_markers, H)

    if game_state is None:
        game_state = GameState()

    detector = MoveDetector(stable_frames_threshold=1)
    detector.reset_baseline(prev_map.square_to_marker)
    res = detector.process_frame(curr_map.square_to_marker, game_state)
    return res.move if (res and res.is_legal) else None
