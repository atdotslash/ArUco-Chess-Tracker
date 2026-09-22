"""2D chessboard display component rendering pieces, coordinates, and move highlights."""

import tkinter as tk
from typing import Dict, List, Optional, Tuple
import customtkinter as ctk

from src.game_state import GameState

# Unicode chess glyphs for crisp rendering
UNICODE_PIECES = {
    # White pieces
    "K": "\u2654",
    "Q": "\u2655",
    "R": "\u2656",
    "B": "\u2657",
    "N": "\u2658",
    "P": "\u2659",
    # Black pieces
    "k": "\u265a",
    "q": "\u265b",
    "r": "\u265c",
    "b": "\u265d",
    "n": "\u265e",
    "p": "\u265f",
}


class BoardView(ctk.CTkFrame):
    """2D interactive/rendered chessboard display."""

    def __init__(
        self,
        master,
        light_color: str = "#EEEED2",
        dark_color: str = "#769656",
        highlight_color: str = "#BACA44",
        last_move_color: str = "#F7EC59",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self.light_color = light_color
        self.dark_color = dark_color
        self.highlight_color = highlight_color
        self.last_move_color = last_move_color

        # Container layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main chessboard canvas
        self.canvas = tk.Canvas(self, bg="#1e222b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Captured pieces label banner
        self.captured_frame = ctk.CTkFrame(self, fg_color="#181b22", corner_radius=6)
        self.captured_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        self.lbl_white_captured = ctk.CTkLabel(
            self.captured_frame,
            text="Captured by White: -",
            font=("Segoe UI", 12),
            text_color="#e0e0e0",
            anchor="w",
        )
        self.lbl_white_captured.pack(side="left", padx=12, pady=4)

        self.lbl_black_captured = ctk.CTkLabel(
            self.captured_frame,
            text="Captured by Black: -",
            font=("Segoe UI", 12),
            text_color="#e0e0e0",
            anchor="e",
        )
        self.lbl_black_captured.pack(side="right", padx=12, pady=4)

        self._cached_game_state: Optional[GameState] = None
        self._last_move: Optional[Tuple[str, str]] = None
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        if self._cached_game_state:
            self.render(self._cached_game_state, self._last_move)

    def update_board(
        self,
        game_state: GameState,
        last_move: Optional[Tuple[str, str]] = None,
    ) -> None:
        """Update display with fresh game state."""
        self._cached_game_state = game_state
        self._last_move = last_move
        self.render(game_state, last_move)

        # Update captured pieces
        white_captured: List[str] = []
        black_captured: List[str] = []
        for p in game_state.get_captured_pieces():
            glyph = UNICODE_PIECES.get(p, p)
            if p.islower():
                # Captured piece was black -> captured by White
                white_captured.append(glyph)
            else:
                black_captured.append(glyph)

        self.lbl_white_captured.configure(
            text="White took: " + (" ".join(white_captured) if white_captured else "None")
        )
        self.lbl_black_captured.configure(
            text="Black took: " + (" ".join(black_captured) if black_captured else "None")
        )

    def render(
        self,
        game_state: GameState,
        last_move: Optional[Tuple[str, str]] = None,
    ) -> None:
        """Redraw all 64 squares, labels, highlights, and pieces."""
        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        margin = 24
        board_pixel_size = min(cw - 2 * margin, ch - 2 * margin)
        if board_pixel_size <= 0:
            return

        sq_size = board_pixel_size / 8.0
        start_x = (cw - board_pixel_size) / 2.0
        start_y = (ch - board_pixel_size) / 2.0

        highlight_squares = set(last_move) if last_move else set()
        king_in_check_sq: Optional[str] = None
        if game_state.board.is_check():
            turn = game_state.board.turn
            king_idx = game_state.board.king(turn)
            if king_idx is not None:
                import chess
                king_in_check_sq = chess.square_name(king_idx)

        # Draw 8x8 squares
        board_state = game_state.get_board_state_dict()

        for row in range(8):  # 0 is rank 8, 7 is rank 1
            rank_str = str(8 - row)
            for col in range(8):  # 0 is file a, 7 is file h
                file_str = chr(ord("a") + col)
                sq_name = f"{file_str}{rank_str}"

                x0 = start_x + col * sq_size
                y0 = start_y + row * sq_size
                x1 = x0 + sq_size
                y1 = y0 + sq_size

                # Square background color
                is_light = (row + col) % 2 == 0
                bg = self.light_color if is_light else self.dark_color

                if sq_name in highlight_squares:
                    bg = self.last_move_color
                elif sq_name == king_in_check_sq:
                    bg = "#FF6B6B"  # Light red for check

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=bg, outline="", width=0)

                # Draw piece if square is occupied
                if sq_name in board_state:
                    piece_sym = board_state[sq_name]
                    glyph = UNICODE_PIECES.get(piece_sym, piece_sym)
                    piece_color = "#FFFFFF" if piece_sym.isupper() else "#111111"
                    font_size = max(12, int(sq_size * 0.65))

                    # Drop shadow for white pieces for high contrast
                    if piece_sym.isupper():
                        self.canvas.create_text(
                            (x0 + x1) / 2 + 1,
                            (y0 + y1) / 2 + 1,
                            text=glyph,
                            font=("Segoe UI Symbol", font_size, "bold"),
                            fill="#444444",
                        )

                    self.canvas.create_text(
                        (x0 + x1) / 2,
                        (y0 + y1) / 2,
                        text=glyph,
                        font=("Segoe UI Symbol", font_size, "bold"),
                        fill=piece_color,
                    )

        # Draw coordinate labels
        label_font = ("Segoe UI", max(9, int(sq_size * 0.22)), "bold")
        label_color = "#9aa4b2"

        # Ranks on left and right margins
        for row in range(8):
            rank_str = str(8 - row)
            y_center = start_y + (row + 0.5) * sq_size
            self.canvas.create_text(
                start_x - 12, y_center, text=rank_str, font=label_font, fill=label_color
            )
            self.canvas.create_text(
                start_x + board_pixel_size + 12,
                y_center,
                text=rank_str,
                font=label_font,
                fill=label_color,
            )

        # Files on top and bottom margins
        for col in range(8):
            file_str = chr(ord("a") + col)
            x_center = start_x + (col + 0.5) * sq_size
            self.canvas.create_text(
                x_center, start_y - 12, text=file_str, font=label_font, fill=label_color
            )
            self.canvas.create_text(
                x_center,
                start_y + board_pixel_size + 12,
                text=file_str,
                font=label_font,
                fill=label_color,
            )
