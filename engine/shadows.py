import numpy as np
from pyrr import Matrix44, Vector3


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-6:
        return np.array([0.0, -1.0, 0.0], dtype="f4")
    return v / n


class ShadowMapper:
    def __init__(self, ctx, depth_program, resolution: int = 2048) -> None:
        self.ctx = ctx
        self.depth_program = depth_program
        self.resolution = resolution
        self.depth_texture = self.ctx.depth_texture((self.resolution, self.resolution))
        self.depth_texture.repeat_x = False
        self.depth_texture.repeat_y = False
        self.depth_texture.compare_func = "<="
        self.depth_fbo = self.ctx.framebuffer(depth_attachment=self.depth_texture)
        self.light_space = np.eye(4, dtype="f4")

    def update_light_matrix(self, direction: tuple[float, float, float], focus: tuple[float, float, float]) -> None:
        focus_v = np.array(focus, dtype="f4")
        light_dir = _normalize(np.array(direction, dtype="f4"))
        light_pos = focus_v - (light_dir * 28.0)

        view = Matrix44.look_at(
            Vector3(light_pos.tolist()),
            Vector3(focus_v.tolist()),
            Vector3([0.0, 1.0, 0.0]),
            dtype="f4",
        )
        proj = Matrix44.orthogonal_projection(-20.0, 20.0, -20.0, 20.0, 0.5, 90.0, dtype="f4")
        self.light_space = np.array(proj * view, dtype="f4")

    def begin(self) -> None:
        self.depth_fbo.use()
        self.ctx.viewport = (0, 0, self.resolution, self.resolution)
        self.ctx.clear(depth=1.0)
        self.ctx.enable_only(self.ctx.DEPTH_TEST)

    def end(self, viewport_size: tuple[int, int]) -> None:
        self.ctx.screen.use()
        self.ctx.viewport = (0, 0, viewport_size[0], viewport_size[1])
