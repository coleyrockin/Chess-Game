"""Tests for game_core.chess_game — chess logic, move validation, and state management."""

from __future__ import annotations

import chess
import pytest

from game_core.chess_game import ChessGameState, GameUpdate


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_board_starts_standard(self):
        gs = ChessGameState()
        assert gs.board.fen() == chess.STARTING_FEN

    def test_no_selection(self):
        gs = ChessGameState()
        assert gs.selected_square is None
        assert gs.legal_targets == set()

    def test_white_to_move_first(self):
        gs = ChessGameState()
        assert gs.board.turn == chess.WHITE


# ---------------------------------------------------------------------------
# Piece selection
# ---------------------------------------------------------------------------

class TestSelection:
    def test_select_own_piece(self):
        gs = ChessGameState()
        update = gs.click_square(chess.E2)  # white pawn
        assert update.selection_changed
        assert gs.selected_square == chess.E2
        assert gs.legal_targets  # pawn on e2 has legal moves

    def test_select_opponent_piece_does_nothing(self):
        gs = ChessGameState()
        update = gs.click_square(chess.E7)  # black pawn
        assert not update.selection_changed
        assert gs.selected_square is None

    def test_select_empty_square_does_nothing(self):
        gs = ChessGameState()
        update = gs.click_square(chess.E4)
        assert not update.selection_changed
        assert gs.selected_square is None

    def test_reselect_different_piece(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        update = gs.click_square(chess.D2)
        assert update.selection_changed
        assert gs.selected_square == chess.D2

    def test_focus_square_on_selection(self):
        gs = ChessGameState()
        update = gs.click_square(chess.E2)
        assert update.focus_square == chess.E2

    @pytest.mark.parametrize("invalid_square", [-1, 64, 999])
    def test_out_of_range_square_is_ignored(self, invalid_square: int):
        gs = ChessGameState()
        update = gs.click_square(invalid_square)
        assert update == GameUpdate()
        assert gs.selected_square is None
        assert gs.legal_targets == set()


# ---------------------------------------------------------------------------
# Move execution
# ---------------------------------------------------------------------------

class TestMoves:
    def test_pawn_advance(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        update = gs.click_square(chess.E4)
        assert update.moved
        assert update.board_changed
        assert update.refresh_turn_pose
        assert not update.captured
        assert gs.board.turn == chess.BLACK

    def test_illegal_move_deselects(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        update = gs.click_square(chess.E5)  # can't jump 3 squares
        assert update.selection_changed
        assert update.refresh_turn_pose
        assert gs.selected_square is None
        assert gs.board.turn == chess.WHITE

    def test_capture_flag(self):
        gs = ChessGameState()
        # Set up a position with an immediate capture available.
        gs.board.set_fen("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        gs.click_square(chess.E4)
        update = gs.click_square(chess.D5)
        assert update.captured
        assert update.moved
        assert update.refresh_turn_pose

    def test_auto_promotion(self):
        gs = ChessGameState()
        gs.board.set_fen("8/4P3/8/8/8/8/8/4K2k w - - 0 1")
        gs.click_square(chess.E7)
        update = gs.click_square(chess.E8)
        assert update.moved
        assert update.refresh_turn_pose
        promoted = gs.board.piece_at(chess.E8)
        assert promoted is not None
        assert promoted.piece_type == chess.QUEEN

    def test_en_passant_flagged_as_capture(self):
        gs = ChessGameState()
        gs.board.set_fen("rnbqkbnr/pppp1ppp/8/4pP2/8/8/PPPPP1PP/RNBQKBNR w KQkq e6 0 3")
        gs.click_square(chess.F5)
        update = gs.click_square(chess.E6)
        assert update.captured
        assert update.refresh_turn_pose


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------

class TestGameOver:
    def test_checkmate_blocks_clicks(self):
        gs = ChessGameState()
        gs.board.set_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        assert gs.board.is_checkmate()
        update = gs.click_square(chess.E2)
        assert not update.selection_changed
        assert not update.moved

    def test_checkmate_status_text(self):
        gs = ChessGameState()
        gs.board.set_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        assert "Checkmate" in gs.turn_status_text()
        assert "Black wins" in gs.turn_status_text()

    def test_stalemate_status_text(self):
        gs = ChessGameState()
        # Black king on a8, white queen on b6, white king on c1 — black has no legal moves
        gs.board.set_fen("k7/8/1Q6/8/8/8/8/2K5 b - - 0 1")
        assert gs.board.is_stalemate()
        assert "Stalemate" in gs.turn_status_text()

    def test_insufficient_material_status_text(self):
        gs = ChessGameState()
        gs.board.set_fen("8/8/8/8/8/8/8/K6k w - - 0 1")
        assert gs.board.is_insufficient_material()
        assert gs.turn_status_text() == "Draw"


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_restores_board(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        gs.click_square(chess.E4)
        update = gs.reset()
        assert update.board_changed
        assert update.selection_changed
        assert update.refresh_turn_pose
        assert gs.board.fen() == chess.STARTING_FEN
        assert gs.selected_square is None

    def test_reset_clears_legal_targets(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        assert gs.legal_targets  # non-empty
        gs.reset()
        assert gs.legal_targets == set()


# ---------------------------------------------------------------------------
# Turn status text
# ---------------------------------------------------------------------------

class TestStatusText:
    def test_white_to_move(self):
        gs = ChessGameState()
        assert "White to move" in gs.turn_status_text()

    def test_black_to_move(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        gs.click_square(chess.E4)
        assert "Black to move" in gs.turn_status_text()

    def test_check_indicator(self):
        gs = ChessGameState()
        # Black king on e8 is in check from white queen on e7.
        gs.board.set_fen("rnbqkbnr/ppppQppp/8/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 2")
        assert gs.board.is_check()
        assert gs.turn_status_text() == "Black to move (Check)"


# ---------------------------------------------------------------------------
# Export payload
# ---------------------------------------------------------------------------

class TestExportPayload:
    def test_initial_payload(self):
        gs = ChessGameState()
        payload = gs.export_payload()
        assert payload["fen"] == chess.STARTING_FEN
        assert payload["turn"] == "white"
        assert payload["is_game_over"] is False
        assert payload["selected_square"] is None
        assert payload["legal_targets"] == []
        assert len(payload["legal_moves_uci"]) == 20  # 20 opening moves

    def test_payload_after_selection(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        payload = gs.export_payload()
        assert payload["selected_square"] == "e2"
        assert len(payload["legal_targets"]) > 0

    def test_payload_after_move(self):
        gs = ChessGameState()
        gs.click_square(chess.E2)
        gs.click_square(chess.E4)
        payload = gs.export_payload()
        assert payload["turn"] == "black"
