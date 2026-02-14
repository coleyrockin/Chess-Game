# Unreal Migration Pack (UE5)

This folder is the Unreal handoff target for Neon City Chess.

## What is already refactored
- Chess rules, turn handling, move validation, and scoring are now engine-agnostic in:
  - `/Users/boydroberts/Documents/projects/Chess Game/game_core/chess_game.py`
  - `/Users/boydroberts/Documents/projects/Chess Game/game_core/scoring.py`
- Python renderer now consumes `game_core` instead of owning chess logic.

## Recommended UE version
- Unreal Engine 5.4+ (5.5+ preferred)

## Included UE5 code
```
Source/NeonCityChess/
    NeonCityChess.Build.cs
    Public/NeonCityChess.h
    Private/NeonCityChess.cpp
    Public/ChessTypes.h
    Public/ChessGameStateComponent.h
    Private/ChessGameStateComponent.cpp
    Public/ChessBoardActor.h
    Private/ChessBoardActor.cpp
    Public/ChessCameraDirector.h
    Private/ChessCameraDirector.cpp
    Public/ChessLightingDirector.h
    Private/ChessLightingDirector.cpp
```

This is a UE C++ bridge module. It lets Unreal drive board interaction while Python `game_core` remains the authoritative chess rules engine.

## System mapping (Python -> Unreal)
- `game_core/chess_game.py` -> `UChessGameStateComponent`
- `game_core/scoring.py` -> `UChessScoreLibrary` (or methods on game state component)
- `engine/camera.py` -> `AChessCameraDirector`
- `engine/lighting.py` -> `AChessLightingDirector`
- `engine/renderer.py` board/piece placement -> `AChessBoardActor` + `AChessPieceActor`

## State data contract
- Schema: `/Users/boydroberts/Documents/projects/Chess Game/unreal/chess_state.schema.json`
- Example: `/Users/boydroberts/Documents/projects/Chess Game/unreal/sample_state.json`
- Exporter: `/Users/boydroberts/Documents/projects/Chess Game/unreal/export_state.py`
- Exporter supports move replay:
  - `python3 unreal/export_state.py --fen "<fen>" --moves "e2e4,e7e5" --output /tmp/state.json`

## Wiring steps in Unreal
1. Create a UE5 **C++** project `NeonCityChessUE`.
2. Copy `/Users/boydroberts/Documents/projects/Chess Game/unreal/Source/NeonCityChess` into your project `Source/`.
3. In editor (or defaults), set these on `UChessGameStateComponent`:
   - `PythonExecutable` = `python3` (or full venv path)
   - `ExportScriptPath` = absolute path to `/Users/boydroberts/Documents/projects/Chess Game/unreal/export_state.py`
   - `WorkingDirectory` = `/Users/boydroberts/Documents/projects/Chess Game`
4. Place in level:
   - Actor with `UChessGameStateComponent`
   - `AChessBoardActor` and assign `GameStateComponent`
   - `AChessCameraDirector` and assign `GameStateComponent`
   - `AChessLightingDirector` and assign `GameStateComponent`
5. Route click hit location into `AChessBoardActor::ClickWorldLocation`.
6. Bind UI widgets to `CurrentState.StatusText`, `CurrentState.ScoreText`, and `CurrentState.Turn`.

## First Unreal milestone
1. Validate click-to-move is fully functional in UE using Python bridge.
2. Replace placeholder board/piece meshes with Nanite assets.
3. Replace basic lights with Lumen-tuned cinematic rig.
4. Port Python bridge logic from `UChessGameStateComponent` into native UE chess rules if you want a Python-free shipping build.
