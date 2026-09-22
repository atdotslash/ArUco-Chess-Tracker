"""Image I/O and format conversion utilities between OpenCV, PIL, and CTkImage."""

from pathlib import Path
from typing import Tuple, Union
import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk


def bgr_to_pil(frame: np.ndarray) -> Image.Image:
    """Convert an OpenCV BGR frame to a PIL Image (RGB)."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image to an OpenCV BGR numpy array."""
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def bgr_to_ctk_image(frame: np.ndarray, display_size: Tuple[int, int]) -> ctk.CTkImage:
    """Convert an OpenCV BGR frame directly to a CTkImage scaled to display_size."""
    pil_img = bgr_to_pil(frame)
    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=display_size)


def save_image(filepath: Union[str, Path], image: Union[np.ndarray, Image.Image]) -> bool:
    """Save an image (OpenCV ndarray or PIL Image) to file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(image, Image.Image):
        image.save(str(path))
        return True
    elif isinstance(image, np.ndarray):
        return cv2.imwrite(str(path), image)
    return False


def draw_hud_text(
    frame: np.ndarray,
    text: str,
    pos: Tuple[int, int],
    font_scale: float = 0.5,
    text_color: Tuple[int, int, int] = (255, 255, 255),
    bg_color: Tuple[int, int, int] = (20, 20, 20),
    thickness: int = 1,
    padding: int = 4,
) -> None:
    """Draw text with a solid contrasting background rectangle for readability."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    x2 = x + text_w + padding * 2
    y2 = y + text_h + padding * 2

    # Draw background box
    cv2.rectangle(frame, (x, y), (x2, y2), bg_color, -1)
    # Draw border
    cv2.rectangle(frame, (x, y), (x2, y2), (80, 80, 80), 1)
    # Draw text
    cv2.putText(
        frame,
        text,
        (x + padding, y + text_h + padding - 2),
        font,
        font_scale,
        text_color,
        thickness,
        cv2.LINE_AA,
    )
