"""Application configuration, constants, and default parameters."""

from typing import Final, Dict, Any

__version__ = "0.1.0"
APP_NAME = "ArUco Chess Tracker"
AUTHOR = "atdotslash"
GITHUB_URL = "https://github.com/atdotslash/ArUco-Chess-Tracker"

# ArUco Dictionary IDs (cv2.aruco.DICT_4X4_250 provides IDs 0-249 without collisions)
DEFAULT_ARUCO_DICT_NAME = "DICT_4X4_250"

# Marker ID ranges and roles
PIECE_ID_MIN: Final[int] = 0
PIECE_ID_MAX: Final[int] = 31

CORNER_ID_A1: Final[int] = 100
CORNER_ID_H1: Final[int] = 101
CORNER_ID_A8: Final[int] = 102
CORNER_ID_H8: Final[int] = 103

CORNER_IDS: Final[tuple[int, ...]] = (
    CORNER_ID_A1,
    CORNER_ID_H1,
    CORNER_ID_A8,
    CORNER_ID_H8,
)

# Standard piece assignment for IDs 0-31
# 0-7: White Pawns (P), 8-9: White Rooks (R), 10-11: White Knights (N),
# 12-13: White Bishops (B), 14: White Queen (Q), 15: White King (K)
# 16-23: Black Pawns (p), 24-25: Black Rooks (r), 26-27: Black Knights (n),
# 28-29: Black Bishops (b), 30: Black Queen (q), 31: Black King (k)
DEFAULT_MARKER_TO_PIECE: Final[Dict[int, str]] = {
    0: "P", 1: "P", 2: "P", 3: "P", 4: "P", 5: "P", 6: "P", 7: "P",
    8: "R", 9: "R",
    10: "N", 11: "N",
    12: "B", 13: "B",
    14: "Q",
    15: "K",
    16: "p", 17: "p", 18: "p", 19: "p", 20: "p", 21: "p", 22: "p", 23: "p",
    24: "r", 25: "r",
    26: "n", 27: "n",
    28: "b", 29: "b",
    30: "q",
    31: "k",
}

PIECE_NAMES: Final[Dict[str, str]] = {
    "P": "White Pawn",
    "R": "White Rook",
    "N": "White Knight",
    "B": "White Bishop",
    "Q": "White Queen",
    "K": "White King",
    "p": "Black Pawn",
    "r": "Black Rook",
    "n": "Black Knight",
    "b": "Black Bishop",
    "q": "Black Queen",
    "k": "Black King",
}

# Standard chess starting squares for standard marker IDs 0-31
STANDARD_STARTING_SQUARES: Final[Dict[int, str]] = {
    # White pawns (rank 2)
    0: "a2", 1: "b2", 2: "c2", 3: "d2", 4: "e2", 5: "f2", 6: "g2", 7: "h2",
    # White pieces (rank 1)
    8: "a1", 10: "b1", 12: "c1", 14: "d1", 15: "e1", 13: "f1", 11: "g1", 9: "h1",
    # Black pawns (rank 7)
    16: "a7", 17: "b7", 18: "c7", 19: "d7", 20: "e7", 21: "f7", 22: "g7", 23: "h7",
    # Black pieces (rank 8)
    24: "a8", 26: "b8", 28: "c8", 30: "d8", 31: "e8", 29: "f8", 27: "g8", 25: "h8",
}

# Physical dimensions (in millimeters and meters)
PIECE_MARKER_SIZE_MM: Final[float] = 15.0
CORNER_MARKER_SIZE_MM: Final[float] = 20.0
PIECE_MARKER_SIZE_M: Final[float] = 0.015
CORNER_MARKER_SIZE_M: Final[float] = 0.020

# ChArUco calibration board specification
CHARUCO_SQUARES_X: Final[int] = 7
CHARUCO_SQUARES_Y: Final[int] = 5
CHARUCO_SQUARE_LENGTH_M: Final[float] = 0.040  # 40mm
CHARUCO_MARKER_LENGTH_M: Final[float] = 0.020  # 20mm
CHARUCO_DICT_NAME: Final[str] = "DICT_5X5_50"

# Calibration target threshold
MAX_ACCEPTABLE_RMS_ERROR: Final[float] = 1.0  # RMS in pixels
RECOMMENDED_CALIBRATION_FRAMES: Final[int] = 20

# Default preferences dictionary
DEFAULT_PREFERENCES: Final[Dict[str, Any]] = {
    "camera": {
        "index": 0,
        "width": 1280,
        "height": 720,
        "fps": 30,
        "backend": "DSHOW",  # DirectShow on Windows, DEFAULT on Linux
        "synthetic_mode": False,
    },
    "detection": {
        "dictionary": "DICT_4X4_250",
        "adaptiveThreshWinSizeMin": 3,
        "adaptiveThreshWinSizeMax": 23,
        "adaptiveThreshWinSizeStep": 10,
        "minMarkerPerimeterRate": 0.03,
        "maxMarkerPerimeterRate": 4.0,
        "polygonalApproxAccuracyRate": 0.03,
        "cornerRefinement": True,
    },
    "stability": {
        "stable_frames_threshold": 5,
        "lost_marker_frames": 5,
    },
    "board": {
        "light_square_color": "#EEEED2",
        "dark_square_color": "#769656",
        "highlight_color": "#BACA44",
        "last_move_color": "#F7EC59",
        "show_coordinates": True,
    },
    "network": {
        "tcp_enabled": True,
        "tcp_host": "127.0.0.1",
        "tcp_port": 5555,
    },
    "appearance": {
        "theme": "Dark",  # "System", "Dark", "Light"
        "color_theme": "blue",
    },
    "marker_mapping": {str(k): v for k, v in DEFAULT_MARKER_TO_PIECE.items()},
}
