# Neon City Chess

Cinematic two-player chess with a neon cyberpunk style.

This repo currently includes:
- A desktop Python/ModernGL game (`main.py`)
- A browser TypeScript 3D game (`web-chess/`) using Babylon.js and `chess.js`
- Unreal handoff/reference files in `unreal/`

## Highlights
- Shader-driven 3D rendering and post-processing
- Turn-based automatic camera (no player camera controls)
- Local two-player chess rules and legal move validation
- Material score/evaluation display (`P=1, N=3, B=3, R=5, Q=9`)
- Neon city visual direction with bloom/fog/reflections

## Quick Start (Desktop Python)
Requirements:
- Python 3.9+
- OpenGL 3.3+ compatible GPU/driver

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Or:

```bash
./first_launch.sh
```

## Quick Start (Browser TypeScript)
Requirements:
- Node.js 20+

```bash
cd web-chess
npm install
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

## Controls
- Left click: select a piece
- Left click a highlighted square: move piece
- `R`: reset board (desktop build)
- `Esc`: quit (desktop build)

## Project Layout
```text
engine/         # Python rendering systems (camera, lighting, fog, post FX, shaders)
game_core/      # Python chess game state + scoring
web-chess/      # Browser client (TypeScript + Babylon.js)
unreal/         # Unreal integration/handoff files
main.py         # Desktop Python entry point
```

## Development Notes
- The camera is game-directed and side-aware to keep each player oriented.
- Desktop runs in windowed mode by default.
- Browser build targets WebGPU when available and falls back to WebGL.

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT License. See `LICENSE`.
