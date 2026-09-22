# ArUco Chess Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.7+-green.svg)](https://opencv.org/)
[![python-chess](https://img.shields.io/badge/python--chess-1.9+-orange.svg)](https://python-chess.readthedocs.io/)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-GUI-purple.svg)](https://customtkinter.tomschimansky.com/)

**ArUco Chess Tracker** is a desktop computer vision application built with Python, OpenCV, and CustomTkinter that tracks a physical chessboard in real-time. By tracking unique ArUco markers adhered to each piece's base and four outer corner reference markers, the system maps pixel coordinates to algebraic chess squares (`a1`-`h8`), validates moves using `python-chess`, renders a live synchronized 2D board, and exposes a high-speed TCP API for robotic arm (SCARA) and chess engine integration.

*Part of the atdotslash -ify toolkit, alongside Transparentify and Vectify.*

---

![ArUco Chess Tracker Demo](assets/demo.gif)

---

## Key Features

- **ChArUco Camera Calibration**: Integrated camera calibration wizard using OpenCV ChArUco boards to eliminate lens distortion and compute subpixel reprojection errors.
- **ArUco Marker Detection & Refinement**: High-speed detection using `cv2.aruco.ArucoDetector` with subpixel corner refinement (`CORNER_REFINE_SUBPIX`), duplicate resolution, and exponential temporal smoothing to eliminate jitter.
- **Perspective Homography Mapping**: Robust projective homography mapping the physical board to a normalized algebraic coordinate space (`[0, 8] x [0, 8]`), resilient to camera perspective tilt.
- **Move Detection with Hand-Occlusion Resilience**: Multi-frame stability buffer that ignores transient changes caused by human hands and only confirms moves once the physical board stabilizes.
- **Full Chess Rule Validation**: Comprehensive rule enforcement via `python-chess` (regular moves, captures, castling, en passant, promotions, check, checkmate, stalemate).
- **Dual Visual Interface**:
  - **Live Camera HUD**: Augmented reality preview with ArUco bounding boxes, projected 8x8 perspective grid, square algebraic labels, and last-move vectors.
  - **2D Digital Board**: Synchronized digital chessboard with piece glyphs, check indicators, move highlights, and captured pieces counters.
- **TCP API Server for Robotic SCARA Arms**: Built-in background TCP socket server running on port `5555` answering FEN, SAN, and full board queries.
- **Hardware-Agnostic Simulation**: Includes a built-in synthetic board generator enabling full testing and offline demonstration without a physical camera.

---

## Hardware Setup

### Camera Mounting
1. Mount your USB webcam or overhead camera above the chessboard.
2. The recommended angle is between **60° and 90° (top-down)** relative to the board surface.
3. Ensure the camera's field of view encompasses the entire 8x8 playing grid and all four corner reference markers.
4. Provide even, diffuse ambient lighting to prevent heavy glare or specular reflections on marker surfaces.

### Marker Printing & Sizes
To generate printable PNGs for all markers and the calibration board:
```bash
python -m src.markers --generate
```
Files will be exported to `assets/markers/`:
- **Piece Markers (IDs `0`–`31`)**: 15 mm × 15 mm with a 3 mm outer white margin.
  - Cut and glue each marker flat against the bottom base of the corresponding chess piece.
- **Board Corner Markers (IDs `100`–`103`)**: 20 mm × 20 mm with a 4 mm outer white margin.
  - Affix them to the outer perimeter corners of the chessboard.
- **ChArUco Board (`charuco_calibration_board.png`)**:
  - Print on rigid paper/cardstock or mount onto a flat board for camera calibration.

---

## Marker Assignment

| Marker ID | Role / Piece | Starting Square |
| :--- | :--- | :--- |
| **0 – 7** | White Pawns | `a2` – `h2` |
| **8, 9** | White Rooks | `a1`, `h1` |
| **10, 11** | White Knights | `b1`, `g1` |
| **12, 13** | White Bishops | `c1`, `f1` |
| **14** | White Queen | `d1` |
| **15** | White King | `e1` |
| **16 – 23** | Black Pawns | `a7` – `h7` |
| **24, 25** | Black Rooks | `a8`, `h8` |
| **26, 27** | Black Knights | `b8`, `g8` |
| **28, 29** | Black Bishops | `c8`, `f8` |
| **30** | Black Queen | `d8` |
| **31** | Black King | `e8` |
| **100** | Board Corner: `a1` (bottom-left) | Outer corner |
| **101** | Board Corner: `h1` (bottom-right) | Outer corner |
| **102** | Board Corner: `a8` (top-left) | Outer corner |
| **103** | Board Corner: `h8` (top-right) | Outer corner |

> **Auto-Detection**: Place your pieces in the standard starting position and open **Marker Config -> Auto-Detect from Starting Position**. The software will automatically match detected marker IDs to standard pieces and save the mapping to your preferences.

---

## Camera Lens Calibration

1. Click **Calibrate Lens** in the toolbar.
2. Hold the printed ChArUco board in front of the camera across various angles, distances, and tilt orientations.
3. When the indicator turns green ("Valid Frame"), press **Space** or **Capture Frame**.
4. Collect 15–20 frames covering the center and outer corners of the camera view.
5. Click **Compute Calibration**.
6. The app computes the camera matrix, distortion coefficients, and reprojection RMS error, automatically saving them to `calibration/camera_params.npz`. An RMS error $< 1.0\text{ px}$ indicates an excellent calibration.

---

## TCP API (Robotic SCARA Arm & Engine Interface)

The application runs a lightweight TCP server (default port `5555`) that processes newline-terminated text commands:

| Command | Response | Example Output |
| :--- | :--- | :--- |
| `GET_FEN` | Current board position in FEN notation | `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1` |
| `GET_LAST_MOVE` | Last confirmed move in SAN notation (or `NONE`) | `e4` |
| `GET_TURN` | Active player's turn (`white` or `black`) | `black` |
| `IS_GAME_OVER` | Game over status (`TRUE` or `FALSE`) | `FALSE` |
| `GET_CAPTURED` | Comma-separated list of captured piece symbols | `p,P` |
| `GET_BOARD_STATE` | Full JSON state payload | `{"fen": "...", "turn": "white", "squares": {"e4": "P", ...}}` |
| `PING` | Health check | `PONG` |

### Python Client Example
```python
import socket

def query_chess_tracker(command: str, host: str = "127.0.0.1", port: int = 5555) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall((command + "\n").encode("utf-8"))
        return sock.recv(4096).decode("utf-8").strip()

fen = query_chess_tracker("GET_FEN")
print(f"Current FEN: {fen}")
```

---

## Installation & Usage

### 1. Requirements
- Python 3.10 or 3.11+
- Virtual environment recommended

### 2. Setup
```bash
git clone https://github.com/atdotslash/ArUco-Chess-Tracker.git
cd ArUco-Chess-Tracker

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Launching
```bash
# Standard mode (webcam / USB camera)
python main.py

# Simulation mode (runs synthetic chessboard without physical camera)
python main.py --synthetic

# Custom TCP port
python main.py --port 5556
```

### 4. Running Tests
```bash
pytest tests/ -v
```

---

## Standalone Packaging (PyInstaller)

Standalone executable builds requiring no installed Python environment can be compiled using the build scripts:

### Windows:
```cmd
build\build_windows.bat
```
Produces `dist\ArUcoChessTracker.exe`.

### Linux:
```bash
chmod +x build/build_linux.sh
./build/build_linux.sh
```
Produces `dist/ArUcoChessTracker`.

---

## Troubleshooting

- **ArUco markers are not detected**:
  - Check camera focus and resolution (1280x720 recommended).
  - Ensure the white border around each marker is intact (at least 3–4 mm).
  - Avoid strong spotlights that create specular glare on glossy paper or tape.
- **High calibration RMS error (> 1.0 px)**:
  - Keep the ChArUco board completely flat (mount on cardstock).
  - Tilt the board at slight angles (15°–30°) rather than only holding it perpendicular.
  - Collect at least 20 frames spanning all 4 corners of the camera frame.
- **Homography / Grid misaligned**:
  - Verify that the four corner markers (`100` at a1, `101` at h1, `102` at a8, `103` at h8) are visible and not occluded.
- **Move not detected**:
  - Wait for the stability counter in the status bar to show green (5 stable frames).
  - Check if the move is legal according to chess rules.
- **TCP server port conflict**:
  - Open **Preferences** (Ctrl+,) and change the TCP port (e.g. to `5556`), or use the `--port` CLI flag.

---

## Known Limitations

- **Piece Recognition**: Pieces without an ArUco marker cannot be recognized.
- **Camera Configuration**: Operates from a single camera feed (overhead or angled).
- **Board Stability**: The physical board must remain stationary during play.

---

## License

MIT License — Copyright (c) 2026 **atdotslash** (Edgardo Sandoval). See [LICENSE](LICENSE) for full details.
