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
    post_processing.py
    skybox.py
    camera.py
    shadows.py
    fog.py
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
- Camera is fully automatic and game-directed.
- Perspective transitions based on turn and piece interaction.
- No player camera orbit/zoom controls.
- Game launches in a standard window by default.

## Visual direction
- Floating chessboard above a neon city
- Emissive cyan/pink/purple light strips
- Reflective wet ground and atmospheric rain
- Auto camera perspective by side-to-move

## Notes
- This renderer intentionally targets modern OpenGL and shader-based rendering.
- If your GPU is older and cannot provide OpenGL 3.3 core, startup may fail.
