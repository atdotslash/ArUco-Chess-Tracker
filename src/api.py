"""External API and TCP server for SCARA robotic arm and chess engine communication."""

import json
import logging
import socket
import socketserver
import threading
from typing import Any, Dict, List, Optional

from src.game_state import GameState

logger = logging.getLogger(__name__)


class ChessTrackerAPI:
    """Facade exposing the current chess tracker state for external consumers."""

    def __init__(self, game_state: GameState) -> None:
        self.game_state = game_state

    def get_fen(self) -> str:
        """Return current FEN string."""
        return self.game_state.get_fen()

    def get_board_state(self) -> Dict[str, Any]:
        """Return comprehensive dictionary of board state."""
        return {
            "fen": self.game_state.get_fen(),
            "turn": self.game_state.get_turn(),
            "last_move": self.game_state.get_last_move(),
            "is_game_over": self.game_state.is_game_over(),
            "status": self.game_state.get_status_text(),
            "captured_pieces": self.game_state.get_captured_pieces(),
            "squares": self.game_state.get_board_state_dict(),
        }

    def get_last_move(self) -> Optional[str]:
        """Return last move in SAN or None."""
        return self.game_state.get_last_move()

    def get_captured_pieces(self) -> List[str]:
        """Return list of captured piece symbols."""
        return self.game_state.get_captured_pieces()

    def is_game_over(self) -> bool:
        """Return game over boolean."""
        return self.game_state.is_game_over()

    def get_turn(self) -> str:
        """Return active player's turn ('white' or 'black')."""
        return self.game_state.get_turn()


class _TCPCommandHandler(socketserver.StreamRequestHandler):
    """Handler for line-oriented TCP client commands."""

    def handle(self) -> None:
        api: ChessTrackerAPI = self.server.api  # type: ignore[attr-defined]
        client_address = self.client_address[0]
        logger.debug("TCP connection opened from %s", client_address)

        try:
            for line in self.rfile:
                command = line.decode("utf-8").strip()
                if not command:
                    continue

                response = self._process_command(command, api)
                try:
                    self.wfile.write((response + "\n").encode("utf-8"))
                    self.wfile.flush()
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                    break
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            logger.debug("TCP connection reset by client %s: %s", client_address, e)
        finally:
            logger.debug("TCP connection closed from %s", client_address)

    def _process_command(self, command: str, api: ChessTrackerAPI) -> str:
        cmd_upper = command.upper()
        if cmd_upper == "GET_FEN":
            return api.get_fen()
        elif cmd_upper == "GET_LAST_MOVE":
            last = api.get_last_move()
            return last if last is not None else "NONE"
        elif cmd_upper == "GET_BOARD_STATE":
            return json.dumps(api.get_board_state(), ensure_ascii=False)
        elif cmd_upper == "GET_TURN":
            return api.get_turn()
        elif cmd_upper == "IS_GAME_OVER":
            return "TRUE" if api.is_game_over() else "FALSE"
        elif cmd_upper == "GET_CAPTURED":
            captured = api.get_captured_pieces()
            return ",".join(captured) if captured else "NONE"
        elif cmd_upper == "PING":
            return "PONG"
        else:
            return f"ERROR: Unknown command '{command}'"


class _ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, api: ChessTrackerAPI):
        self.api = api
        super().__init__(server_address, RequestHandlerClass)


class TCPServerManager:
    """Manages the background TCP socket server lifecycle."""

    def __init__(
        self,
        api: ChessTrackerAPI,
        host: str = "127.0.0.1",
        port: int = 5555,
    ) -> None:
        self.api = api
        self.host = host
        self.port = port
        self._server: Optional[_ThreadedTCPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start TCP server on a background thread."""
        if self._server is not None:
            return True

        try:
            self._server = _ThreadedTCPServer(
                (self.host, self.port), _TCPCommandHandler, self.api
            )
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="ChessTrackerTCPServer",
            )
            self._thread.start()
            logger.info("TCP API server started on %s:%d", self.host, self.port)
            return True
        except Exception as e:
            logger.error("Failed to start TCP server on %s:%d: %s", self.host, self.port, e)
            self._server = None
            return False

    def stop(self) -> None:
        """Gracefully shut down TCP server and release port."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
            self._thread = None
            logger.info("TCP API server stopped.")

    def is_running(self) -> bool:
        """Check if server is active."""
        return self._server is not None
