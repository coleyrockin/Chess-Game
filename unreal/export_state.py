from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game_core import ChessGameState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Neon City Chess state payload for Unreal.")
    parser.add_argument(
        "--fen",
        default=chess.STARTING_FEN,
        help="FEN string to export. Defaults to the starting position.",
    )
    parser.add_argument(
        "--moves",
        default="",
        help="Comma-separated UCI moves to apply on top of --fen (example: e2e4,e7e5,g1f3).",
    )
    parser.add_argument(
        "--output",
        default="unreal/sample_state.json",
        help="Output JSON file path.",
    )
    return parser.parse_args()


def _parse_moves(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def _apply_uci_moves(board: chess.Board, moves: list[str]) -> None:
    for idx, uci in enumerate(moves, start=1):
        try:
            move = chess.Move.from_uci(uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move at index {idx}: {uci}") from exc
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move at index {idx}: {uci} on position {board.fen()}")
        board.push(move)


def main() -> None:
    args = parse_args()
    try:
        board = chess.Board(args.fen)
    except ValueError as exc:
        raise SystemExit(f"Invalid --fen value: {exc}") from exc

    moves = _parse_moves(args.moves)
    try:
        _apply_uci_moves(board, moves)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    game = ChessGameState(board=board)
    payload = game.export_payload()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote state to {output_path.resolve()}")


if __name__ == "__main__":
    main()
