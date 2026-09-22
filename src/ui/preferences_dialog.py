"""Preferences dialog window for configuring camera, detection, stability, and UI."""

from typing import Callable, Optional
import customtkinter as ctk

from src.preferences import Preferences


class PreferencesDialog(ctk.CTkToplevel):
    """Modal dialog allowing users to adjust application preferences."""

    def __init__(self, parent, preferences: Preferences, on_saved: Optional[Callable] = None) -> None:
        super().__init__(parent)
        self.preferences = preferences
        self.on_saved = on_saved

        self.title("Preferences")
        self.geometry("520x620")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 620) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        # Scrollable container for settings
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Application Settings")
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=16)

        self._build_camera_section()
        self._build_stability_section()
        self._build_board_section()
        self._build_network_section()
        self._build_appearance_section()

        # Footer action buttons
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", padx=16, pady=(0, 16))

        self.btn_reset = ctk.CTkButton(
            self.footer,
            text="Reset Defaults",
            fg_color="#495057",
            hover_color="#343a40",
            width=120,
            command=self._on_reset,
        )
        self.btn_reset.pack(side="left")

        self.btn_cancel = ctk.CTkButton(
            self.footer,
            text="Cancel",
            fg_color="#6c757d",
            hover_color="#5a6268",
            width=100,
            command=self.destroy,
        )
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_save = ctk.CTkButton(
            self.footer,
            text="Save Settings",
            fg_color="#2b8a3e",
            hover_color="#237032",
            width=120,
            command=self._on_save,
        )
        self.btn_save.pack(side="right")

    def _build_camera_section(self) -> None:
        lbl = ctk.CTkLabel(self.scroll_frame, text="Camera Settings", font=("Segoe UI", 14, "bold"))
        lbl.pack(anchor="w", pady=(8, 4))

        # Camera index
        f1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f1.pack(fill="x", pady=2)
        ctk.CTkLabel(f1, text="Camera Index:").pack(side="left")
        self.ent_cam_index = ctk.CTkEntry(f1, width=80)
        self.ent_cam_index.insert(0, str(self.preferences.get("camera", "index", 0)))
        self.ent_cam_index.pack(side="right")

        # Resolution dropdown
        f2 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f2.pack(fill="x", pady=2)
        ctk.CTkLabel(f2, text="Resolution:").pack(side="left")
        cur_w = self.preferences.get("camera", "width", 1280)
        cur_h = self.preferences.get("camera", "height", 720)
        res_str = f"{cur_w}x{cur_h}"
        self.combo_res = ctk.CTkComboBox(
            f2,
            values=["640x480", "1280x720", "1920x1080"],
            width=140,
        )
        self.combo_res.set(res_str)
        self.combo_res.pack(side="right")

        # Synthetic camera mode switch
        f3 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f3.pack(fill="x", pady=2)
        self.var_synthetic = ctk.BooleanVar(value=bool(self.preferences.get("camera", "synthetic_mode", False)))
        self.chk_synthetic = ctk.CTkSwitch(
            f3,
            text="Synthetic Board Simulation (No physical camera)",
            variable=self.var_synthetic,
        )
        self.chk_synthetic.pack(side="left")

    def _build_stability_section(self) -> None:
        lbl = ctk.CTkLabel(self.scroll_frame, text="Move Stability & Tracking", font=("Segoe UI", 14, "bold"))
        lbl.pack(anchor="w", pady=(14, 4))

        # Stable frames threshold
        f1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f1.pack(fill="x", pady=2)
        ctk.CTkLabel(f1, text="Stable Frames for Move Confirmation:").pack(side="left")
        self.ent_stable_frames = ctk.CTkEntry(f1, width=80)
        self.ent_stable_frames.insert(0, str(self.preferences.get("stability", "stable_frames_threshold", 5)))
        self.ent_stable_frames.pack(side="right")

        # Lost marker frames
        f2 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f2.pack(fill="x", pady=2)
        ctk.CTkLabel(f2, text="Frames before Marker Considered Lost:").pack(side="left")
        self.ent_lost_frames = ctk.CTkEntry(f2, width=80)
        self.ent_lost_frames.insert(0, str(self.preferences.get("stability", "lost_marker_frames", 5)))
        self.ent_lost_frames.pack(side="right")

    def _build_board_section(self) -> None:
        lbl = ctk.CTkLabel(self.scroll_frame, text="2D Chessboard Appearance", font=("Segoe UI", 14, "bold"))
        lbl.pack(anchor="w", pady=(14, 4))

        # Light square color
        f1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f1.pack(fill="x", pady=2)
        ctk.CTkLabel(f1, text="Light Square Color:").pack(side="left")
        self.ent_light_col = ctk.CTkEntry(f1, width=120)
        self.ent_light_col.insert(0, str(self.preferences.get("board", "light_square_color", "#EEEED2")))
        self.ent_light_col.pack(side="right")

        # Dark square color
        f2 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f2.pack(fill="x", pady=2)
        ctk.CTkLabel(f2, text="Dark Square Color:").pack(side="left")
        self.ent_dark_col = ctk.CTkEntry(f2, width=120)
        self.ent_dark_col.insert(0, str(self.preferences.get("board", "dark_square_color", "#769656")))
        self.ent_dark_col.pack(side="right")

    def _build_network_section(self) -> None:
        lbl = ctk.CTkLabel(self.scroll_frame, text="TCP Server (SCARA / API)", font=("Segoe UI", 14, "bold"))
        lbl.pack(anchor="w", pady=(14, 4))

        # TCP Port
        f1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f1.pack(fill="x", pady=2)
        ctk.CTkLabel(f1, text="TCP Port:").pack(side="left")
        self.ent_tcp_port = ctk.CTkEntry(f1, width=80)
        self.ent_tcp_port.insert(0, str(self.preferences.get("network", "tcp_port", 5555)))
        self.ent_tcp_port.pack(side="right")

        # TCP Host
        f2 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f2.pack(fill="x", pady=2)
        ctk.CTkLabel(f2, text="Bind Host:").pack(side="left")
        self.ent_tcp_host = ctk.CTkEntry(f2, width=120)
        self.ent_tcp_host.insert(0, str(self.preferences.get("network", "tcp_host", "127.0.0.1")))
        self.ent_tcp_host.pack(side="right")

    def _build_appearance_section(self) -> None:
        lbl = ctk.CTkLabel(self.scroll_frame, text="Window Theme", font=("Segoe UI", 14, "bold"))
        lbl.pack(anchor="w", pady=(14, 4))

        f1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        f1.pack(fill="x", pady=2)
        ctk.CTkLabel(f1, text="Theme:").pack(side="left")
        self.combo_theme = ctk.CTkComboBox(
            f1,
            values=["Dark", "Light", "System"],
            width=120,
        )
        self.combo_theme.set(str(self.preferences.get("appearance", "theme", "Dark")))
        self.combo_theme.pack(side="right")

    def _on_save(self) -> None:
        """Parse, validate, and write preferences."""
        try:
            # Camera
            cam_idx = int(self.ent_cam_index.get().strip())
            res = self.combo_res.get().split("x")
            w, h = int(res[0]), int(res[1])
            self.preferences.set("camera", "index", cam_idx)
            self.preferences.set("camera", "width", w)
            self.preferences.set("camera", "height", h)
            self.preferences.set("camera", "synthetic_mode", self.var_synthetic.get())

            # Stability
            sf = int(self.ent_stable_frames.get().strip())
            lf = int(self.ent_lost_frames.get().strip())
            self.preferences.set("stability", "stable_frames_threshold", max(1, sf))
            self.preferences.set("stability", "lost_marker_frames", max(1, lf))

            # Board colors
            self.preferences.set("board", "light_square_color", self.ent_light_col.get().strip())
            self.preferences.set("board", "dark_square_color", self.ent_dark_col.get().strip())

            # Network
            port = int(self.ent_tcp_port.get().strip())
            self.preferences.set("network", "tcp_port", port)
            self.preferences.set("network", "tcp_host", self.ent_tcp_host.get().strip())

            # Appearance
            theme = self.combo_theme.get()
            self.preferences.set("appearance", "theme", theme)
            ctk.set_appearance_mode(theme)

            self.preferences.save()

            if self.on_saved:
                self.on_saved()

            self.destroy()
        except ValueError as e:
            ctk.CTkLabel(self, text=f"Invalid value: {e}", text_color="red").pack(pady=4)

    def _on_reset(self) -> None:
        """Reset to defaults and reload form inputs."""
        self.preferences.reset_to_defaults()
        if self.on_saved:
            self.on_saved()
        self.destroy()
