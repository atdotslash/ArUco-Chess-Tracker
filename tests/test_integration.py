"""End-to-end integration test validating camera, vision pipeline, move detection, and TCP API."""

import socket
import time
import pytest

from src.camera import Camera
from src.aruco_detector import ArucoDetectorWrapper
from src.homography import HomographyManager
from src.board_mapper import BoardMapper
from src.game_state import GameState
from src.move_detector import MoveDetector
from src.api import ChessTrackerAPI, TCPServerManager


def test_full_pipeline_simulation():
    """Simulate full camera stream, ArUco detection, homography, move detection, and TCP queries."""
    cam = Camera(synthetic=True, width=1280, height=720)
    assert cam.start() is True

    detector = ArucoDetectorWrapper()
    homography_mgr = HomographyManager()
    board_mapper = BoardMapper()
    game_state = GameState()
    move_detector = MoveDetector(stable_frames_threshold=3)

    test_port = 5577
    api = ChessTrackerAPI(game_state)
    tcp = TCPServerManager(api, port=test_port)
    assert tcp.start() is True

    time.sleep(0.2)

    try:
        # Step 1: Establish baseline with 32 starting pieces
        mapping = None
        for _ in range(6):
            ret, frame = cam.read()
            assert ret is True
            markers = detector.detect_markers(frame)
            corners = {m.id: m.center for m in markers if m.id in (100, 101, 102, 103)}
            H = homography_mgr.update(corners)
            mapping = board_mapper.map_markers_to_board(markers, H)
            move_detector.process_frame(mapping.square_to_marker, game_state)
            time.sleep(0.02)

        assert mapping is not None
        assert len(mapping.square_to_marker) == 32

        # Step 2: Physical move simulation (White pawn marker 4 moves from e2 to e4)
        cam.synthetic_generator.set_piece_position(4, "e4")

        detected_move_result = None
        for _ in range(8):
            ret, frame = cam.read()
            markers = detector.detect_markers(frame)
            corners = {m.id: m.center for m in markers if m.id in (100, 101, 102, 103)}
            H = homography_mgr.update(corners)
            mapping = board_mapper.map_markers_to_board(markers, H)
            res = move_detector.process_frame(mapping.square_to_marker, game_state)
            if res.move and res.is_legal:
                detected_move_result = res
                game_state.apply_move(res.move)
                break
            time.sleep(0.02)

        assert detected_move_result is not None
        assert detected_move_result.san == "e4"
        assert game_state.get_last_move() == "e4"
        assert game_state.get_turn() == "black"

        # Step 3: Verify TCP server answers with matching state
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2.0)
            sock.connect(("127.0.0.1", test_port))

            sock.sendall(b"GET_LAST_MOVE\n")
            last_move_tcp = sock.recv(1024).decode().strip()
            assert last_move_tcp == "e4"

            sock.sendall(b"GET_FEN\n")
            fen_tcp = sock.recv(1024).decode().strip()
            assert "4P3" in fen_tcp
            assert fen_tcp == game_state.get_fen()

    finally:
        tcp.stop()
        cam.stop()
