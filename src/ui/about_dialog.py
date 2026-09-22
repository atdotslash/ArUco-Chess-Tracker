"""About dialog window displaying application information, versions, and license."""

import platform
import sys
import webbrowser
import chess
import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image

from src.config import __version__, APP_NAME, AUTHOR, GITHUB_URL
from src.utils.paths import get_icons_dir


class AboutDialog(ctk.CTkToplevel):
    """Modal dialog displaying version and licensing information."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title(f"About {APP_NAME}")
        self.geometry("460x520")
        self.resizable(False, False)

        # Center on parent window
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 460) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 520) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self.transient(parent)
        self.grab_set()

        # Key bindings
        self.bind("<Escape>", lambda e: self.destroy())

        # Main layout
        self.grid_columnconfigure(0, weight=1)

        # App Icon
        icon_path = get_icons_dir() / "app.png"
        if icon_path.exists():
            try:
                pil_icon = Image.open(icon_path).resize((72, 72), Image.Resampling.LANCZOS)
                self.icon_img = ctk.CTkImage(light_image=pil_icon, dark_image=pil_icon, size=(72, 72))
                self.lbl_icon = ctk.CTkLabel(self, image=self.icon_img, text="")
                self.lbl_icon.pack(pady=(20, 8))
            except Exception:
                pass

        # Title & Version
        self.lbl_title = ctk.CTkLabel(
            self,
            text=APP_NAME,
            font=("Segoe UI", 20, "bold"),
        )
        self.lbl_title.pack(pady=(0, 2))

        self.lbl_version = ctk.CTkLabel(
            self,
            text=f"Version {__version__}",
            font=("Segoe UI", 12),
            text_color="#9aa4b2",
        )
        self.lbl_version.pack(pady=(0, 10))

        # Description
        desc_text = (
            "Real-time physical chessboard tracking using computer vision and ArUco markers.\n"
            "Maintains game state, validates moves, and provides an API for robotic integration."
        )
        self.lbl_desc = ctk.CTkLabel(
            self,
            text=desc_text,
            font=("Segoe UI", 11),
            justify="center",
            wraplength=400,
        )
        self.lbl_desc.pack(padx=20, pady=(0, 14))

        # Author and GitHub link
        author_frame = ctk.CTkFrame(self, fg_color="transparent")
        author_frame.pack(pady=(0, 10))

        lbl_author = ctk.CTkLabel(author_frame, text=f"Author: {AUTHOR}  |  ", font=("Segoe UI", 11))
        lbl_author.pack(side="left")

        lbl_link = ctk.CTkLabel(
            author_frame,
            text="GitHub Repository",
            font=("Segoe UI", 11, "underline"),
            text_color="#4dabf7",
            cursor="hand2",
        )
        lbl_link.pack(side="left")
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))

        # System & Runtime specifications box
        runtime_frame = ctk.CTkFrame(self, fg_color="#1e222b", corner_radius=8)
        runtime_frame.pack(fill="x", padx=28, pady=(0, 16))

        runtime_info = [
            ("OpenCV", cv2.__version__),
            ("python-chess", chess.__version__),
            ("NumPy", np.__version__),
            ("Python", platform.python_version()),
            ("Platform", f"{platform.system()} ({platform.machine()})"),
            ("License", "MIT License"),
        ]

        for idx, (label, val) in enumerate(runtime_info):
            row_frame = ctk.CTkFrame(runtime_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row_frame, text=label, font=("Segoe UI", 10), text_color="#868e96").pack(side="left")
            ctk.CTkLabel(row_frame, text=val, font=("Segoe UI", 10, "bold")).pack(side="right")

        # Close button
        self.btn_close = ctk.CTkButton(
            self,
            text="Close",
            width=120,
            command=self.destroy,
        )
        self.btn_close.pack(pady=(0, 16))
