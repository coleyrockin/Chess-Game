# Neon City Chess (ModernGL)

Cinematic cyberpunk 3D chess with a modern OpenGL renderer in Python.

## Rendering stack
- ModernGL programmable pipeline
- GLSL shaders (vertex + fragment)
- Shadow depth pass + PCF shadow sampling
- HDR scene framebuffer + bloom blur chain
- Skybox cubemap reflections
- Volumetric-style fog and post-processing (FXAA-like smoothing, vignette, film grain, DOF, motion blur)

## Engine architecture
```
engine/
    renderer.py
    shaders/
        pbr.vert
        pbr.frag
        shadow_depth.vert
        shadow_depth.frag
        skybox.vert
        skybox.frag
        post_quad.vert
        bloom_blur.frag
        final_composite.frag
    lighting.py
    materials.py
    scoring.py
    post_processing.py
    skybox.py
    camera.py
    shadows.py
    fog.py

game_core/
    chess_game.py
    scoring.py

unreal/
    README.md
    chess_state.schema.json
    sample_state.json
    export_state.py
    Source/
        NeonCityChess/
            NeonCityChess.Build.cs
            Public/
            Private/
```

## Requirements
- Python 3.9+
- A GPU/driver with OpenGL 3.3 core support

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Fast first launch
```bash
./first_launch.sh
```

## Controls
- Left-click: select/move piece
- `R`: reset board
- `Esc`: quit

Camera behavior:
- Camera is fully automatic and game-directed ("personal drone" per side).
- Clear side-to-move perspective swap on every turn.
- Board focus shifts to the active side's king area, then to selected pieces.
- No player camera orbit/zoom controls.
- Game launches in a standard window by default.

Scoring system:
- Built-in material scoring (`P=1, N=3, B=3, R=5, Q=9`).
- Live score appears in the window title:
  `Mat W:x B:y | Caps W:x B:y | White +n / Black +n / Even`.

## Visual direction
- Floating chessboard above a neon city
- Emissive cyan/pink/purple light strips
- Reflective wet ground and atmospheric rain
- Auto camera perspective by side-to-move

## Notes
- This renderer intentionally targets modern OpenGL and shader-based rendering.
- If your GPU is older and cannot provide OpenGL 3.3 core, startup may fail.
- Unreal migration handoff lives in `/Users/boydroberts/Documents/projects/Chess Game/unreal/`.
