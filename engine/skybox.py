from pathlib import Path

import numpy as np


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SkyboxPass:
    def __init__(self, ctx, shader_dir: Path) -> None:
        self.ctx = ctx
        self.program = self.ctx.program(
            vertex_shader=_read_text(shader_dir / "skybox.vert"),
            fragment_shader=_read_text(shader_dir / "skybox.frag"),
        )

        vertices = np.array(
            [
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                -1.0,
                1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                1.0,
            ],
            dtype="f4",
        )
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.vertex_array(self.program, [(self.vbo, "3f", "in_position")])

        self.cubemap = self.ctx.texture_cube((128, 128), 3)
        self._build_cubemap()
        self.cubemap.build_mipmaps()
        self.cubemap.filter = (self.ctx.LINEAR_MIPMAP_LINEAR, self.ctx.LINEAR)
        self.cubemap.repeat_x = False
        self.cubemap.repeat_y = False

    def _build_cubemap(self) -> None:
        tops = [
            np.array([16, 32, 68], dtype=np.float32),
            np.array([20, 42, 70], dtype=np.float32),
            np.array([24, 34, 78], dtype=np.float32),
            np.array([12, 22, 50], dtype=np.float32),
            np.array([28, 36, 80], dtype=np.float32),
            np.array([18, 26, 60], dtype=np.float32),
        ]
        bottoms = [
            np.array([2, 4, 10], dtype=np.float32),
            np.array([4, 8, 14], dtype=np.float32),
            np.array([5, 7, 15], dtype=np.float32),
            np.array([1, 2, 8], dtype=np.float32),
            np.array([5, 6, 15], dtype=np.float32),
            np.array([3, 4, 12], dtype=np.float32),
        ]

        for face in range(6):
            top = tops[face]
            bottom = bottoms[face]
            t = np.linspace(0.0, 1.0, 128, dtype=np.float32).reshape(128, 1, 1)
            gradient = (top * (1.0 - t)) + (bottom * t)
            gradient = np.repeat(gradient, 128, axis=1).astype(np.uint8)
            self.cubemap.write(gradient.tobytes(), face=face)

    def render(self, view: np.ndarray, projection: np.ndarray) -> None:
        view_no_translation = np.array(view, dtype="f4", copy=True)
        view_no_translation[3, 0] = 0.0
        view_no_translation[3, 1] = 0.0
        view_no_translation[3, 2] = 0.0

        old_depth_func = self.ctx.depth_func
        self.ctx.depth_func = "<="
        self.cubemap.use(location=0)
        self.program["uSkybox"].value = 0
        self.program["uView"].write(view_no_translation.astype("f4").tobytes())
        self.program["uProjection"].write(projection.astype("f4").tobytes())
        self.vao.render()
        self.ctx.depth_func = old_depth_func
