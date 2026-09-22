"""Unit and integration tests for ChessTrackerAPI and TCPServerManager."""

import json
import socket
import time
import pytest

from src.game_state import GameState
from src.api import ChessTrackerAPI, TCPServerManager


def send_tcp_command(host: str, port: int, command: str) -> str:
    """Helper to open client socket, send a command, and read response."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2.0)
        s.connect((host, port))
        s.sendall((command + "\n").encode("utf-8"))
        data = s.recv(4096)
        return data.decode("utf-8").strip()


def test_chess_tracker_api_facade():
    """Verify direct API queries."""
    gs = GameState()
    api = ChessTrackerAPI(gs)

    assert api.get_turn() == "white"
    assert "rnbqkbnr" in api.get_fen()
    assert api.get_last_move() is None
    assert api.is_game_over() is False

    gs.apply_move_san("e4")
    assert api.get_turn() == "black"
    assert api.get_last_move() == "e4"

    state = api.get_board_state()
    assert state["turn"] == "black"
    assert state["last_move"] == "e4"
    assert state["squares"]["e4"] == "P"


def test_tcp_server_commands():
    """Verify network commands over actual local TCP socket."""
    gs = GameState()
    api = ChessTrackerAPI(gs)
    test_port = 5599

    server = TCPServerManager(api=api, host="127.0.0.1", port=test_port)
    assert server.start() is True
    time.sleep(0.1)

    try:
        # PING
        res_ping = send_tcp_command("127.0.0.1", test_port, "PING")
        assert res_ping == "PONG"

        # GET_FEN
        res_fen = send_tcp_command("127.0.0.1", test_port, "GET_FEN")
        assert res_fen == gs.get_fen()

        # GET_LAST_MOVE (none yet)
        res_last = send_tcp_command("127.0.0.1", test_port, "GET_LAST_MOVE")
        assert res_last == "NONE"

        # Apply move and test updated responses
        gs.apply_move_san("e4")
        res_fen2 = send_tcp_command("127.0.0.1", test_port, "GET_FEN")
        assert "4P3" in res_fen2

        res_last2 = send_tcp_command("127.0.0.1", test_port, "GET_LAST_MOVE")
        assert res_last2 == "e4"

        # GET_BOARD_STATE (JSON payload)
        res_json = send_tcp_command("127.0.0.1", test_port, "GET_BOARD_STATE")
        parsed = json.loads(res_json)
        assert parsed["last_move"] == "e4"
        assert parsed["turn"] == "black"

        # Unknown command error
        res_err = send_tcp_command("127.0.0.1", test_port, "FOOBAR")
        assert "ERROR" in res_err

    finally:
        server.stop()
        assert server.is_running() is False
