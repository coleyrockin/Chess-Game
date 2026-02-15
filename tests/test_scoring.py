"""Tests for game_core.scoring — material counting and score display."""

from __future__ import annotations

import chess
import pytest

from game_core.scoring import PIECE_VALUES, PieceScorer, ScoreSnapshot


class TestPieceValues:
    def test_standard_values(self):
        assert PIECE_VALUES[chess.PAWN] == 1
        assert PIECE_VALUES[chess.KNIGHT] == 3
        assert PIECE_VALUES[chess.BISHOP] == 3
        assert PIECE_VALUES[chess.ROOK] == 5
        assert PIECE_VALUES[chess.QUEEN] == 9
        assert PIECE_VALUES[chess.KING] == 0

    def test_starting_material_constant(self):
        # 8*1 + 2*3 + 2*3 + 2*5 + 1*9 = 39
        assert PieceScorer.STARTING_MATERIAL == 39


class TestMaterialCounting:
    def test_starting_position_material(self):
        board = chess.Board()
        assert PieceScorer.material_for(board, chess.WHITE) == 39
        assert PieceScorer.material_for(board, chess.BLACK) == 39

    def test_after_pawn_capture(self):
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        # White captured a pawn, now has 9 pawns worth... no, white has same pieces.
        # White material = 39 (same pieces), Black has lost a pawn = 38.
        assert PieceScorer.material_for(board, chess.WHITE) == 39
        assert PieceScorer.material_for(board, chess.BLACK) == 38

    def test_empty_board_with_kings_only(self):
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        assert PieceScorer.material_for(board, chess.WHITE) == 0
        assert PieceScorer.material_for(board, chess.BLACK) == 0


class TestSnapshot:
    def test_starting_snapshot(self):
        board = chess.Board()
        snap = PieceScorer.snapshot(board)
        assert snap.white_material == 39
        assert snap.black_material == 39
        assert snap.white_captured == 0
        assert snap.black_captured == 0
        assert snap.advantage == 0

    def test_advantage_calculation(self):
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        snap = PieceScorer.snapshot(board)
        assert snap.advantage == 1  # white +1

    def test_black_advantage(self):
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPP1PPPP/RNBQKBNR w KQkq - 0 1")
        # White missing a pawn
        snap = PieceScorer.snapshot(board)
        assert snap.advantage == -1  # black +1

    def test_captured_material(self):
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        snap = PieceScorer.snapshot(board)
        assert snap.white_captured == 1  # white captured 1 point of black material
        assert snap.black_captured == 0


class TestStatusText:
    def test_even_position(self):
        board = chess.Board()
        text = PieceScorer.status_text(board)
        assert "Even" in text

    def test_white_advantage_text(self):
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        text = PieceScorer.status_text(board)
        assert "White +1" in text

    def test_black_advantage_text(self):
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPP1PPPP/RNBQKBNR w KQkq - 0 1")
        text = PieceScorer.status_text(board)
        assert "Black +1" in text

    def test_contains_material_info(self):
        board = chess.Board()
        text = PieceScorer.status_text(board)
        assert "Mat" in text
        assert "W:39" in text
        assert "B:39" in text
