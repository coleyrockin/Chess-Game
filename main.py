import math
import random
import time as pytime

try:
    import chess
except ModuleNotFoundError as exc:
    missing = exc.name or "python-chess"
    raise SystemExit(
        f"Missing dependency: {missing}. Run: pip install -r requirements.txt"
    ) from exc

try:
    from ursina import Entity, Sky, Text, Ursina, Vec3, camera, color, destroy, time, window
except ModuleNotFoundError as exc:
    missing = exc.name or "ursina"
    raise SystemExit(
        f"Missing dependency: {missing}. Run: pip install -r requirements.txt"
    ) from exc

try:
    from direct.filter.CommonFilters import CommonFilters
    from direct.showbase import ShowBaseGlobal
    from panda3d.core import (
        AmbientLight,
        DirectionalLight,
        Fog,
        Material,
        Vec4,
        loadPrcFileData,
    )
except ModuleNotFoundError as exc:
    missing = exc.name or "panda3d"
    raise SystemExit(
        f"Missing dependency: {missing}. Run: pip install -r requirements.txt"
    ) from exc


def _configure_modern_gl() -> None:
    # Request HDR-friendly buffers; runtime chooses the best GL profile available.
    loadPrcFileData("", "win-size 1280 800")
    loadPrcFileData("", "framebuffer-srgb true")
    loadPrcFileData("", "framebuffer-float true")
    loadPrcFileData("", "framebuffer-multisample 1")
    loadPrcFileData("", "multisamples 4")
    loadPrcFileData("", "texture-anisotropic-degree 8")


_configure_modern_gl()


LIGHT_TILE = color.rgba(100, 248, 255, 200)
DARK_TILE = color.rgba(16, 44, 90, 225)
SELECTED_TILE = color.rgb(255, 145, 92)
LEGAL_MARKER = color.rgba(255, 240, 170, 210)
WHITE_PIECE = color.rgb(195, 255, 255)
BLACK_PIECE = color.rgb(255, 90, 210)
CITY_GROUND = color.rgb(7, 10, 18)


class NeonChess:
    def __init__(self) -> None:
        self.board = chess.Board()
        self.selected_square = None
        self.square_tiles = {}
        self.legal_markers = []
        self.piece_entities = []
        self.rain_drops = []
        self.city_blinkers = []
        self.pbr_material_targets = []
        self.volumetric_anchor = None

        self.board_height = 2.35
        self.rng = random.Random(1107)

        self.camera_yaw = 0.0
        self.camera_pitch = 31.0
        self.camera_distance = 17.0
        self.target_camera_yaw = 0.0
        self.target_camera_pitch = 31.0
        self.target_camera_distance = 17.0

        self.render_flags = []
        self.render_warnings = []
        self.filters = None
        self.pbr_materials_enabled = False
        self.base = ShowBaseGlobal.base
        self.render = self.base.render if self.base is not None else None
        if self.base is None or self.render is None:
            raise SystemExit("Renderer bootstrap failed. Start the app with `python main.py`.")

        self._configure_scene()
        self._build_city_backdrop()
        self._build_board()
        self._build_lighting()
        self._build_rain()
        self._refresh_pieces()
        self._setup_render_pipeline()
        self._update_status_text()
        self._set_camera_targets(immediate=True)
        self._update_camera()

    @staticmethod
    def _with_alpha(base_color: Vec4, alpha: int) -> Vec4:
        return color.rgba(
            int(base_color.r * 255),
            int(base_color.g * 255),
            int(base_color.b * 255),
            alpha,
        )

    def _configure_scene(self) -> None:
        window.title = "Neon City Chess"
        window.color = color.rgb(3, 6, 14)
        window.fullscreen = False
        window.exit_button.visible = True
        Sky(color=color.rgb(6, 8, 19))

        Entity(
            model="quad",
            scale=(140, 140),
            rotation_x=90,
            y=-1.25,
            color=CITY_GROUND,
        )

        wet_surface = Entity(
            model="quad",
            scale=(120, 120),
            rotation_x=90,
            y=-1.245,
            color=color.rgba(15, 22, 38, 170),
        )
        self._queue_pbr_surface(wet_surface, roughness=0.05, metallic=0.95, emission=0.02)

        self.status_text = Text(
            text="",
            x=-0.86,
            y=0.46,
            scale=1.1,
            color=color.rgba(185, 238, 255, 255),
            background=True,
        )
        self.controls_text = Text(
            text="Click piece -> click target | Auto camera by turn | R reset",
            x=-0.86,
            y=0.41,
            scale=0.9,
            color=color.rgba(220, 236, 255, 220),
        )
        self.render_text = Text(
            text="Render pipeline: initializing...",
            x=-0.86,
            y=0.36,
            scale=0.83,
            color=color.rgba(180, 220, 255, 200),
        )

    def _build_city_backdrop(self) -> None:
        for lane in range(-60, 61, 6):
            h_line = Entity(
                model="cube",
                position=(lane, -1.23, 0),
                scale=(0.04, 0.004, 120),
                color=color.rgba(80, 160, 255, 44),
            )
            self._queue_pbr_surface(h_line, roughness=0.12, metallic=0.88, emission=0.7)

            v_line = Entity(
                model="cube",
                position=(0, -1.23, lane),
                scale=(120, 0.004, 0.04),
                color=color.rgba(255, 90, 190, 34),
            )
            self._queue_pbr_surface(v_line, roughness=0.13, metallic=0.85, emission=0.7)

        building_palette = [
            color.rgb(15, 19, 30),
            color.rgb(13, 17, 32),
            color.rgb(12, 15, 27),
            color.rgb(18, 19, 35),
        ]
        accent_palette = [
            color.rgba(95, 210, 255, 230),
            color.rgba(255, 92, 203, 220),
            color.rgba(180, 120, 255, 210),
        ]

        for _ in range(170):
            x = self.rng.uniform(-38, 38)
            z = self.rng.uniform(-38, 38)
            if abs(x) < 9 and abs(z) < 9:
                continue

            w = self.rng.uniform(1.1, 3.6)
            h = self.rng.uniform(4.5, 28.0)
            tower = Entity(
                model="cube",
                position=(x, (h / 2) - 1.2, z),
                scale=(w, h, w),
                color=self.rng.choice(building_palette),
            )
            self._queue_pbr_surface(tower, roughness=0.68, metallic=0.08, emission=0.0)

            strip_color = self.rng.choice(accent_palette)
            base_r = int(strip_color.r * 255)
            base_g = int(strip_color.g * 255)
            base_b = int(strip_color.b * 255)
            strip = Entity(
                model="cube",
                parent=tower,
                position=(0, 0.25, 0.501),
                scale=(0.84, 0.11, 0.01),
                color=color.rgba(base_r, base_g, base_b, 220),
            )
            strip.pulse_rate = self.rng.uniform(1.7, 3.1)
            strip.pulse_offset = self.rng.uniform(0, 6.28)
            strip.base_alpha = 220
            strip.base_r = base_r
            strip.base_g = base_g
            strip.base_b = base_b
            self.city_blinkers.append(strip)
            self._queue_pbr_surface(strip, roughness=0.08, metallic=0.85, emission=2.1)

            beacon = Entity(
                model="sphere",
                parent=tower,
                position=(0, 0.5, 0),
                scale=(0.11, 0.11, 0.11),
                color=color.rgba(base_r, base_g, base_b, 140),
            )
            self._queue_pbr_surface(beacon, roughness=0.05, metallic=0.92, emission=2.5)

    def _build_lighting(self) -> None:
        self.ambient_np = None
        self.key_light = None
        self.key_light_np = None
        self.rim_light = None
        self.rim_light_np = None

        gsg = self.base.win.getGsg()
        if not bool(gsg.getSupportsBasicShaders()):
            return

        ambient = AmbientLight("ambient")
        ambient.setColor((0.22, 0.24, 0.3, 1.0))
        self.ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(self.ambient_np)

        self.key_light = DirectionalLight("key")
        self.key_light.setColor((0.92, 0.95, 1.0, 1.0))
        self.key_light_np = self.render.attachNewNode(self.key_light)
        self.key_light_np.setHpr(-32, -49, 0)
        self.render.setLight(self.key_light_np)

        self.rim_light = DirectionalLight("rim")
        self.rim_light.setColor((1.0, 0.55, 0.86, 1.0))
        self.rim_light_np = self.render.attachNewNode(self.rim_light)
        self.rim_light_np.setHpr(145, -23, 0)
        self.render.setLight(self.rim_light_np)

    def _build_board(self) -> None:
        board_parent = Entity(y=self.board_height)

        chassis = Entity(
            parent=board_parent,
            model="cube",
            position=(0, -0.26, 0),
            scale=(10.2, 0.15, 10.2),
            color=color.rgb(12, 23, 52),
        )
        self._queue_pbr_surface(chassis, roughness=0.55, metallic=0.45, emission=0.03)

        underglow = Entity(
            parent=board_parent,
            model="cube",
            position=(0, -0.18, 0),
            scale=(9.6, 0.03, 9.6),
            color=color.rgba(255, 130, 220, 70),
        )
        self._queue_pbr_surface(underglow, roughness=0.06, metallic=0.9, emission=1.9)

        sheen = Entity(
            parent=board_parent,
            model="cube",
            position=(0, -0.15, 0),
            scale=(9.2, 0.03, 9.2),
            color=color.rgba(80, 220, 255, 85),
        )
        self._queue_pbr_surface(sheen, roughness=0.03, metallic=0.95, emission=1.5)

        self.volumetric_anchor = Entity(
            parent=board_parent,
            model="sphere",
            position=(0, 0.2, 0),
            scale=(0.45, 0.22, 0.45),
            color=color.rgba(100, 230, 255, 110),
        )
        self._queue_pbr_surface(self.volumetric_anchor, roughness=0.02, metallic=0.85, emission=3.0)

        for rank in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank)
                x, z = self._square_to_world(square)
                tile_color = LIGHT_TILE if (file_idx + rank) % 2 == 0 else DARK_TILE
                tile = Entity(
                    parent=board_parent,
                    model="cube",
                    position=(x, 0, z),
                    scale=(1, 0.07, 1),
                    color=tile_color,
                    collider="box",
                )
                tile.default_color = tile_color
                tile.on_click = lambda s=square: self.on_square_clicked(s)
                self.square_tiles[square] = tile
                if (file_idx + rank) % 2 == 0:
                    self._queue_pbr_surface(tile, roughness=0.17, metallic=0.72, emission=0.42)
                else:
                    self._queue_pbr_surface(tile, roughness=0.28, metallic=0.62, emission=0.18)

        for edge_spec in (
            (0, 0.06, -4.02, 8.25, 0.02, 0.04, color.rgba(110, 230, 255, 180)),
            (0, 0.06, 4.02, 8.25, 0.02, 0.04, color.rgba(110, 230, 255, 180)),
            (-4.02, 0.06, 0, 0.04, 0.02, 8.25, color.rgba(255, 130, 210, 180)),
            (4.02, 0.06, 0, 0.04, 0.02, 8.25, color.rgba(255, 130, 210, 180)),
        ):
            edge = Entity(
                parent=board_parent,
                model="cube",
                position=(edge_spec[0], edge_spec[1], edge_spec[2]),
                scale=(edge_spec[3], edge_spec[4], edge_spec[5]),
                color=edge_spec[6],
            )
            self._queue_pbr_surface(edge, roughness=0.05, metallic=0.9, emission=1.7)

    def _build_rain(self) -> None:
        for _ in range(280):
            drop = Entity(
                model="cube",
                position=(
                    self.rng.uniform(-32, 32),
                    self.rng.uniform(4.5, 24),
                    self.rng.uniform(-32, 32),
                ),
                scale=(0.014, self.rng.uniform(0.28, 0.58), 0.014),
                color=color.rgba(165, 215, 255, self.rng.randint(60, 150)),
            )
            drop.fall_speed = self.rng.uniform(7.4, 14.0)
            drop.wind = self.rng.uniform(-0.55, 0.55)
            self.rain_drops.append(drop)
            self._queue_pbr_surface(drop, roughness=0.03, metallic=0.15, emission=0.35)

    def _setup_render_pipeline(self) -> None:
        # Modern Panda3D pipeline with fallback if the GPU is limited.
        self.render_flags.clear()
        self.render_warnings.clear()
        pipeline_ok = False

        gsg = self.base.win.getGsg()
        shader_major = int(gsg.getDriverShaderVersionMajor() or 0)
        shader_minor = int(gsg.getDriverShaderVersionMinor() or 0)
        shader_version = float(f"{shader_major}.{shader_minor}")
        max_texture_stages = int(gsg.getMaxTextureStages() or 0)
        supports_glsl = bool(gsg.getSupportsGlsl())
        supports_basic_shaders = bool(gsg.getSupportsBasicShaders())

        self.render_flags.append(f"GPU GLSL {shader_version:.2f}")
        self.render_flags.append(f"{max_texture_stages} texture stages")

        high_quality = supports_glsl and supports_basic_shaders and shader_major >= 3 and max_texture_stages >= 16
        medium_quality = supports_glsl and shader_major >= 2 and max_texture_stages >= 8

        if high_quality:
            try:
                import simplepbr

                simplepbr.init(
                    render_node=self.render,
                    window=self.base.win,
                    camera_node=self.base.cam,
                    taskmgr=self.base.taskMgr,
                    msaa_samples=4,
                    max_lights=12,
                    use_normal_maps=True,
                    use_emission_maps=True,
                    use_occlusion_maps=True,
                    exposure=1.12,
                    enable_shadows=True,
                    shadow_bias=0.0006,
                    enable_fog=True,
                    use_330=True,
                )
                if self.key_light is not None:
                    self.key_light.setShadowCaster(True, 2048, 2048)
                    self.key_light.getLens().setNearFar(4, 120)
                    self.key_light.getLens().setFilmSize(58, 58)
                self.render_flags.extend(["OpenGL 3.x", "PBR", "Shadow Mapping"])
                pipeline_ok = True
            except Exception as exc:
                self.render_warnings.append(f"PBR high preset failed: {exc}")

        if not pipeline_ok and medium_quality:
            try:
                import simplepbr

                simplepbr.init(
                    render_node=self.render,
                    window=self.base.win,
                    camera_node=self.base.cam,
                    taskmgr=self.base.taskMgr,
                    msaa_samples=2,
                    max_lights=6,
                    use_normal_maps=False,
                    use_emission_maps=True,
                    use_occlusion_maps=False,
                    exposure=1.0,
                    enable_shadows=False,
                    enable_fog=True,
                    use_330=False,
                )
                if self.key_light is not None:
                    self.key_light.setShadowCaster(False)
                self.render_flags.extend(["PBR (compat mode)", "Fog"])
                pipeline_ok = True
            except Exception as exc:
                self.render_warnings.append(f"PBR medium preset failed: {exc}")

        if not pipeline_ok:
            if self.key_light is not None:
                self.key_light.setShadowCaster(False)
            self.render_warnings.append("GPU is below modern shader baseline; using compatibility rendering.")

        if pipeline_ok:
            self.pbr_materials_enabled = True
            self._apply_queued_pbr_materials()
            self._refresh_pieces()

        if pipeline_ok and shader_major >= 3:
            try:
                self.filters = CommonFilters(self.base.win, self.base.cam)
                self.filters.setHighDynamicRange()
                self.filters.setExposureAdjust(0.55)
                self.filters.setBloom(
                    blend=(0.2, 0.35, 0.45, 0.0),
                    mintrigger=0.45,
                    maxtrigger=1.0,
                    desat=0.1,
                    intensity=1.3,
                    size="large",
                )
                self.filters.setAmbientOcclusion(numsamples=12, radius=0.035, amount=1.6, strength=0.02)
                if self.volumetric_anchor is not None:
                    self.filters.setVolumetricLighting(
                        self.volumetric_anchor,
                        numsamples=48,
                        density=2.6,
                        decay=0.08,
                        exposure=0.17,
                        source="color",
                    )
                self.render_flags.extend(["HDR Bloom", "AO", "Volumetric"])
            except Exception as exc:
                self.render_warnings.append(f"PostFX fallback: {exc}")
        elif pipeline_ok:
            self.render_warnings.append("PostFX disabled: shader model below 3.0 on current GPU.")

        try:
            fog = Fog("neon_fog")
            fog.setColor(0.035, 0.055, 0.09)
            fog.setExpDensity(0.017)
            self.render.setFog(fog)
            if "Fog" not in self.render_flags:
                self.render_flags.append("Fog")
        except Exception as exc:
            self.render_warnings.append(f"Fog fallback: {exc}")

        if self.render_flags:
            self.render_text.text = "Render pipeline: " + ", ".join(self.render_flags)
        else:
            self.render_text.text = "Render pipeline: compatibility mode"
        if self.render_warnings:
            self.render_text.text += " | " + self.render_warnings[0]

    @staticmethod
    def _to_vec4(c: Vec4) -> Vec4:
        alpha = c.a if hasattr(c, "a") else 1.0
        return Vec4(c.r, c.g, c.b, alpha)

    def _queue_pbr_surface(self, entity: Entity, roughness: float, metallic: float, emission: float) -> None:
        self.pbr_material_targets.append((entity, roughness, metallic, emission))

    def _apply_queued_pbr_materials(self) -> None:
        for entity, roughness, metallic, emission in self.pbr_material_targets:
            self._apply_pbr_material(entity, roughness, metallic, emission)

    def _apply_pbr_material(self, entity: Entity, roughness: float, metallic: float, emission: float) -> None:
        if not self.pbr_materials_enabled:
            return
        try:
            c = self._to_vec4(entity.color)
            material = Material()
            material.set_base_color(Vec4(c.x, c.y, c.z, max(0.12, c.w)))
            material.set_roughness(max(0.0, min(1.0, roughness)))
            material.set_metallic(max(0.0, min(1.0, metallic)))
            material.set_emission(Vec4(c.x * emission, c.y * emission, c.z * emission, 1.0))
            entity.setMaterial(material, 1)
        except Exception:
            # Some low-end backends may not accept all material parameters.
            pass

    def _square_to_world(self, square: int) -> tuple[float, float]:
        file_idx = chess.square_file(square)
        rank = chess.square_rank(square)
        return file_idx - 3.5, rank - 3.5

    def _world_piece(self, piece: chess.Piece, square: int) -> Entity:
        x, z = self._square_to_world(square)
        tone = WHITE_PIECE if piece.color == chess.WHITE else BLACK_PIECE
        root = Entity(position=(x, self.board_height + 0.1, z))
        root.base_y = self.board_height + 0.1
        root.float_seed = square * 0.33
        root.turn_speed = 16 if piece.color == chess.WHITE else -16

        glow_top = Entity(
            parent=root,
            model="sphere",
            y=0.02,
            scale=(0.64, 0.05, 0.64),
            color=self._with_alpha(tone, 90),
        )
        glow_bottom = Entity(
            parent=root,
            model="sphere",
            y=-0.12,
            scale=(0.65, 0.018, 0.65),
            color=self._with_alpha(tone, 55),
        )
        self._apply_pbr_material(glow_top, roughness=0.03, metallic=0.86, emission=2.4)
        self._apply_pbr_material(glow_bottom, roughness=0.04, metallic=0.9, emission=1.3)

        base1 = Entity(parent=root, model="cube", y=0.05, scale=(0.5, 0.06, 0.5), color=tone)
        base2 = Entity(
            parent=root,
            model="cube",
            y=0.1,
            scale=(0.38, 0.03, 0.38),
            color=color.rgba(255, 255, 255, 95),
        )
        self._apply_pbr_material(base1, roughness=0.23, metallic=0.72, emission=0.45)
        self._apply_pbr_material(base2, roughness=0.08, metallic=0.9, emission=0.95)

        ptype = piece.piece_type
        part_entities = []
        if ptype == chess.PAWN:
            part_entities.extend(
                [
                    Entity(parent=root, model="cube", y=0.2, scale=(0.26, 0.2, 0.26), color=tone),
                    Entity(parent=root, model="sphere", y=0.42, scale=0.23, color=tone),
                ]
            )
        elif ptype == chess.ROOK:
            part_entities.extend(
                [
                    Entity(parent=root, model="cube", y=0.29, scale=(0.38, 0.45, 0.38), color=tone),
                    Entity(parent=root, model="cube", y=0.56, scale=(0.5, 0.09, 0.5), color=tone),
                ]
            )
        elif ptype == chess.KNIGHT:
            part_entities.extend(
                [
                    Entity(parent=root, model="cube", y=0.24, scale=(0.3, 0.3, 0.3), color=tone),
                    Entity(parent=root, model="cube", y=0.51, scale=(0.2, 0.42, 0.2), color=tone, rotation_x=-17),
                    Entity(parent=root, model="sphere", y=0.67, scale=0.19, color=tone),
                ]
            )
        elif ptype == chess.BISHOP:
            part_entities.extend(
                [
                    Entity(parent=root, model="cube", y=0.34, scale=(0.31, 0.53, 0.31), color=tone),
                    Entity(parent=root, model="sphere", y=0.65, scale=0.16, color=tone),
                ]
            )
        elif ptype == chess.QUEEN:
            part_entities.extend(
                [
                    Entity(parent=root, model="cube", y=0.29, scale=(0.32, 0.36, 0.32), color=tone),
                    Entity(parent=root, model="sphere", y=0.57, scale=(0.46, 0.29, 0.46), color=tone),
                    Entity(parent=root, model="sphere", y=0.78, scale=0.16, color=tone),
                ]
            )
        elif ptype == chess.KING:
            part_entities.extend(
                [
                    Entity(parent=root, model="cube", y=0.3, scale=(0.33, 0.43, 0.33), color=tone),
                    Entity(parent=root, model="cube", y=0.62, scale=(0.24, 0.24, 0.24), color=tone),
                    Entity(parent=root, model="cube", y=0.84, scale=(0.08, 0.3, 0.08), color=tone),
                    Entity(parent=root, model="cube", y=0.84, scale=(0.3, 0.08, 0.08), color=tone),
                ]
            )

        for part in part_entities:
            self._apply_pbr_material(part, roughness=0.14, metallic=0.78, emission=0.95)

        return root

    def _refresh_pieces(self) -> None:
        for piece_entity in self.piece_entities:
            destroy(piece_entity)
        self.piece_entities.clear()

        for square, piece in self.board.piece_map().items():
            entity = self._world_piece(piece, square)
            self.piece_entities.append(entity)

    def _clear_legal_markers(self) -> None:
        for marker in self.legal_markers:
            destroy(marker)
        self.legal_markers.clear()

    def _set_tile_colors(self) -> None:
        for tile in self.square_tiles.values():
            tile.color = tile.default_color

        if self.selected_square is not None:
            self.square_tiles[self.selected_square].color = SELECTED_TILE

    def _draw_legal_markers(self, origin: int) -> None:
        self._clear_legal_markers()
        targets = {move.to_square for move in self.board.legal_moves if move.from_square == origin}
        for target in targets:
            x, z = self._square_to_world(target)
            marker = Entity(
                model="sphere",
                position=(x, self.board_height + 0.08, z),
                scale=(0.24, 0.04, 0.24),
                color=LEGAL_MARKER,
            )
            self._apply_pbr_material(marker, roughness=0.05, metallic=0.86, emission=2.2)
            self.legal_markers.append(marker)

    def _try_move(self, from_square: int, to_square: int) -> bool:
        candidate = chess.Move(from_square, to_square)
        if candidate in self.board.legal_moves:
            self.board.push(candidate)
            return True

        piece = self.board.piece_at(from_square)
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(to_square) in (0, 7):
            promotion = chess.Move(from_square, to_square, promotion=chess.QUEEN)
            if promotion in self.board.legal_moves:
                self.board.push(promotion)
                return True

        return False

    def on_square_clicked(self, square: int) -> None:
        if self.board.is_game_over():
            return

        clicked_piece = self.board.piece_at(square)
        turn_color = self.board.turn

        if self.selected_square is None:
            if clicked_piece and clicked_piece.color == turn_color:
                self.selected_square = square
                self._set_tile_colors()
                self._draw_legal_markers(square)
            return

        if clicked_piece and clicked_piece.color == turn_color:
            self.selected_square = square
            self._set_tile_colors()
            self._draw_legal_markers(square)
            return

        moved = self._try_move(self.selected_square, square)
        self.selected_square = None
        self._set_tile_colors()
        self._clear_legal_markers()

        if moved:
            self._refresh_pieces()
            self._update_status_text()
            self._set_camera_targets(immediate=False)

    def _update_status_text(self) -> None:
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            self.status_text.text = f"Checkmate. {winner} wins!"
            return

        if self.board.is_stalemate():
            self.status_text.text = "Stalemate."
            return

        if (
            self.board.is_insufficient_material()
            or self.board.is_seventyfive_moves()
            or self.board.is_fivefold_repetition()
        ):
            self.status_text.text = "Draw."
            return

        turn = "White" if self.board.turn == chess.WHITE else "Black"
        suffix = " (Check!)" if self.board.is_check() else ""
        self.status_text.text = f"{turn} to move{suffix}"

    @staticmethod
    def _lerp_angle(current: float, target: float, amount: float) -> float:
        delta = ((target - current + 180.0) % 360.0) - 180.0
        return current + (delta * amount)

    def _set_camera_targets(self, immediate: bool = False) -> None:
        self.target_camera_yaw = 0.0 if self.board.turn == chess.WHITE else 180.0
        self.target_camera_pitch = 30.0
        self.target_camera_distance = 17.0
        if immediate:
            self.camera_yaw = self.target_camera_yaw
            self.camera_pitch = self.target_camera_pitch
            self.camera_distance = self.target_camera_distance

    def _update_camera(self) -> None:
        pitch_rad = math.radians(self.camera_pitch)
        yaw_rad = math.radians(self.camera_yaw)
        horizontal = self.camera_distance * math.cos(pitch_rad)
        x = horizontal * math.sin(yaw_rad)
        z = -horizontal * math.cos(yaw_rad)
        y = self.camera_distance * math.sin(pitch_rad) + self.board_height + 0.55
        camera.position = Vec3(x, y, z)
        camera.look_at(Vec3(0, self.board_height + 0.2, 0))

    def input(self, key: str) -> None:
        if key == "r":
            self.board.reset()
            self.selected_square = None
            self._set_tile_colors()
            self._clear_legal_markers()
            self._refresh_pieces()
            self._update_status_text()
            self._set_camera_targets(immediate=True)
            self._update_camera()

    def update(self) -> None:
        now = pytime.time()
        blend = min(1.0, time.dt * 2.8)
        self.camera_yaw = self._lerp_angle(self.camera_yaw, self.target_camera_yaw, blend)
        self.camera_pitch += (self.target_camera_pitch - self.camera_pitch) * blend
        self.camera_distance += (self.target_camera_distance - self.camera_distance) * blend
        self._update_camera()

        for piece in self.piece_entities:
            piece.rotation_y += piece.turn_speed * time.dt
            piece.y = piece.base_y + math.sin((now * 2.25) + piece.float_seed) * 0.018

        for blinker in self.city_blinkers:
            pulse = 0.6 + (math.sin(now * blinker.pulse_rate + blinker.pulse_offset) * 0.4)
            blinker.color = color.rgba(
                blinker.base_r,
                blinker.base_g,
                blinker.base_b,
                max(20, int(blinker.base_alpha * pulse)),
            )

        for drop in self.rain_drops:
            drop.y -= drop.fall_speed * time.dt
            drop.x += drop.wind * time.dt
            if drop.y < -1.24:
                drop.y = self.rng.uniform(10.0, 24.0)
                drop.x = self.rng.uniform(-32, 32)
                drop.z = self.rng.uniform(-32, 32)


game = None


def input(key: str) -> None:
    if game is not None:
        game.input(key)


def update() -> None:
    if game is not None:
        game.update()


def main() -> None:
    global game
    app = Ursina()
    game = NeonChess()
    app.run()


if __name__ == "__main__":
    main()
