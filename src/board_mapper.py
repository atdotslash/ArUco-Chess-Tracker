"""Mapping detected ArUco markers to chessboard squares using homography."""

from dataclasses import dataclass, field
import logging
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.aruco_detector import DetectedMarker
from src.config import PIECE_ID_MIN, PIECE_ID_MAX
from src.homography import pixel_to_board, board_to_square, square_to_board_center

logger = logging.getLogger(__name__)


@dataclass
class BoardMappingResult:
    """Encapsulates the mapped positions of all detected piece markers."""

    marker_to_square: Dict[int, str] = field(default_factory=dict)
    square_to_marker: Dict[str, int] = field(default_factory=dict)
    offboard_markers: List[int] = field(default_factory=list)
    marker_board_coords: Dict[int, Tuple[float, float]] = field(default_factory=dict)
    conflicts: Dict[str, List[int]] = field(default_factory=dict)


class BoardMapper:
    """Translates pixel positions of detected markers to chessboard squares."""

    def __init__(self) -> None:
        pass

    def map_markers_to_board(
        self,
        markers: List[DetectedMarker],
        H: Optional[np.ndarray],
    ) -> BoardMappingResult:
        """Map piece markers (IDs 0-31) to squares (a1-h8) via homography matrix H.

        Args:
            markers: List of detected markers.
            H: 3x3 Homography matrix mapping pixels to board coordinates [0, 8] x [0, 8].

        Returns:
            BoardMappingResult object.
        """
        result = BoardMappingResult()
        if H is None:
            return result

        # First pass: map each piece marker to continuous board coordinates and square
        candidates_by_square: Dict[str, List[Tuple[int, float]]] = {}

        for m in markers:
            # Only process piece markers
            if not (PIECE_ID_MIN <= m.id <= PIECE_ID_MAX):
                continue

            bx, by = pixel_to_board(m.center, H)
            result.marker_board_coords[m.id] = (bx, by)

            sq = board_to_square((bx, by))
            if sq is None:
                result.offboard_markers.append(m.id)
                continue

            center_bx, center_by = square_to_board_center(sq)  # type: ignore[misc]
            dist_to_center = math.hypot(bx - center_bx, by - center_by)

            if sq not in candidates_by_square:
                candidates_by_square[sq] = []
            candidates_by_square[sq].append((m.id, dist_to_center))

        # Second pass: resolve any multiple markers claiming the same square
        for sq, candidates in candidates_by_square.items():
            if len(candidates) == 1:
                mid, _ = candidates[0]
                result.marker_to_square[mid] = sq
                result.square_to_marker[sq] = mid
            else:
                # Multiple markers on same square: sort by distance to square center
                candidates.sort(key=lambda item: item[1])
                winner_id, _ = candidates[0]
                result.marker_to_square[winner_id] = sq
                result.square_to_marker[sq] = winner_id
                result.conflicts[sq] = [c[0] for c in candidates]
                logger.warning(
                    "Conflict on square %s between markers %s. Assigned to %d.",
                    sq,
                    [c[0] for c in candidates],
                    winner_id,
                )
                for loser_id, _ in candidates[1:]:
                    result.offboard_markers.append(loser_id)

        return result
