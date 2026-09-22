"""Unit tests for ArUco marker detection, deduplication, and smoothing."""

import cv2
import numpy as np
import pytest

from src.aruco_detector import ArucoDetectorWrapper, DetectedMarker
from src.markers import generate_marker, get_aruco_dict


def test_detect_single_and_corner_markers():
    """Verify detection of piece markers and corner markers on synthetic image."""
    detector = ArucoDetectorWrapper(dict_name="DICT_4X4_250")

    # Create canvas
    canvas = np.full((600, 800, 3), 255, dtype=np.uint8)

    # Place marker 0 (White pawn) at (100, 100)
    m0 = np.array(generate_marker(0, marker_size_px=100, border_px=20))
    canvas[100:240, 100:240] = cv2.cvtColor(m0, cv2.COLOR_RGB2BGR)

    # Place marker 15 (White king) at (300, 100)
    m15 = np.array(generate_marker(15, marker_size_px=100, border_px=20))
    canvas[100:240, 300:440] = cv2.cvtColor(m15, cv2.COLOR_RGB2BGR)

    # Place marker 102 (Corner a8) at (100, 300)
    m102 = np.array(generate_marker(102, marker_size_px=100, border_px=20))
    canvas[300:440, 100:240] = cv2.cvtColor(m102, cv2.COLOR_RGB2BGR)

    detected = detector.detect_markers(canvas)
    detected_ids = {m.id for m in detected}

    assert 0 in detected_ids
    assert 15 in detected_ids
    assert 102 in detected_ids
    assert len(detected) == 3

    # Check center accuracy for marker 0 (center of 100:240 is 170)
    m0_detected = next(m for m in detected if m.id == 0)
    cx, cy = m0_detected.center
    assert abs(cx - 170) < 5
    assert abs(cy - 170) < 5


def test_filter_unexpected_marker_ids():
    """Verify markers outside 0-31 and 100-103 are ignored."""
    detector = ArucoDetectorWrapper()
    canvas = np.full((400, 400, 3), 255, dtype=np.uint8)

    # ID 50 is outside piece range (0-31) and not a corner (100-103)
    m50 = np.array(generate_marker(50, marker_size_px=100, border_px=20))
    canvas[50:190, 50:190] = cv2.cvtColor(m50, cv2.COLOR_RGB2BGR)

    detected = detector.detect_markers(canvas)
    assert len(detected) == 0


def test_duplicate_marker_resolution():
    """Verify duplicate marker detection retains candidate with largest area."""
    detector = ArucoDetectorWrapper()
    canvas = np.full((600, 600, 3), 255, dtype=np.uint8)

    # Place small marker 7 at (50, 50)
    m_small = np.array(generate_marker(7, marker_size_px=50, border_px=10))
    canvas[50:120, 50:120] = cv2.cvtColor(m_small, cv2.COLOR_RGB2BGR)

    # Place large marker 7 at (200, 200)
    m_large = np.array(generate_marker(7, marker_size_px=120, border_px=20))
    canvas[200:360, 200:360] = cv2.cvtColor(m_large, cv2.COLOR_RGB2BGR)

    detected = detector.detect_markers(canvas)
    assert len(detected) == 1
    marker7 = detected[0]
    assert marker7.id == 7
    # Center should be closer to the large marker (~280, ~280)
    assert marker7.center[0] > 200
    assert marker7.center[1] > 200


def test_temporal_smoothing_and_loss():
    """Verify temporal smoothing and clearing of lost markers."""
    detector = ArucoDetectorWrapper(smoothing_alpha=0.5, lost_frames_threshold=3)

    canvas1 = np.full((400, 400, 3), 255, dtype=np.uint8)
    m1 = np.array(generate_marker(1, marker_size_px=80, border_px=20))
    canvas1[50:170, 50:170] = cv2.cvtColor(m1, cv2.COLOR_RGB2BGR)

    det1 = detector.detect_markers(canvas1)
    assert len(det1) == 1
    c1 = det1[0].center

    # Frame 2: shift position slightly
    canvas2 = np.full((400, 400, 3), 255, dtype=np.uint8)
    canvas2[60:180, 60:180] = cv2.cvtColor(m1, cv2.COLOR_RGB2BGR)

    det2 = detector.detect_markers(canvas2)
    assert len(det2) == 1
    c2 = det2[0].center

    # Due to smoothing_alpha=0.5, position should be between c1 and raw ~120
    assert c1[0] < c2[0] < 125

    # Simulate empty frames to test loss threshold
    empty_frame = np.full((400, 400, 3), 255, dtype=np.uint8)
    for _ in range(4):
        detector.detect_markers(empty_frame)

    assert 1 not in detector._smoothed_corners


def test_module_level_detect_markers_and_generate_marker_args():
    """Verify module-level detect_markers function and generate_marker parameter compatibility."""
    from src.aruco_detector import detect_markers
    import cv2

    img = generate_marker(10, size_px=100, border_px=15, dictionary=cv2.aruco.DICT_4X4_250)
    canvas = np.full((300, 300, 3), 255, dtype=np.uint8)
    canvas[50:180, 50:180] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    markers = detect_markers(canvas)
    assert len(markers) == 1
    assert markers[0].id == 10
