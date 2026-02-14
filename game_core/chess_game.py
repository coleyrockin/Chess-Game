from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set

import chess

from .scoring import PieceScorer


@dataclass(frozen=True)
class GameUpdate:
    board_changed: bool = False
    selection_changed: bool = False
    moved: bool = False
    captured: bool = False
    refresh_turn_pose: bool = False
    focus_square: Optional[int] = None


@dataclass
class ChessGameState:
    board: chess.Board = field(default_factory=chess.Board)
    selected_square: Optional[int] = None
    legal_targets: Set[int] = field(default_factory=set)

    def reset(self) -> GameUpdate:
        self.board.reset()
        self.selected_square = None
        self.legal_targets.clear()
        return GameUpdate(board_changed=True, selection_changed=True, refresh_turn_pose=True)

    def click_square(self, square: int) -> GameUpdate:
        if self.board.is_game_over():
            return GameUpdate()

        clicked_piece = self.board.piece_at(square)
        turn_color = self.board.turn

        if self.selected_square is None:
            if clicked_piece and clicked_piece.color == turn_color:
                self._select_square(square)
                return GameUpdate(selection_changed=True, focus_square=square)
            return GameUpdate()

        if clicked_piece and clicked_piece.color == turn_color:
            self._select_square(square)
            return GameUpdate(selection_changed=True, focus_square=square)

        move = chess.Move(self.selected_square, square)
        if move not in self.board.legal_moves:
            selected_piece = self.board.piece_at(self.selected_square)
            if selected_piece and selected_piece.piece_type == chess.PAWN and chess.square_rank(square) in (0, 7):
                move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)

        if move in self.board.legal_moves:
            captured = self.board.piece_at(move.to_square) is not None or self.board.is_en_passant(move)
            self.board.push(move)
            self.selected_square = None
            self.legal_targets.clear()
            return GameUpdate(
                board_changed=True,
                selection_changed=True,
                moved=True,
                captured=captured,
                refresh_turn_pose=True,
            )

        self.selected_square = None
        self.legal_targets.clear()
        return GameUpdate(selection_changed=True, refresh_turn_pose=True)

    def turn_status_text(self) -> str:
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"Checkmate | {winner} wins"
        if self.board.is_stalemate():
            return "Stalemate"
        if self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            return "Draw"
        turn = "White" if self.board.turn == chess.WHITE else "Black"
        if self.board.is_check():
            return f"{turn} to move (Check)"
        return f"{turn} to move"

    def score_status_text(self) -> str:
        return PieceScorer.status_text(self.board)

    def export_payload(self) -> dict:
        return {
            "fen": self.board.fen(),
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "selected_square": chess.square_name(self.selected_square) if self.selected_square is not None else None,
            "legal_targets": [chess.square_name(s) for s in sorted(self.legal_targets)],
            "is_game_over": self.board.is_game_over(),
            "status_text": self.turn_status_text(),
            "score_text": self.score_status_text(),
            "legal_moves_uci": sorted(move.uci() for move in self.board.legal_moves),
        }

    def _select_square(self, square: int) -> None:
        self.selected_square = square
        self.legal_targets = {move.to_square for move in self.board.legal_moves if move.from_square == square}
