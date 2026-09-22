"""Unit tests for camera capture and ChArUco calibration."""

import cv2
import numpy as np
import pytest
from pathlib import Path

from src.camera import Camera, SyntheticBoardGenerator
from src.calibration import CharucoCalibrator
from src.markers import generate_charuco_board_image


def test_synthetic_camera_frame_generation():
    """Verify synthetic board generator renders valid 3-channel frames."""
    gen = SyntheticBoardGenerator(width=640, height=480)
    frame = gen.render_frame()

    assert frame is not None
    assert frame.shape == (480, 640, 3)
    assert frame.dtype == np.uint8
    # Ensure it's not all black
    assert np.mean(frame) > 10


def test_camera_synthetic_mode_lifecycle():
    """Verify Camera class starts, reads frames, and stops gracefully in synthetic mode."""
    cam = Camera(source=0, width=640, height=480, fps=30, synthetic=True)
    assert cam.start() is True
    assert cam.is_opened() is True

    # Allow grabber thread to grab a frame
    import time
    time.sleep(0.1)
    ret, frame = cam.read()
    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)

    cam.stop()
    assert cam.is_opened() is False


def test_charuco_calibration_pipeline(tmp_path: Path):
    """Test full calibration pipeline: corner detection, calibration, save/load, and undistort."""
    calib = CharucoCalibrator()
    base_board = np.array(generate_charuco_board_image(image_size=(800, 600)))

    # Collect frames under slight transformations
    angles = [0, 6, -6, 12]
    for angle in angles:
        M = cv2.getRotationMatrix2D((400, 300), angle, 0.9)
        warped = cv2.warpAffine(base_board, M, (800, 600), borderValue=(255, 255, 255))
        ok, count = calib.add_frame(warped)
        assert ok is True
        assert count >= 12

    assert calib.get_frame_count() == len(angles)

    rms, camera_matrix, dist_coeffs = calib.calibrate()
    assert rms < 1.0  # Synthetic reprojection error should be very low
    assert camera_matrix.shape == (3, 3)
    assert dist_coeffs.shape == (1, 5)

    # Test saving and loading calibration
    save_path = tmp_path / "test_camera_params.npz"
    assert CharucoCalibrator.save_calibration(save_path, camera_matrix, dist_coeffs, rms) is True
    assert save_path.exists()

    loaded = CharucoCalibrator.load_calibration(save_path)
    assert loaded is not None
    k_loaded, d_loaded, rms_loaded = loaded
    np.testing.assert_allclose(camera_matrix, k_loaded)
    np.testing.assert_allclose(dist_coeffs, d_loaded)
    assert abs(rms - rms_loaded) < 1e-4

    # Test undistort
    undistorted = CharucoCalibrator.undistort(base_board, camera_matrix, dist_coeffs)
    assert undistorted.shape == base_board.shape
