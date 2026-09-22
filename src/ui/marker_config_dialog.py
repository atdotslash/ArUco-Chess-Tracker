"""Marker configuration dialog for assigning ArUco IDs to chess pieces."""

from typing import Callable, Dict, Optional
import customtkinter as ctk

from src.config import (
    PIECE_ID_MIN,
    PIECE_ID_MAX,
    PIECE_NAMES,
    DEFAULT_MARKER_TO_PIECE,
)
from src.preferences import Preferences

# Options for piece assignment dropdown
PIECE_CHOICES = [
    ("P", "White Pawn (P)"),
    ("R", "White Rook (R)"),
    ("N", "White Knight (N)"),
    ("B", "White Bishop (B)"),
    ("Q", "White Queen (Q)"),
    ("K", "White King (K)"),
    ("p", "Black Pawn (p)"),
    ("r", "Black Rook (r)"),
    ("n", "Black Knight (n)"),
    ("b", "Black Bishop (b)"),
    ("q", "Black Queen (q)"),
    ("k", "Black King (k)"),
    ("?", "Unassigned (?)"),
]
SYMBOL_TO_LABEL = {sym: label for sym, label in PIECE_CHOICES}
LABEL_TO_SYMBOL = {label: sym for sym, label in PIECE_CHOICES}


class MarkerConfigDialog(ctk.CTkToplevel):
    """Modal dialog for custom marker ID to chess piece mapping."""

    def __init__(
        self,
        parent,
        preferences: Preferences,
        current_detected_squares: Optional[Dict[int, str]] = None,
        on_saved: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self.preferences = preferences
        self.current_detected_squares = current_detected_squares or {}
        self.on_saved = on_saved

        self.title("ArUco Marker Assignment")
        self.geometry("640x700")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 640) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 700) // 2
        self.geometry(f"+{max(0, px)}+{max(0, py)}")

        self.transient(parent)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        # Header description
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))

        lbl_title = ctk.CTkLabel(header, text="Assign ArUco IDs (0-31) to Chess Pieces", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            header,
            text="Each piece should have a unique ArUco marker glued to its bottom base.\n"
                 "You can manually assign pieces or click 'Auto-Detect' when board is in starting position.",
            font=("Segoe UI", 11),
            text_color="#9aa4b2",
            justify="left",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Action buttons toolbar
        tb = ctk.CTkFrame(self, fg_color="transparent")
        tb.pack(fill="x", padx=20, pady=(0, 8))

        self.btn_auto = ctk.CTkButton(
            tb,
            text="Auto-Detect from Starting Position",
            fg_color="#1971c2",
            hover_color="#1864ab",
            command=self._on_auto_detect,
        )
        self.btn_auto.pack(side="left")

        self.btn_default = ctk.CTkButton(
            tb,
            text="Standard Defaults",
            fg_color="#495057",
            hover_color="#343a40",
            width=140,
            command=self._on_standard_defaults,
        )
        self.btn_default.pack(side="left", padx=8)

        # Scrollable table of markers
        self.table_scroll = ctk.CTkScrollableFrame(self, label_text="Marker ID Mappings (0 - 31)")
        self.table_scroll.pack(fill="both", expand=True, padx=20, pady=8)

        # 2-column grid layout for 32 markers (0-15 White, 16-31 Black)
        self.table_scroll.grid_columnconfigure((0, 1), weight=1)

        self._combos: Dict[int, ctk.CTkComboBox] = {}
        mapping = self.preferences.get_marker_mapping()

        choice_labels = [label for _, label in PIECE_CHOICES]

        for m_id in range(PIECE_ID_MIN, PIECE_ID_MAX + 1):
            col = 0 if m_id < 16 else 1
            row = m_id if m_id < 16 else (m_id - 16)

            card = ctk.CTkFrame(self.table_scroll, fg_color="#1e222b", corner_radius=6)
            card.grid(row=row, column=col, padx=4, pady=3, sticky="ew")

            current_sym = mapping.get(m_id, DEFAULT_MARKER_TO_PIECE.get(m_id, "?"))
            current_label = SYMBOL_TO_LABEL.get(current_sym, f"Piece ({current_sym})")

            # Marker ID badge
            badge_color = "#339af0" if m_id < 16 else "#e03131"
            lbl_id = ctk.CTkLabel(
                card,
                text=f"ID #{m_id:02d}",
                font=("Segoe UI", 11, "bold"),
                text_color=badge_color,
                width=54,
            )
            lbl_id.pack(side="left", padx=6)

            # Piece dropdown
            combo = ctk.CTkComboBox(
                card,
                values=choice_labels,
                width=175,
                height=28,
            )
            combo.set(current_label)
            combo.pack(side="right", padx=6, pady=4)
            self._combos[m_id] = combo

        # Footer actions
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(8, 16))

        self.btn_cancel = ctk.CTkButton(
            footer,
            text="Cancel",
            fg_color="#6c757d",
            hover_color="#5a6268",
            width=100,
            command=self.destroy,
        )
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_save = ctk.CTkButton(
            footer,
            text="Save Configuration",
            fg_color="#2b8a3e",
            hover_color="#237032",
            width=150,
            command=self._on_save,
        )
        self.btn_save.pack(side="right")

    def _on_auto_detect(self) -> None:
        """Map markers to pieces from currently detected squares in standard position."""
        from src.config import STANDARD_STARTING_SQUARES

        square_to_default_sym: Dict[str, str] = {}
        for mid, sq in STANDARD_STARTING_SQUARES.items():
            square_to_default_sym[sq] = DEFAULT_MARKER_TO_PIECE[mid]

        assigned = 0
        for mid, sq in self.current_detected_squares.items():
            if mid in self._combos and sq in square_to_default_sym:
                sym = square_to_default_sym[sq]
                label = SYMBOL_TO_LABEL.get(sym)
                if label:
                    self._combos[mid].set(label)
                    assigned += 1

        self.btn_auto.configure(text=f"Auto-Detected: {assigned} pieces!")

    def _on_standard_defaults(self) -> None:
        """Reset dropdowns to standard 0-31 defaults."""
        for mid, combo in self._combos.items():
            sym = DEFAULT_MARKER_TO_PIECE.get(mid, "?")
            label = SYMBOL_TO_LABEL.get(sym, "?")
            combo.set(label)

    def _on_save(self) -> None:
        """Save dropdown values to preferences."""
        new_mapping: Dict[int, str] = {}
        for mid, combo in self._combos.items():
            label = combo.get()
            sym = LABEL_TO_SYMBOL.get(label, "?")
            new_mapping[mid] = sym

        self.preferences.set_marker_mapping(new_mapping)
        self.preferences.save()

        if self.on_saved:
            self.on_saved()

        self.destroy()
