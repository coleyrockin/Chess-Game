from pathlib import Path

import numpy as np


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# Module-level constant for quad geometry to avoid repeated allocations
_QUAD_VERTICES = np.array(
    [
        -1.0,
        -1.0,
        0.0,
        0.0,
        1.0,
        -1.0,
        1.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        -1.0,
        -1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        -1.0,
        1.0,
        0.0,
        1.0,
    ],
    dtype="f4",
)


class PostProcessingPipeline:
    def __init__(self, ctx, shader_dir: Path, width: int, height: int) -> None:
        self.ctx = ctx
        self.shader_dir = shader_dir
        self.width = width
        self.height = height

        self.blur_program = self.ctx.program(
            vertex_shader=_read_text(shader_dir / "post_quad.vert"),
            fragment_shader=_read_text(shader_dir / "bloom_blur.frag"),
        )
        self.composite_program = self.ctx.program(
            vertex_shader=_read_text(shader_dir / "post_quad.vert"),
            fragment_shader=_read_text(shader_dir / "final_composite.frag"),
        )

        # Use pre-allocated module-level constant
        self.quad_vbo = self.ctx.buffer(_QUAD_VERTICES.tobytes())
        self.blur_vao = self.ctx.vertex_array(
            self.blur_program,
            [(self.quad_vbo, "2f 2f", "in_position", "in_uv")],
        )
        self.composite_vao = self.ctx.vertex_array(
            self.composite_program,
            [(self.quad_vbo, "2f 2f", "in_position", "in_uv")],
        )

        self.scene_fbo = None
        self.scene_color = None
        self.scene_bright = None
        self.scene_depth = None
        self.pingpong_fbo = []
        self.pingpong_textures = []
        self.bloom_texture = None
        self._rebuild_targets()

    def _make_color_tex(self):
        tex = self.ctx.texture((self.width, self.height), 4, dtype="f2")
        tex.filter = (self.ctx.LINEAR, self.ctx.LINEAR)
        tex.repeat_x = False
        tex.repeat_y = False
        return tex

    def _rebuild_targets(self) -> None:
        self.scene_color = self._make_color_tex()
        self.scene_bright = self._make_color_tex()
        self.scene_depth = self.ctx.depth_texture((self.width, self.height))
        self.scene_depth.repeat_x = False
        self.scene_depth.repeat_y = False

        self.scene_fbo = self.ctx.framebuffer(
            color_attachments=[self.scene_color, self.scene_bright],
            depth_attachment=self.scene_depth,
        )

        self.pingpong_textures = [self._make_color_tex(), self._make_color_tex()]
        self.pingpong_fbo = [
            self.ctx.framebuffer(color_attachments=[self.pingpong_textures[0]]),
            self.ctx.framebuffer(color_attachments=[self.pingpong_textures[1]]),
        ]
        self.bloom_texture = self.pingpong_textures[0]

    def resize(self, width: int, height: int) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self._rebuild_targets()

    def begin_scene(self) -> None:
        self.scene_fbo.use()
        self.ctx.viewport = (0, 0, self.width, self.height)
        self.ctx.enable(self.ctx.DEPTH_TEST)
        self.ctx.clear(0.01, 0.015, 0.03, 1.0, depth=1.0)

    def apply_bloom(self, blur_passes: int = 8) -> None:
        self.ctx.disable(self.ctx.DEPTH_TEST)
        horizontal = True
        first = True
        self.blur_program["uImage"].value = 0

        for _ in range(blur_passes):
            target_index = 0 if horizontal else 1
            self.pingpong_fbo[target_index].use()
            self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            self.blur_program["uHorizontal"].value = horizontal
            if first:
                self.scene_bright.use(location=0)
                first = False
            else:
                source_index = 1 if horizontal else 0
                self.pingpong_textures[source_index].use(location=0)
            self.blur_vao.render(self.ctx.TRIANGLES)
            horizontal = not horizontal

        last_index = 1 if horizontal else 0
        self.bloom_texture = self.pingpong_textures[last_index]
        self.ctx.enable(self.ctx.DEPTH_TEST)

    def composite(
        self,
        exposure: float,
        bloom_strength: float,
        elapsed_time: float,
        camera_speed: float,
        focus_depth: float,
        dof_strength: float,
        motion_blur: float,
    ) -> None:
        self.ctx.screen.use()
        self.ctx.viewport = (0, 0, self.width, self.height)
        self.ctx.disable(self.ctx.DEPTH_TEST)
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        self.scene_color.use(location=0)
        self.bloom_texture.use(location=1)
        self.scene_depth.use(location=2)

        self.composite_program["uScene"].value = 0
        self.composite_program["uBloom"].value = 1
        self.composite_program["uDepth"].value = 2
        self.composite_program["uExposure"].value = exposure
        self.composite_program["uBloomStrength"].value = bloom_strength
        self.composite_program["uTime"].value = elapsed_time
        self.composite_program["uCameraSpeed"].value = camera_speed
        self.composite_program["uFocusDepth"].value = focus_depth
        self.composite_program["uDofStrength"].value = dof_strength
        self.composite_program["uMotionBlur"].value = motion_blur
        self.composite_program["uResolution"].value = (float(self.width), float(self.height))

        self.composite_vao.render(self.ctx.TRIANGLES)
        self.ctx.enable(self.ctx.DEPTH_TEST)
