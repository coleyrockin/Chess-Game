from dataclasses import dataclass
from typing import Dict

import chess


PIECE_VALUES: Dict[int, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


@dataclass(frozen=True)
class ScoreSnapshot:
    white_material: int
    black_material: int
    white_captured: int
    black_captured: int
    advantage: int


class PieceScorer:
    STARTING_MATERIAL = 39

    @staticmethod
    def material_for(board: chess.Board, color: bool) -> int:
        total = 0
        for piece in board.piece_map().values():
            if piece.color == color:
                total += PIECE_VALUES.get(piece.piece_type, 0)
        return total

    @classmethod
    def snapshot(cls, board: chess.Board) -> ScoreSnapshot:
        # Single-pass calculation for both colors to avoid redundant iteration
        white = 0
        black = 0
        for piece in board.piece_map().values():
            value = PIECE_VALUES.get(piece.piece_type, 0)
            if piece.color == chess.WHITE:
                white += value
            else:
                black += value
        
        return ScoreSnapshot(
            white_material=white,
            black_material=black,
            white_captured=max(0, cls.STARTING_MATERIAL - black),
            black_captured=max(0, cls.STARTING_MATERIAL - white),
            advantage=white - black,
        )

    @classmethod
    def status_text(cls, board: chess.Board) -> str:
        snap = cls.snapshot(board)
        if snap.advantage > 0:
            eval_text = f"White +{snap.advantage}"
        elif snap.advantage < 0:
            eval_text = f"Black +{abs(snap.advantage)}"
        else:
            eval_text = "Even"
        return (
            f"Mat W:{snap.white_material} B:{snap.black_material} | "
            f"Caps W:{snap.white_captured} B:{snap.black_captured} | {eval_text}"
        )
