"""Tests for engine module imports and re-exports."""

from __future__ import annotations


class TestEngineReExports:
    """Verify the engine scoring shim re-exports from game_core."""

    def test_engine_scoring_imports(self):
        from engine.scoring import PIECE_VALUES, PieceScorer, ScoreSnapshot
        assert PieceScorer.STARTING_MATERIAL == 39
        assert hasattr(ScoreSnapshot, "__dataclass_fields__")
        assert isinstance(PIECE_VALUES, dict)

    def test_engine_scoring_same_as_game_core(self):
        from engine.scoring import PieceScorer as EnginePieceScorer
        from game_core.scoring import PieceScorer as CorePieceScorer
        assert EnginePieceScorer is CorePieceScorer

    def test_engine_init_exports(self):
        from engine import ChessRenderer, PieceScorer
        assert PieceScorer.STARTING_MATERIAL == 39


class TestGameCoreExports:
    def test_game_core_init_exports(self):
        from game_core import ChessGameState, GameUpdate, PieceScorer, ScoreSnapshot
        gs = ChessGameState()
        assert gs.board is not None
