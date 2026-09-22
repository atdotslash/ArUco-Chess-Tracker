"""ArUco marker detection with subpixel corner refinement, jitter filtering, and pose estimation."""

from dataclasses import dataclass
import logging
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.config import (
    DEFAULT_ARUCO_DICT_NAME,
    PIECE_ID_MIN,
    PIECE_ID_MAX,
    CORNER_IDS,
    PIECE_MARKER_SIZE_M,
    CORNER_MARKER_SIZE_M,
)
from src.markers import get_aruco_dict

logger = logging.getLogger(__name__)


@dataclass
class DetectedMarker:
    """Represents a detected ArUco marker with corner geometry and optional 3D pose."""

    id: int
    corners: np.ndarray  # Shape (4, 2) in pixels (float32)
    center: Tuple[float, float]  # (cx, cy) in pixels
    area: float
    rvec: Optional[np.ndarray] = None  # (3, 1) rotation vector
    tvec: Optional[np.ndarray] = None  # (3, 1) translation vector


class ArucoDetectorWrapper:
    """High-level ArUco detector handling subpixel refinement, filtering, and smoothing."""

    def __init__(
        self,
        dict_name: str = DEFAULT_ARUCO_DICT_NAME,
        smoothing_alpha: float = 0.6,
        lost_frames_threshold: int = 5,
    ) -> None:
        self.dict_name = dict_name
        self.smoothing_alpha = smoothing_alpha  # 1.0 = no smoothing, lower = smoother
        self.lost_frames_threshold = lost_frames_threshold

        self.dictionary = get_aruco_dict(dict_name)
        self.parameters = cv2.aruco.DetectorParameters()
        self._configure_parameters()
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)

        # Temporal smoothing state: marker_id -> previous corners (4, 2)
        self._smoothed_corners: Dict[int, np.ndarray] = {}
        # Tracking frame loss: marker_id -> consecutive frames not seen
        self._missing_counts: Dict[int, int] = {}

    def _configure_parameters(self) -> None:
        """Set optimal detection parameters specified in project requirements."""
        self.parameters.adaptiveThreshWinSizeMin = 3
        self.parameters.adaptiveThreshWinSizeMax = 23
        self.parameters.adaptiveThreshWinSizeStep = 10
        self.parameters.minMarkerPerimeterRate = 0.03
        self.parameters.maxMarkerPerimeterRate = 4.0
        self.parameters.polygonalApproxAccuracyRate = 0.03
        self.parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

    def detect_markers(
        self,
        frame: np.ndarray,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None,
    ) -> List[DetectedMarker]:
        """Detect valid pieces and board corner markers on the given frame.

        Args:
            frame: BGR or grayscale image.
            camera_matrix: Optional 3x3 camera intrinsic matrix for pose estimation.
            dist_coeffs: Optional distortion coefficients for pose estimation.

        Returns:
            List of DetectedMarker objects with valid IDs.
        """
        if frame is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        corners_list, ids_array, rejected = self.detector.detectMarkers(gray)

        if ids_array is None or len(corners_list) == 0:
            self._update_missing_markers(set())
            return []

        # Raw detected markers grouping by ID for duplicate resolution
        candidates_by_id: Dict[int, List[np.ndarray]] = {}
        for corners_item, marker_id in zip(corners_list, ids_array.flatten()):
            mid = int(marker_id)
            # Only accept expected IDs (pieces 0-31 or board corners 100-103)
            if not ((PIECE_ID_MIN <= mid <= PIECE_ID_MAX) or (mid in CORNER_IDS)):
                continue

            pts = corners_item.reshape(4, 2).astype(np.float32)
            if mid not in candidates_by_id:
                candidates_by_id[mid] = []
            candidates_by_id[mid].append(pts)

        detected_set = set(candidates_by_id.keys())
        self._update_missing_markers(detected_set)

        results: List[DetectedMarker] = []
        for mid, pts_list in candidates_by_id.items():
            # If duplicate markers are detected with same ID, choose candidate with largest area
            if len(pts_list) > 1:
                logger.warning("Duplicate marker ID %d detected (%d times). Choosing largest area.", mid, len(pts_list))
                pts_list.sort(key=lambda p: cv2.contourArea(p), reverse=True)

            best_pts = pts_list[0]
            area = float(cv2.contourArea(best_pts))

            # Apply temporal exponential smoothing on corners
            if mid in self._smoothed_corners and self.smoothing_alpha < 1.0:
                smoothed = self.smoothing_alpha * best_pts + (1.0 - self.smoothing_alpha) * self._smoothed_corners[mid]
            else:
                smoothed = best_pts
            self._smoothed_corners[mid] = smoothed

            # Compute marker center
            cx = float(np.mean(smoothed[:, 0]))
            cy = float(np.mean(smoothed[:, 1]))

            # Pose estimation if camera intrinsics are available
            rvec, tvec = None, None
            if camera_matrix is not None and dist_coeffs is not None:
                rvec, tvec = self._estimate_marker_pose(smoothed, mid, camera_matrix, dist_coeffs)

            results.append(
                DetectedMarker(
                    id=mid,
                    corners=smoothed,
                    center=(cx, cy),
                    area=area,
                    rvec=rvec,
                    tvec=tvec,
                )
            )

        return results

    def _estimate_marker_pose(
        self,
        corners: np.ndarray,
        marker_id: int,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Estimate 6DoF pose for a single square marker."""
        size = CORNER_MARKER_SIZE_M if marker_id in CORNER_IDS else PIECE_MARKER_SIZE_M
        # Object coordinates centered at marker center in OpenCV order
        half = size / 2.0
        obj_pts = np.float32([
            [-half, half, 0.0],
            [half, half, 0.0],
            [half, -half, 0.0],
            [-half, -half, 0.0],
        ])

        try:
            success, rvec, tvec = cv2.solvePnP(
                obj_pts,
                corners,
                camera_matrix,
                dist_coeffs,
                False,
                cv2.SOLVEPNP_IPPE_SQUARE,
            )
            if success:
                return rvec, tvec
        except Exception as e:
            logger.debug("solvePnP failed for marker %d: %s", marker_id, e)
        return None, None

    def _update_missing_markers(self, detected_ids: set[int]) -> None:
        """Track which markers were not seen and prune stale smoothing states."""
        # For all currently tracked markers not in detected_ids
        for mid in list(self._smoothed_corners.keys()):
            if mid not in detected_ids:
                count = self._missing_counts.get(mid, 0) + 1
                self._missing_counts[mid] = count
                if count >= self.lost_frames_threshold:
                    # Marker considered lost; clear smoothing cache
                    del self._smoothed_corners[mid]
                    del self._missing_counts[mid]
            else:
                self._missing_counts[mid] = 0

    @staticmethod
    def draw_markers(
        frame: np.ndarray,
        markers: List[DetectedMarker],
        draw_labels: bool = True,
        draw_axes: bool = False,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Render detected markers with bounding polygons, centers, and IDs onto the frame."""
        output = frame.copy()
        for marker in markers:
            pts = marker.corners.astype(np.int32)
            # Corner polygon
            is_corner = marker.id in CORNER_IDS
            poly_color = (0, 165, 255) if is_corner else (0, 255, 0)  # Orange for corners, green for pieces
            cv2.polylines(output, [pts], True, poly_color, 2, cv2.LINE_AA)

            # Center circle
            cx, cy = int(marker.center[0]), int(marker.center[1])
            cv2.circle(output, (cx, cy), 3, (0, 0, 255), -1)

            # Label
            if draw_labels:
                label = f"ID:{marker.id}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(output, label, (cx - 15, cy - 8), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # 3D Axes if calibrated pose is available
            if draw_axes and marker.rvec is not None and marker.tvec is not None and camera_matrix is not None:
                axis_len = CORNER_MARKER_SIZE_M if is_corner else PIECE_MARKER_SIZE_M
                cv2.drawFrameAxes(output, camera_matrix, dist_coeffs, marker.rvec, marker.tvec, axis_len)

        return output
