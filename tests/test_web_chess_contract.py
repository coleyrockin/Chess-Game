"""Contract tests for critical web chess runtime hooks and input plumbing."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_TS = REPO_ROOT / "web-chess" / "src" / "main.ts"
BOARD_SCENE_TS = REPO_ROOT / "web-chess" / "src" / "boardScene.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestWebChessAutomationHooks:
    def test_main_exposes_text_and_time_hooks(self):
        source = _read(MAIN_TS)
        assert "render_game_to_text" in source
        assert "advanceTime" in source

    def test_main_has_required_keyboard_controls(self):
        source = _read(MAIN_TS)
        assert "key === 'r'" in source
        assert "key === 'f'" in source
        assert "key === 'escape'" in source


class TestWebChessInputPath:
    def test_board_scene_has_pointer_pick_and_click_fallback(self):
        source = _read(BOARD_SCENE_TS)
        assert "PointerEventTypes.POINTERPICK" in source
        assert "addEventListener('click'" in source
        assert "this.scene.pick" in source
