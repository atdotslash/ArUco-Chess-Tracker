"""Generation and export of ArUco piece markers, corner markers, and ChArUco calibration boards."""

import argparse
from pathlib import Path
from typing import Optional, Union
import cv2
import numpy as np
from PIL import Image

from src.config import (
    PIECE_ID_MIN,
    PIECE_ID_MAX,
    CORNER_IDS,
    PIECE_NAMES,
    DEFAULT_MARKER_TO_PIECE,
    CHARUCO_SQUARES_X,
    CHARUCO_SQUARES_Y,
    CHARUCO_SQUARE_LENGTH_M,
    CHARUCO_MARKER_LENGTH_M,
)
from src.utils.paths import get_markers_dir


def get_aruco_dict(dict_name: Union[str, int] = "DICT_4X4_250") -> cv2.aruco.Dictionary:
    """Return cv2.aruco predefined dictionary object from string name or integer constant."""
    if isinstance(dict_name, int):
        return cv2.aruco.getPredefinedDictionary(dict_name)
    attr_name = getattr(cv2.aruco, str(dict_name), None)
    if attr_name is None:
        attr_name = cv2.aruco.DICT_4X4_250
    return cv2.aruco.getPredefinedDictionary(attr_name)


def generate_marker(
    marker_id: int,
    size_px: int = 300,
    border_px: int = 60,
    dictionary: Union[int, str] = "DICT_4X4_250",
    marker_size_px: Optional[int] = None,
    dict_name: Optional[Union[str, int]] = None,
) -> Image.Image:
    """Generate a single ArUco marker image with a white outer border.

    Args:
        marker_id: ArUco identifier (0-249).
        size_px: Pixel dimension of the black marker square (alias: marker_size_px).
        border_px: Width of the outer white margin.
        dictionary: ArUco dictionary (name string or OpenCV integer constant).

    Returns:
        PIL Image in RGB mode.
    """
    actual_size = marker_size_px if marker_size_px is not None else size_px
    actual_dict = dict_name if dict_name is not None else dictionary

    aruco_dict = get_aruco_dict(actual_dict)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, actual_size)

    # Add white border around the marker
    total_size = actual_size + 2 * border_px
    bordered = np.full((total_size, total_size), 255, dtype=np.uint8)
    bordered[border_px : border_px + actual_size, border_px : border_px + actual_size] = marker_img

    # Convert to PIL RGB
    return Image.fromarray(bordered).convert("RGB")


def generate_charuco_board_image(
    squares_x: int = CHARUCO_SQUARES_X,
    squares_y: int = CHARUCO_SQUARES_Y,
    square_len: float = CHARUCO_SQUARE_LENGTH_M,
    marker_len: float = CHARUCO_MARKER_LENGTH_M,
    dict_name: str = "DICT_5X5_50",
    image_size: tuple[int, int] = (1400, 1000),
    margin_px: int = 40,
) -> Image.Image:
    """Generate a printable ChArUco calibration board image."""
    dictionary = get_aruco_dict(dict_name)
    board = cv2.aruco.CharucoBoard((squares_x, squares_y), square_len, marker_len, dictionary)
    board_img = board.generateImage(image_size, marginSize=margin_px)
    return Image.fromarray(board_img).convert("RGB")


def generate_all_markers(output_dir: Union[str, Path] | None = None) -> None:
    """Generate all pieces markers (0-31), corner markers (100-103), and ChArUco board.

    Args:
        output_dir: Destination directory. Defaults to assets/markers.
    """
    out_path = Path(output_dir) if output_dir else get_markers_dir()
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Generating ArUco markers in {out_path}...")

    # 1. Piece markers (IDs 0-31): 300x300 px + 60px border
    for m_id in range(PIECE_ID_MIN, PIECE_ID_MAX + 1):
        piece_symbol = DEFAULT_MARKER_TO_PIECE.get(m_id, "?")
        piece_name = PIECE_NAMES.get(piece_symbol, f"Piece_{m_id}").replace(" ", "_")
        filename = f"piece_{m_id:02d}_{piece_symbol}_{piece_name}.png"
        img = generate_marker(m_id, marker_size_px=300, border_px=60)
        img.save(out_path / filename)

    # 2. Board corner markers (IDs 100-103): 400x400 px + 80px border
    corner_labels = {
        100: "a1",
        101: "h1",
        102: "a8",
        103: "h8",
    }
    for c_id in CORNER_IDS:
        label = corner_labels.get(c_id, f"corner_{c_id}")
        filename = f"corner_{c_id}_{label}.png"
        img = generate_marker(c_id, marker_size_px=400, border_px=80)
        img.save(out_path / filename)

    # 3. ChArUco calibration board
    charuco_img = generate_charuco_board_image()
    charuco_img.save(out_path / "charuco_calibration_board.png")

    print(f"Successfully generated 32 piece markers, 4 corner markers, and 1 ChArUco board in {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate printable ArUco chess markers.")
    parser.add_argument("--generate", action="store_true", help="Generate all markers and boards into assets/markers/")
    parser.add_argument("--output", type=str, default=None, help="Custom output directory")
    args = parser.parse_args()

    if args.generate:
        generate_all_markers(args.output)
    else:
        parser.print_help()
