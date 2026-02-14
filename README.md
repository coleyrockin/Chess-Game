# Neon City Chess (3D)

A stylized 3D chess game built in Python for two local players.

## Requirements
- Python 3.9+
- Internet access on first install (to download dependencies)

## Why this stack
- `Ursina`: quick 3D gameplay iteration in Python.
- `python-chess`: reliable move legality, turn handling, check/checkmate/stalemate logic.

## Current features
- Floating holographic chessboard above a cyberpunk city
- Blade Runner-style atmosphere with rain, neon skyline, and wet-street reflections
- Auto camera orientation by turn (board view flips for active player)
- Modern OpenGL/Panda3D rendering path
- Physically based shading (PBR materials)
- Shadow-capable lighting + HDR bloom + ambient occlusion
- Volumetric light/fog pass and post-processing stack
- Click-to-select and click-to-move controls
- Legal move highlighting
- Auto-queen pawn promotions
- Turn + game-state text (check, checkmate, stalemate, draw)
- Local two-player play on one machine

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

If you see a dependency error, run:
```bash
pip install -r requirements.txt
```

## Fast First Launch
```bash
./first_launch.sh
```

The renderer attempts a full modern pipeline first and falls back to a compatibility mode automatically if the GPU/driver cannot run every effect.

## Controls
- Click a piece, then click a highlighted target square.
- Camera is automatic and repositions for the player whose turn it is.
- `R`: reset game

## Next upgrades (good for "play with mom")
- Online private room (invite code)
- Piece themes (wood, crystal, vaporwave, minimal)
- Move history + undo
- Timer options and handicap mode
