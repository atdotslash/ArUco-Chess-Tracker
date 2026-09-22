"""Camera calibration using ChArUco boards and lens distortion correction."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.config import (
    CHARUCO_SQUARES_X,
    CHARUCO_SQUARES_Y,
    CHARUCO_SQUARE_LENGTH_M,
    CHARUCO_MARKER_LENGTH_M,
    CHARUCO_DICT_NAME,
    MAX_ACCEPTABLE_RMS_ERROR,
)
from src.markers import get_aruco_dict
from src.utils.paths import get_default_calibration_path

logger = logging.getLogger(__name__)


class CharucoCalibrator:
    """Manages ChArUco board detection, frame collection, camera matrix calibration, and persistence."""

    def __init__(
        self,
        squares_x: int = CHARUCO_SQUARES_X,
        squares_y: int = CHARUCO_SQUARES_Y,
        square_len: float = CHARUCO_SQUARE_LENGTH_M,
        marker_len: float = CHARUCO_MARKER_LENGTH_M,
        dict_name: str = CHARUCO_DICT_NAME,
        min_corners_for_valid_frame: int = 6,
    ) -> None:
        self.squares_x = squares_x
        self.squares_y = squares_y
        self.square_len = square_len
        self.marker_len = marker_len
        self.dict_name = dict_name
        self.min_corners = min_corners_for_valid_frame

        self.dictionary = get_aruco_dict(dict_name)
        self.board = cv2.aruco.CharucoBoard(
            (squares_x, squares_y), square_len, marker_len, self.dictionary
        )
        self.detector = cv2.aruco.CharucoDetector(self.board)

        # Storage for captured calibration frames
        self.all_corners: List[np.ndarray] = []
        self.all_ids: List[np.ndarray] = []
        self.image_size: Optional[Tuple[int, int]] = None  # (width, height)

    def detect_charuco(
        self, frame: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], int]:
        """Detect ChArUco board corners on a given frame.

        Returns:
            Tuple of (charuco_corners, charuco_ids, corner_count)
        """
        if frame is None:
            return None, None, 0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        corners, ids, marker_corners, marker_ids = self.detector.detectBoard(gray)

        count = len(corners) if corners is not None else 0
        return corners, ids, count

    def add_frame(self, frame: np.ndarray) -> Tuple[bool, int]:
        """Attempt to add a frame to the calibration dataset.

        Returns:
            Tuple of (success_boolean, detected_corners_count)
        """
        corners, ids, count = self.detect_charuco(frame)
        if count >= self.min_corners and corners is not None and ids is not None:
            h, w = frame.shape[:2]
            self.image_size = (w, h)
            self.all_corners.append(corners)
            self.all_ids.append(ids)
            return True, count
        return False, count

    def get_frame_count(self) -> int:
        """Return the number of captured valid frames."""
        return len(self.all_corners)

    def reset(self) -> None:
        """Clear all collected calibration frames."""
        self.all_corners.clear()
        self.all_ids.clear()
        self.image_size = None

    def calibrate(self) -> Tuple[float, np.ndarray, np.ndarray]:
        """Compute camera matrix, distortion coefficients, and RMS error.

        Raises:
            ValueError: If fewer than 3 frames have been collected.
        """
        if len(self.all_corners) < 3:
            raise ValueError(
                f"Need at least 3 valid frames to calibrate, got {len(self.all_corners)}"
            )

        if self.image_size is None:
            raise ValueError("Image size is unknown.")

        logger.info(
            "Calibrating camera with %d frames, size=%s...",
            len(self.all_corners),
            self.image_size,
        )

        rms, camera_matrix, dist_coeffs, _, _ = cv2.aruco.calibrateCameraCharuco(
            charucoCorners=self.all_corners,
            charucoIds=self.all_ids,
            board=self.board,
            imageSize=self.image_size,
            cameraMatrix=None,
            distCoeffs=None,
        )

        logger.info("Calibration finished. RMS reprojection error: %.4f px", rms)
        return float(rms), camera_matrix, dist_coeffs

    @staticmethod
    def save_calibration(
        filepath: Path | str,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
        rms: float,
    ) -> bool:
        """Save calibration parameters to a .npz file."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(
                str(path),
                camera_matrix=camera_matrix,
                dist_coeffs=dist_coeffs,
                rms=rms,
            )
            logger.info("Saved calibration to %s", path)
            return True
        except Exception as e:
            logger.error("Failed to save calibration: %s", e)
            return False

    @staticmethod
    def load_calibration(
        filepath: Path | str | None = None,
    ) -> Optional[Tuple[np.ndarray, np.ndarray, float]]:
        """Load calibration parameters from a .npz file.

        Returns:
            Tuple of (camera_matrix, dist_coeffs, rms) or None if file is missing/invalid.
        """
        path = Path(filepath) if filepath else get_default_calibration_path()
        if not path.exists():
            return None

        try:
            data = np.load(str(path))
            camera_matrix = data["camera_matrix"]
            dist_coeffs = data["dist_coeffs"]
            rms = float(data["rms"])
            return camera_matrix, dist_coeffs, rms
        except Exception as e:
            logger.warning("Could not read calibration file at %s: %s", path, e)
            return None

    @staticmethod
    def undistort(
        frame: np.ndarray, camera_matrix: np.ndarray, dist_coeffs: np.ndarray
    ) -> np.ndarray:
        """Correct lens distortion using camera calibration parameters."""
        if camera_matrix is None or dist_coeffs is None:
            return frame
        return cv2.undistort(frame, camera_matrix, dist_coeffs)
