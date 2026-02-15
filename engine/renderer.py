from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import moderngl
import numpy as np
from game_core import ChessGameState
from pyrr import Matrix44, Vector3

from .camera import CinematicCamera
from .fog import FogSettings
from .lighting import SceneLighting
from .materials import CyberpunkMaterials, MaterialDef
from .post_processing import PostProcessingPipeline
from .shadows import ShadowMapper
from .skybox import SkyboxPass
from .utils import normalize, read_shader

MAX_POINT_LIGHTS = 8
MAX_SPOT_LIGHTS = 2

# GLFW key codes used in on_key — avoids importing glfw in the renderer.
KEY_R = 82
MOUSE_LEFT = 0
ACTION_PRESS = 1

# Module-level constants for geometry to avoid repeated allocations
_CUBE_VERTICES = np.array(
    [
        # +Z
        -0.5,
        -0.5,
        0.5,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.5,
        -0.5,
        0.5,
        0.0,
        0.0,
        1.0,
        1.0,
        0.0,
        0.5,
        0.5,
        0.5,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        -0.5,
        0.5,
        0.5,
        0.0,
        0.0,
        1.0,
        0.0,
        1.0,
        # -Z
        0.5,
        -0.5,
        -0.5,
        0.0,
        0.0,
        -1.0,
        0.0,
        0.0,
        -0.5,
        -0.5,
        -0.5,
        0.0,
        0.0,
        -1.0,
        1.0,
        0.0,
        -0.5,
        0.5,
        -0.5,
        0.0,
        0.0,
        -1.0,
        1.0,
        1.0,
        0.5,
        0.5,
        -0.5,
        0.0,
        0.0,
        -1.0,
        0.0,
        1.0,
        # +X
        0.5,
        -0.5,
        0.5,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.5,
        -0.5,
        -0.5,
        1.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.5,
        0.5,
        -0.5,
        1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        0.5,
        0.5,
        0.5,
        1.0,
        0.0,
        0.0,
        0.0,
        1.0,
        # -X
        -0.5,
        -0.5,
        -0.5,
        -1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        -0.5,
        -0.5,
        0.5,
        -1.0,
        0.0,
        0.0,
        1.0,
        0.0,
        -0.5,
        0.5,
        0.5,
        -1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        -0.5,
        0.5,
        -0.5,
        -1.0,
        0.0,
        0.0,
        0.0,
        1.0,
        # +Y
        -0.5,
        0.5,
        0.5,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.5,
        0.5,
        0.5,
        0.0,
        1.0,
        0.0,
        1.0,
        0.0,
        0.5,
        0.5,
        -0.5,
        0.0,
        1.0,
        0.0,
        1.0,
        1.0,
        -0.5,
        0.5,
        -0.5,
        0.0,
        1.0,
        0.0,
        0.0,
        1.0,
        # -Y
        -0.5,
        -0.5,
        -0.5,
        0.0,
        -1.0,
        0.0,
        0.0,
        0.0,
        0.5,
        -0.5,
        -0.5,
        0.0,
        -1.0,
        0.0,
        1.0,
        0.0,
        0.5,
        -0.5,
        0.5,
        0.0,
        -1.0,
        0.0,
        1.0,
        1.0,
        -0.5,
        -0.5,
        0.5,
        0.0,
        -1.0,
        0.0,
        0.0,
        1.0,
    ],
    dtype="f4",
)

_CUBE_INDICES = np.array(
    [
        0,
        1,
        2,
        0,
        2,
        3,
        4,
        5,
        6,
        4,
        6,
        7,
        8,
        9,
        10,
        8,
        10,
        11,
        12,
        13,
        14,
        12,
        14,
        15,
        16,
        17,
        18,
        16,
        18,
        19,
        20,
        21,
        22,
        20,
        22,
        23,
    ],
    dtype="i4",
)


@dataclass
class MeshBundle:
    vao_scene: moderngl.VertexArray
    vao_shadow: moderngl.VertexArray


@dataclass
class RenderObject:
    mesh: str
    model: np.ndarray
    material: MaterialDef
    cast_shadow: bool = True
    pulse_speed: float = 0.0
    pulse_phase: float = 0.0
    pulse_strength: float = 0.0


@dataclass
class RainDrop:
    x: float
    y: float
    z: float
    speed: float
    drift: float
    length: float
    render_obj: RenderObject


@dataclass(frozen=True)
class PiecePart:
    mesh: str
    offset: Tuple[float, float, float]
    scale: Tuple[float, float, float]
    yaw_degrees: float = 0.0



def _model_matrix(
    position: Tuple[float, float, float],
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    yaw_degrees: float = 0.0,
) -> np.ndarray:
    translation = Matrix44.from_translation(Vector3(position), dtype="f4")
    rotation = Matrix44.from_y_rotation(math.radians(yaw_degrees), dtype="f4")
    scale_m = Matrix44.from_scale(Vector3(scale), dtype="f4")
    return np.array(translation * rotation * scale_m, dtype="f4")


def _cube_geometry() -> Tuple[np.ndarray, np.ndarray]:
    # Return pre-allocated module-level constants to avoid repeated allocations
    return _CUBE_VERTICES, _CUBE_INDICES


def _cylinder_geometry(segments: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    vertices: List[float] = []
    indices: List[int] = []

    # Side surface
    for i in range(segments + 1):
        t = (i / segments) * math.tau
        x = math.cos(t) * 0.5
        z = math.sin(t) * 0.5
        u = i / segments

        # Bottom and top ring vertices for smooth side normals
        vertices.extend([x, -0.5, z, x * 2.0, 0.0, z * 2.0, u, 0.0])
        vertices.extend([x, 0.5, z, x * 2.0, 0.0, z * 2.0, u, 1.0])

    for i in range(segments):
        base = i * 2
        indices.extend([base, base + 1, base + 3, base, base + 3, base + 2])

    # Top cap
    top_center_idx = len(vertices) // 8
    vertices.extend([0.0, 0.5, 0.0, 0.0, 1.0, 0.0, 0.5, 0.5])
    for i in range(segments):
        t = (i / segments) * math.tau
        x = math.cos(t) * 0.5
        z = math.sin(t) * 0.5
        vertices.extend([x, 0.5, z, 0.0, 1.0, 0.0, (x + 0.5), (z + 0.5)])
    for i in range(segments):
        a = top_center_idx + 1 + i
        b = top_center_idx + 1 + ((i + 1) % segments)
        indices.extend([top_center_idx, a, b])

    # Bottom cap
    bottom_center_idx = len(vertices) // 8
    vertices.extend([0.0, -0.5, 0.0, 0.0, -1.0, 0.0, 0.5, 0.5])
    for i in range(segments):
        t = (i / segments) * math.tau
        x = math.cos(t) * 0.5
        z = math.sin(t) * 0.5
        vertices.extend([x, -0.5, z, 0.0, -1.0, 0.0, (x + 0.5), (z + 0.5)])
    for i in range(segments):
        a = bottom_center_idx + 1 + i
        b = bottom_center_idx + 1 + ((i + 1) % segments)
        indices.extend([bottom_center_idx, b, a])

    return np.array(vertices, dtype="f4"), np.array(indices, dtype="i4")


def _cone_geometry(segments: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    vertices: List[float] = []
    indices: List[int] = []
    apex = np.array([0.0, 0.5, 0.0], dtype="f4")

    # Side surface (flat-ish faces for readable silhouette)
    for i in range(segments):
        t0 = (i / segments) * math.tau
        t1 = ((i + 1) / segments) * math.tau
        p0 = np.array([math.cos(t0) * 0.5, -0.5, math.sin(t0) * 0.5], dtype="f4")
        p1 = np.array([math.cos(t1) * 0.5, -0.5, math.sin(t1) * 0.5], dtype="f4")
        normal = normalize(np.cross(p1 - p0, apex - p0))

        base_idx = len(vertices) // 8
        vertices.extend([apex[0], apex[1], apex[2], normal[0], normal[1], normal[2], 0.5, 1.0])
        vertices.extend([p0[0], p0[1], p0[2], normal[0], normal[1], normal[2], 0.0, 0.0])
        vertices.extend([p1[0], p1[1], p1[2], normal[0], normal[1], normal[2], 1.0, 0.0])
        indices.extend([base_idx, base_idx + 1, base_idx + 2])

    # Bottom cap
    center_idx = len(vertices) // 8
    vertices.extend([0.0, -0.5, 0.0, 0.0, -1.0, 0.0, 0.5, 0.5])
    for i in range(segments):
        t = (i / segments) * math.tau
        x = math.cos(t) * 0.5
        z = math.sin(t) * 0.5
        vertices.extend([x, -0.5, z, 0.0, -1.0, 0.0, (x + 0.5), (z + 0.5)])
    for i in range(segments):
        a = center_idx + 1 + i
        b = center_idx + 1 + ((i + 1) % segments)
        indices.extend([center_idx, b, a])

    return np.array(vertices, dtype="f4"), np.array(indices, dtype="i4")


class ChessRenderer:
    def __init__(self, ctx: moderngl.Context, width: int, height: int, asset_root: Path) -> None:
        self.ctx = ctx
        self.width = max(1, width)
        self.height = max(1, height)
        self.asset_root = asset_root
        self.shader_dir = asset_root / "engine" / "shaders"

        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.board_height = 2.4
        self.elapsed = 0.0
        self.motion_blur = 0.0
        self.rng = random.Random(3441)

        self.game = ChessGameState()
        self.last_score_text = ""

        self.cursor_x = 0.0
        self.cursor_y = 0.0
        self.camera = CinematicCamera((0.0, self.board_height + 0.25, 0.0))
        self.lighting = SceneLighting.cyberpunk_defaults(self.board_height)
        self.fog = FogSettings(color=(0.04, 0.06, 0.1), density=0.02, height_falloff=0.11)

        self.scene_program = self._load_program("pbr.vert", "pbr.frag")
        self.depth_program = self._load_program("shadow_depth.vert", "shadow_depth.frag")

        self.meshes = self._build_meshes()
        self.shadow_mapper = ShadowMapper(self.ctx, self.depth_program, resolution=2048)
        self.skybox = SkyboxPass(self.ctx, self.shader_dir)
        self.post = PostProcessingPipeline(self.ctx, self.shader_dir, self.width, self.height)

        self.static_objects: List[RenderObject] = []
        self.tile_objects: Dict[int, RenderObject] = {}
        self.tile_base_materials: Dict[int, MaterialDef] = {}
        self.piece_objects: List[RenderObject] = []
        self.rain_drops: List[RainDrop] = []
        self.pulsing_objects: List[Tuple[RenderObject, MaterialDef]] = []

        self._build_environment()
        self._build_board()
        self._build_rain()
        self._rebuild_pieces()
        self._set_turn_camera_pose()
        
        # Cache uniform locations for render loop performance
        self._cache_uniform_locations()
        
        # Cache for picking ray calculations
        self._cached_inv_vp: Optional[np.ndarray] = None
        self._cached_view_hash: Optional[int] = None
        self._cached_proj_hash: Optional[int] = None

    def _load_program(self, vertex_name: str, fragment_name: str) -> moderngl.Program:
        return self.ctx.program(
            vertex_shader=read_shader(self.shader_dir / vertex_name),
            fragment_shader=read_shader(self.shader_dir / fragment_name),
        )

    def _cache_uniform_locations(self) -> None:
        """Cache uniform locations to avoid string lookups in render loop."""
        prog = self.scene_program
        self.u_model = prog.get("uModel", None)
        self.u_view = prog.get("uView", None)
        self.u_projection = prog.get("uProjection", None)
        self.u_light_space = prog.get("uLightSpaceMatrix", None)
        self.u_view_pos = prog.get("uViewPos", None)
        self.u_time = prog.get("uTime", None)
        self.u_shadow_map = prog.get("uShadowMap", None)
        self.u_skybox = prog.get("uSkybox", None)
        
        # Material uniforms
        self.u_mat_albedo = prog.get("uMaterial.albedo", None)
        self.u_mat_metallic = prog.get("uMaterial.metallic", None)
        self.u_mat_roughness = prog.get("uMaterial.roughness", None)
        self.u_mat_specular = prog.get("uMaterial.specular", None)
        self.u_mat_emissive = prog.get("uMaterial.emissive", None)
        
        # Depth program uniforms
        self.depth_u_model = self.depth_program.get("uModel", None)
        self.depth_u_light_space = self.depth_program.get("uLightSpaceMatrix", None)

    def _build_meshes(self) -> Dict[str, MeshBundle]:
        def build_mesh(vertices: np.ndarray, indices: np.ndarray) -> MeshBundle:
            vbo = self.ctx.buffer(vertices.tobytes())
            ibo = self.ctx.buffer(indices.tobytes())
            pos_vbo = self.ctx.buffer(vertices.reshape(-1, 8)[:, 0:3].astype("f4").tobytes())

            vao_scene = self.ctx.vertex_array(
                self.scene_program,
                [(vbo, "3f 3f 2f", "in_position", "in_normal", "in_uv")],
                ibo,
            )
            vao_shadow = self.ctx.vertex_array(
                self.depth_program,
                [(pos_vbo, "3f", "in_position")],
                ibo,
            )
            return MeshBundle(vao_scene=vao_scene, vao_shadow=vao_shadow)

        cube_v, cube_i = _cube_geometry()
        cyl_v, cyl_i = _cylinder_geometry(24)
        cone_v, cone_i = _cone_geometry(24)
        return {
            "cube": build_mesh(cube_v, cube_i),
            "cylinder": build_mesh(cyl_v, cyl_i),
            "cone": build_mesh(cone_v, cone_i),
        }

    def _build_environment(self) -> None:
        # Larger reflective plaza beneath board.
        self.static_objects.append(
            RenderObject(
                "cube",
                _model_matrix((0.0, -1.38, 0.0), (180.0, 0.1, 180.0)),
                CyberpunkMaterials.WET_GROUND,
                cast_shadow=False,
            )
        )

        accent_materials = [
            CyberpunkMaterials.CITY_NEON_CYAN,
            CyberpunkMaterials.CITY_NEON_PINK,
            CyberpunkMaterials.CITY_NEON_PURPLE,
        ]

        # Subtle local platform rings near the board.
        for radius, mat in [(12.0, CyberpunkMaterials.CITY_NEON_CYAN), (17.0, CyberpunkMaterials.CITY_NEON_PINK)]:
            for i in range(36):
                angle = (i / 36.0) * math.tau
                x = math.cos(angle) * radius
                z = math.sin(angle) * radius
                seg = RenderObject(
                    "cube",
                    _model_matrix((x, -1.30, z), (0.24, 0.014, 2.3), yaw_degrees=math.degrees(angle)),
                    mat,
                    cast_shadow=False,
                    pulse_speed=self.rng.uniform(1.0, 2.1),
                    pulse_phase=self.rng.uniform(0.0, math.tau),
                    pulse_strength=0.22,
                )
                self.static_objects.append(seg)
                self.pulsing_objects.append((seg, mat))

        # Skyline ring 1: medium towers.
        for i in range(48):
            angle = (i / 48.0) * math.tau
            radius = self.rng.uniform(24.0, 34.0)
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius

            w = self.rng.uniform(1.5, 3.4)
            d = self.rng.uniform(1.5, 3.8)
            h = self.rng.uniform(12.0, 30.0)
            self.static_objects.append(
                RenderObject(
                    "cube",
                    _model_matrix((x, (h * 0.5) - 1.25, z), (w, h, d)),
                    CyberpunkMaterials.CITY_BUILDING,
                    cast_shadow=True,
                )
            )

            for side in (-1.0, 1.0):
                mat = self.rng.choice(accent_materials)
                strip = RenderObject(
                    "cube",
                    _model_matrix((x + (w * 0.5 + 0.04) * side, (h * 0.58) - 1.25, z), (0.04, h * 0.55, 0.06)),
                    mat,
                    cast_shadow=False,
                    pulse_speed=self.rng.uniform(1.2, 2.4),
                    pulse_phase=self.rng.uniform(0.0, math.tau),
                    pulse_strength=0.35,
                )
                self.static_objects.append(strip)
                self.pulsing_objects.append((strip, mat))

        # Skyline ring 2: tall distant spires for depth.
        for i in range(64):
            angle = (i / 64.0) * math.tau
            radius = self.rng.uniform(40.0, 62.0)
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius

            base_h = self.rng.uniform(20.0, 48.0)
            self.static_objects.append(
                RenderObject(
                    "cube",
                    _model_matrix((x, (base_h * 0.5) - 1.25, z), (2.0, base_h, 2.0)),
                    CyberpunkMaterials.CITY_BUILDING,
                    cast_shadow=False,
                )
            )
            self.static_objects.append(
                RenderObject(
                    "cube",
                    _model_matrix((x, base_h - 1.25 + 5.0, z), (0.7, 10.0, 0.7)),
                    CyberpunkMaterials.CITY_BUILDING,
                    cast_shadow=False,
                )
            )

            spire = RenderObject(
                "cone",
                _model_matrix((x, base_h - 1.25 + 11.0, z), (0.45, 1.8, 0.45)),
                self.rng.choice(accent_materials),
                cast_shadow=False,
                pulse_speed=self.rng.uniform(1.3, 2.8),
                pulse_phase=self.rng.uniform(0.0, math.tau),
                pulse_strength=0.40,
            )
            self.static_objects.append(spire)
            self.pulsing_objects.append((spire, spire.material))

        # Floating billboard shards for skyline character.
        for _ in range(20):
            angle = self.rng.uniform(0.0, math.tau)
            radius = self.rng.uniform(18.0, 28.0)
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            y = self.rng.uniform(8.0, 18.0)
            panel = RenderObject(
                "cube",
                _model_matrix((x, y, z), (self.rng.uniform(1.8, 4.0), 0.08, self.rng.uniform(0.2, 0.35)), yaw_degrees=self.rng.uniform(0.0, 360.0)),
                self.rng.choice(accent_materials),
                cast_shadow=False,
                pulse_speed=self.rng.uniform(1.5, 3.0),
                pulse_phase=self.rng.uniform(0.0, math.tau),
                pulse_strength=0.45,
            )
            self.static_objects.append(panel)
            self.pulsing_objects.append((panel, panel.material))

    @staticmethod
    def _in_board_core(x: float, z: float) -> bool:
        return abs(x) < 10.0 and abs(z) < 10.0

    @staticmethod
    def _in_camera_corridor(x: float, z: float) -> bool:
        # Keep a wide, long lane clear for both player-side drone perspectives.
        if abs(x) < 8.5 and abs(z) < 30.0:
            return True
        # Also clear diagonal lanes used during side swaps.
        return abs(x) < 14.0 and abs(z) < 18.0

    def _build_board(self) -> None:
        self.static_objects.extend(
            [
                RenderObject(
                    "cube",
                    _model_matrix((0.0, self.board_height - 0.28, 0.0), (10.6, 0.18, 10.6)),
                    CyberpunkMaterials.BOARD_FRAME,
                    cast_shadow=True,
                ),
                RenderObject(
                    "cube",
                    _model_matrix((0.0, self.board_height - 0.2, 0.0), (9.8, 0.04, 9.8)),
                    CyberpunkMaterials.BOARD_EDGE_PINK,
                    cast_shadow=False,
                ),
                RenderObject(
                    "cube",
                    _model_matrix((0.0, self.board_height - 0.16, 0.0), (9.3, 0.03, 9.3)),
                    CyberpunkMaterials.BOARD_EDGE_CYAN,
                    cast_shadow=False,
                ),
            ]
        )

        edges = [
            ((0.0, self.board_height + 0.08, -4.02), (8.25, 0.03, 0.04), CyberpunkMaterials.BOARD_EDGE_CYAN),
            ((0.0, self.board_height + 0.08, 4.02), (8.25, 0.03, 0.04), CyberpunkMaterials.BOARD_EDGE_CYAN),
            ((-4.02, self.board_height + 0.08, 0.0), (0.04, 0.03, 8.25), CyberpunkMaterials.BOARD_EDGE_PINK),
            ((4.02, self.board_height + 0.08, 0.0), (0.04, 0.03, 8.25), CyberpunkMaterials.BOARD_EDGE_PINK),
        ]
        for pos, scale, mat in edges:
            edge = RenderObject("cube", _model_matrix(pos, scale), mat, cast_shadow=False, pulse_speed=2.0, pulse_phase=0.0, pulse_strength=0.2)
            self.static_objects.append(edge)
            self.pulsing_objects.append((edge, mat))

        for rank in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank)
                x, z = self._square_to_world(square)
                is_light = (file_idx + rank) % 2 == 0
                mat = CyberpunkMaterials.BOARD_LIGHT if is_light else CyberpunkMaterials.BOARD_DARK
                tile = RenderObject(
                    "cube",
                    _model_matrix((x, self.board_height, z), (1.0, 0.08, 1.0)),
                    mat,
                    cast_shadow=True,
                )
                self.tile_objects[square] = tile
                self.tile_base_materials[square] = mat

    def _build_rain(self) -> None:
        for _ in range(320):
            x = self.rng.uniform(-34.0, 34.0)
            y = self.rng.uniform(5.0, 25.0)
            z = self.rng.uniform(-34.0, 34.0)
            speed = self.rng.uniform(10.0, 16.0)
            drift = self.rng.uniform(-0.55, 0.55)
            length = self.rng.uniform(0.32, 0.72)
            obj = RenderObject(
                "cube",
                _model_matrix((x, y, z), (0.014, length, 0.014)),
                CyberpunkMaterials.RAIN_STREAK,
                cast_shadow=False,
            )
            self.rain_drops.append(RainDrop(x=x, y=y, z=z, speed=speed, drift=drift, length=length, render_obj=obj))

    def _square_to_world(self, square: int) -> Tuple[float, float]:
        file_idx = chess.square_file(square)
        rank = chess.square_rank(square)
        return file_idx - 3.5, rank - 3.5

    def _piece_parts(self, piece_type: int) -> List[PiecePart]:
        base: List[PiecePart] = [
            PiecePart("cylinder", (0.0, 0.05, 0.0), (0.58, 0.08, 0.58)),
            PiecePart("cylinder", (0.0, 0.11, 0.0), (0.44, 0.04, 0.44)),
        ]

        if piece_type == chess.PAWN:
            return base + [
                PiecePart("cylinder", (0.0, 0.23, 0.0), (0.24, 0.20, 0.24)),
                PiecePart("cylinder", (0.0, 0.36, 0.0), (0.16, 0.10, 0.16)),
                PiecePart("cone", (0.0, 0.50, 0.0), (0.15, 0.14, 0.15)),
            ]

        if piece_type == chess.ROOK:
            return base + [
                PiecePart("cylinder", (0.0, 0.28, 0.0), (0.34, 0.30, 0.34)),
                PiecePart("cylinder", (0.0, 0.50, 0.0), (0.44, 0.10, 0.44)),
                PiecePart("cube", (-0.20, 0.62, -0.20), (0.10, 0.10, 0.10)),
                PiecePart("cube", (-0.20, 0.62, 0.20), (0.10, 0.10, 0.10)),
                PiecePart("cube", (0.20, 0.62, -0.20), (0.10, 0.10, 0.10)),
                PiecePart("cube", (0.20, 0.62, 0.20), (0.10, 0.10, 0.10)),
            ]

        if piece_type == chess.KNIGHT:
            return base + [
                PiecePart("cylinder", (0.0, 0.24, 0.0), (0.30, 0.18, 0.30)),
                PiecePart("cube", (0.0, 0.42, -0.03), (0.22, 0.24, 0.30)),
                PiecePart("cube", (0.0, 0.62, 0.08), (0.14, 0.30, 0.18)),
                PiecePart("cube", (0.0, 0.80, 0.15), (0.10, 0.10, 0.14)),
                PiecePart("cube", (0.06, 0.88, 0.13), (0.03, 0.10, 0.03)),
                PiecePart("cube", (-0.06, 0.88, 0.13), (0.03, 0.10, 0.03)),
                PiecePart("cube", (0.0, 0.68, -0.12), (0.04, 0.22, 0.08)),
            ]

        if piece_type == chess.BISHOP:
            return base + [
                PiecePart("cylinder", (0.0, 0.24, 0.0), (0.28, 0.20, 0.28)),
                PiecePart("cylinder", (0.0, 0.45, 0.0), (0.20, 0.26, 0.20)),
                PiecePart("cone", (0.0, 0.68, 0.0), (0.14, 0.24, 0.14)),
                PiecePart("cylinder", (0.0, 0.83, 0.0), (0.08, 0.08, 0.08)),
                PiecePart("cube", (0.0, 0.72, 0.12), (0.02, 0.20, 0.04)),
            ]

        if piece_type == chess.QUEEN:
            return base + [
                PiecePart("cylinder", (0.0, 0.27, 0.0), (0.30, 0.24, 0.30)),
                PiecePart("cylinder", (0.0, 0.48, 0.0), (0.22, 0.18, 0.22)),
                PiecePart("cylinder", (0.0, 0.62, 0.0), (0.34, 0.07, 0.34)),
                PiecePart("cylinder", (0.0, 0.75, 0.0), (0.12, 0.10, 0.12)),
                PiecePart("cone", (-0.16, 0.82, 0.0), (0.05, 0.12, 0.05)),
                PiecePart("cone", (0.16, 0.82, 0.0), (0.05, 0.12, 0.05)),
                PiecePart("cone", (0.0, 0.82, -0.16), (0.05, 0.12, 0.05)),
                PiecePart("cone", (0.0, 0.82, 0.16), (0.05, 0.12, 0.05)),
                PiecePart("cone", (0.0, 0.88, 0.0), (0.06, 0.10, 0.06)),
            ]

        if piece_type == chess.KING:
            return base + [
                PiecePart("cylinder", (0.0, 0.28, 0.0), (0.30, 0.24, 0.30)),
                PiecePart("cylinder", (0.0, 0.50, 0.0), (0.22, 0.22, 0.22)),
                PiecePart("cylinder", (0.0, 0.70, 0.0), (0.12, 0.12, 0.12)),
                PiecePart("cylinder", (0.0, 0.84, 0.0), (0.04, 0.22, 0.04)),
                PiecePart("cube", (0.0, 0.91, 0.0), (0.22, 0.04, 0.04)),
                PiecePart("cube", (0.0, 0.96, 0.0), (0.04, 0.14, 0.04)),
            ]

        return base

    def _rebuild_pieces(self) -> None:
        self.piece_objects.clear()
        for square, piece in self.game.board.piece_map().items():
            x, z = self._square_to_world(square)
            base_y = self.board_height + 0.05
            mat = CyberpunkMaterials.WHITE_PIECE if piece.color == chess.WHITE else CyberpunkMaterials.BLACK_PIECE

            for part in self._piece_parts(piece.piece_type):
                world_pos = (x + part.offset[0], base_y + part.offset[1], z + part.offset[2])
                self.piece_objects.append(
                    RenderObject(
                        part.mesh,
                        _model_matrix(world_pos, part.scale, yaw_degrees=part.yaw_degrees),
                        mat,
                        cast_shadow=True,
                    )
                )

            if square == self.game.selected_square:
                self.piece_objects.append(
                    RenderObject(
                        "cube",
                        _model_matrix((x, base_y + 0.02, z), (0.72, 0.04, 0.72)),
                        CyberpunkMaterials.PIECE_SELECTION,
                        cast_shadow=False,
                    )
                )

    def resize(self, width: int, height: int) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.post.resize(self.width, self.height)
        self.ctx.viewport = (0, 0, self.width, self.height)
        # Invalidate picking cache on resize
        self._cached_inv_vp = None
        self._cached_view_hash = None
        self._cached_proj_hash = None

    def on_mouse_move(self, x: float, y: float) -> None:
        self.cursor_x = x
        self.cursor_y = y

    def on_mouse_button(self, button: int, action: int, x: float, y: float) -> None:
        if button == MOUSE_LEFT and action == ACTION_PRESS:
            square = self._pick_square(x, y)
            if square is not None:
                self._handle_square_click(square)

    def on_key(self, key: int, action: int) -> None:
        if action != ACTION_PRESS:
            return
        if key == KEY_R:
            self.game.reset()
            self._apply_game_update(refresh_turn_pose=True, board_changed=True)
            return

    def _turn_focus_point(self) -> Tuple[float, float, float]:
        white_turn = self.game.board.turn == chess.WHITE
        king_square = self.game.board.king(chess.WHITE if white_turn else chess.BLACK)
        if king_square is None:
            z_bias = -1.5 if white_turn else 1.5
            return (0.0, self.board_height + 0.48, z_bias)

        king_x, king_z = self._square_to_world(king_square)
        z_bias = -1.55 if white_turn else 1.55
        return (king_x * 0.35, self.board_height + 0.48, z_bias)

    def _set_turn_camera_pose(self) -> None:
        white_turn = self.game.board.turn == chess.WHITE
        self.camera.set_turn_view(white_turn)
        self.camera.focus_on(self._turn_focus_point())
        self.lighting.apply_turn_bias(white_turn, self.board_height)

    def _pick_square(self, mouse_x: float, mouse_y: float) -> Optional[int]:
        aspect = self.width / max(1, self.height)
        # Uniform matrices are uploaded in OpenGL column-major order.
        # Use the same convention here so unprojection matches what is rendered.
        view = self.camera.view_matrix().T
        proj = self.camera.projection_matrix(aspect).T
        
        # Cache the expensive matrix inverse operation
        view_hash = hash(view.tobytes())
        proj_hash = hash(proj.tobytes())
        
        if (self._cached_inv_vp is None or 
            self._cached_view_hash != view_hash or 
            self._cached_proj_hash != proj_hash):
            self._cached_inv_vp = np.linalg.inv(proj @ view)
            self._cached_view_hash = view_hash
            self._cached_proj_hash = proj_hash
        
        inv = self._cached_inv_vp

        x_ndc = (2.0 * mouse_x / self.width) - 1.0
        y_ndc = 1.0 - (2.0 * mouse_y / self.height)
        near = np.array([x_ndc, y_ndc, -1.0, 1.0], dtype="f4")
        far = np.array([x_ndc, y_ndc, 1.0, 1.0], dtype="f4")

        near_world = inv @ near
        far_world = inv @ far
        near_world /= near_world[3]
        far_world /= far_world[3]

        ray_origin = near_world[:3]
        ray_dir = normalize(far_world[:3] - near_world[:3])
        if abs(ray_dir[1]) < 1e-6:
            return None

        t = (self.board_height - ray_origin[1]) / ray_dir[1]
        if t < 0.0:
            return None
        hit = ray_origin + (ray_dir * t)

        file_idx = int(math.floor(hit[0] + 4.0))
        rank = int(math.floor(hit[2] + 4.0))
        if 0 <= file_idx < 8 and 0 <= rank < 8:
            return chess.square(file_idx, rank)
        return None

    def _handle_square_click(self, square: int) -> None:
        update = self.game.click_square(square)
        self._apply_game_update(
            refresh_turn_pose=update.refresh_turn_pose,
            board_changed=update.board_changed,
            selection_changed=update.selection_changed,
            focus_square=update.focus_square,
            captured=update.captured,
            moved=update.moved,
        )

    def _apply_game_update(
        self,
        refresh_turn_pose: bool = False,
        board_changed: bool = False,
        selection_changed: bool = False,
        focus_square: Optional[int] = None,
        captured: bool = False,
        moved: bool = False,
    ) -> None:
        if focus_square is not None:
            x, z = self._square_to_world(focus_square)
            self.camera.focus_on((x, self.board_height + 0.35, z))
        elif refresh_turn_pose:
            self._set_turn_camera_pose()

        if captured:
            self.camera.add_capture_shake(0.45)

        if moved:
            self.motion_blur = max(self.motion_blur, 0.85)

        if board_changed or selection_changed:
            self._rebuild_pieces()

    def turn_status_text(self) -> str:
        return self.game.turn_status_text()

    def score_status_text(self) -> str:
        self.last_score_text = self.game.score_status_text()
        return self.last_score_text

    def _effective_tile_material(self, square: int) -> MaterialDef:
        if square == self.game.selected_square:
            return CyberpunkMaterials.PIECE_SELECTION
        if square in self.game.legal_targets:
            return CyberpunkMaterials.LEGAL_MARKER
        return self.tile_base_materials[square]

    def update(self, dt: float) -> None:
        self.elapsed += dt
        self.camera.update(dt)
        self.motion_blur = max(0.0, self.motion_blur - (dt * 1.8))

        # Update pulsing materials by creating new MaterialDef instances
        # (MaterialDef is frozen/immutable, so in-place updates are not possible)
        for obj, base_mat in self.pulsing_objects:
            pulse = 1.0 + (math.sin((self.elapsed * obj.pulse_speed) + obj.pulse_phase) * obj.pulse_strength)
            emissive = tuple(channel * pulse for channel in base_mat.emissive)
            obj.material = MaterialDef(
                albedo=base_mat.albedo,
                metallic=base_mat.metallic,
                roughness=base_mat.roughness,
                specular=base_mat.specular,
                emissive=emissive,
            )

        for drop in self.rain_drops:
            drop.y -= drop.speed * dt
            drop.x += drop.drift * dt
            if drop.y < -1.3:
                drop.y = self.rng.uniform(8.0, 25.0)
                drop.x = self.rng.uniform(-34.0, 34.0)
                drop.z = self.rng.uniform(-34.0, 34.0)
            drop.render_obj.model = _model_matrix((drop.x, drop.y, drop.z), (0.014, drop.length, 0.014))

    def render(self) -> None:
        aspect = self.width / max(1, self.height)
        view = self.camera.view_matrix()
        projection = self.camera.projection_matrix(aspect)

        self.shadow_mapper.update_light_matrix(self.lighting.directional.direction, (0.0, self.board_height, 0.0))
        self._render_shadow_pass()

        self.post.begin_scene()
        self.skybox.render(view, projection)
        self._render_scene_pass(view, projection)
        self.post.apply_bloom(blur_passes=10)

        focus_depth = float(np.clip((self.camera.state.distance - 8.0) / 28.0, 0.25, 0.85))
        dof_strength = float(np.clip(0.32 + ((1.0 - focus_depth) * 0.5), 0.2, 0.78))
        camera_speed = float(np.clip(self.camera.velocity * 0.06, 0.0, 1.0))
        self.post.composite(
            exposure=1.08,
            bloom_strength=1.24,
            elapsed_time=self.elapsed,
            camera_speed=camera_speed,
            focus_depth=focus_depth,
            dof_strength=dof_strength,
            motion_blur=self.motion_blur,
        )

    def _render_shadow_pass(self) -> None:
        self.shadow_mapper.begin()
        if self.depth_u_light_space is not None:
            self.depth_u_light_space.write(self.shadow_mapper.light_space.astype("f4").tobytes())

        for obj in self.static_objects:
            if obj.cast_shadow:
                self._draw_shadow_object(obj)
        for tile in self.tile_objects.values():
            self._draw_shadow_object(tile)
        for piece in self.piece_objects:
            if piece.cast_shadow:
                self._draw_shadow_object(piece)

        self.shadow_mapper.end((self.width, self.height))

    def _render_scene_pass(self, view: np.ndarray, projection: np.ndarray) -> None:
        if self.u_view is not None:
            self.u_view.write(view.astype("f4").tobytes())
        if self.u_projection is not None:
            self.u_projection.write(projection.astype("f4").tobytes())
        if self.u_light_space is not None:
            self.u_light_space.write(self.shadow_mapper.light_space.astype("f4").tobytes())
        if self.u_view_pos is not None:
            self.u_view_pos.value = tuple(self.camera.eye.tolist())
        if self.u_time is not None:
            self.u_time.value = self.elapsed

        self.lighting.upload(self.scene_program, MAX_POINT_LIGHTS, MAX_SPOT_LIGHTS)
        self.fog.upload(self.scene_program)

        self.shadow_mapper.depth_texture.use(location=0)
        self.skybox.cubemap.use(location=1)
        if self.u_shadow_map is not None:
            self.u_shadow_map.value = 0
        if self.u_skybox is not None:
            self.u_skybox.value = 1

        for obj in self.static_objects:
            self._draw_scene_object(obj, obj.material)
        for square, tile in self.tile_objects.items():
            self._draw_scene_object(tile, self._effective_tile_material(square))
        for piece in self.piece_objects:
            self._draw_scene_object(piece, piece.material)
        for drop in self.rain_drops:
            self._draw_scene_object(drop.render_obj, drop.render_obj.material)

    def _draw_shadow_object(self, obj: RenderObject) -> None:
        mesh = self.meshes[obj.mesh]
        if self.depth_u_model is not None:
            self.depth_u_model.write(obj.model.astype("f4").tobytes())
        mesh.vao_shadow.render()

    def _draw_scene_object(self, obj: RenderObject, material: MaterialDef) -> None:
        mesh = self.meshes[obj.mesh]
        if self.u_model is not None:
            self.u_model.write(obj.model.astype("f4").tobytes())

        if self.u_mat_albedo is not None:
            self.u_mat_albedo.value = material.albedo
        if self.u_mat_metallic is not None:
            self.u_mat_metallic.value = material.metallic
        if self.u_mat_roughness is not None:
            self.u_mat_roughness.value = material.roughness
        if self.u_mat_specular is not None:
            self.u_mat_specular.value = material.specular
        if self.u_mat_emissive is not None:
            self.u_mat_emissive.value = material.emissive
        mesh.vao_scene.render()
