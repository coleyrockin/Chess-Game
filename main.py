import math
import time as pytime

try:
    import chess
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: python-chess. Run: pip install -r requirements.txt"
    ) from exc

try:
    from ursina import (
        AmbientLight,
        DirectionalLight,
        Entity,
        Sky,
        Text,
        Ursina,
        Vec3,
        color,
        destroy,
        window,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: ursina. Run: pip install -r requirements.txt"
    ) from exc

LIGHT_TILE = color.rgb(130, 235, 255)
DARK_TILE = color.rgb(16, 44, 90)
SELECTED_TILE = color.rgb(255, 180, 90)
LEGAL_MARKER = color.rgba(255, 245, 165, 190)
WHITE_PIECE = color.rgb(232, 255, 255)
BLACK_PIECE = color.rgb(255, 120, 190)


class NeonChess:
    def __init__(self) -> None:
        self.board = chess.Board()
        self.selected_square = None
        self.square_tiles = {}
        self.legal_markers = []
        self.piece_entities = []
        self.camera_yaw = 45
        self.camera_pitch = 34
        self.camera_distance = 16

        self._configure_scene()
        self._build_board()
        self._build_lighting()
        self._refresh_pieces()
        self._update_status_text()
        self._update_camera()

    def _configure_scene(self) -> None:
        window.title = "Neon Family Chess"
        window.color = color.rgb(7, 10, 22)
        window.fullscreen = False
        window.exit_button.visible = True
        Sky(color=color.rgb(7, 10, 25))

        # Decorative layers to make the world feel less flat.
        Entity(
            model="quad",
            scale=(50, 50),
            rotation_x=90,
            y=-0.15,
            color=color.rgba(8, 16, 40, 255),
        )
        Entity(
            model="sphere",
            scale=(20, 0.03, 20),
            rotation_x=90,
            y=-0.12,
            color=color.rgba(80, 40, 110, 45),
        )

        self.status_text = Text(
            text="",
            x=-0.86,
            y=0.46,
            scale=1.15,
            color=color.azure,
            background=True,
        )
        self.controls_text = Text(
            text="Click: move | A/D rotate | W/S tilt | Z/X zoom | R reset",
            x=-0.86,
            y=0.41,
            scale=0.95,
            color=color.rgba(220, 240, 255, 220),
        )

    def _build_lighting(self) -> None:
        AmbientLight(color=color.rgba(145, 145, 195, 255))
        sun = Entity()
        sun.rotation = Vec3(45, -35, 0)
        DirectionalLight(parent=sun, y=2, z=3, shadows=True, color=color.rgba(240, 240, 255, 255))

    def _build_board(self) -> None:
        board_parent = Entity()
        border = Entity(
            parent=board_parent,
            model="cube",
            position=(0, -0.07, 0),
            scale=(8.9, 0.1, 8.9),
            color=color.rgb(20, 30, 60),
        )
        border.set_shader_input("ambient_color", Vec3(0.5, 0.5, 0.6))

        for rank in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank)
                x, z = self._square_to_world(square)
                tile_color = LIGHT_TILE if (file_idx + rank) % 2 == 0 else DARK_TILE
                tile = Entity(
                    parent=board_parent,
                    model="cube",
                    position=(x, 0, z),
                    scale=(1, 0.08, 1),
                    color=tile_color,
                    collider="box",
                )
                tile.default_color = tile_color
                tile.on_click = lambda s=square: self.on_square_clicked(s)
                self.square_tiles[square] = tile

    def _square_to_world(self, square: int) -> tuple[float, float]:
        file_idx = chess.square_file(square)
        rank = chess.square_rank(square)
        return file_idx - 3.5, rank - 3.5

    def _world_piece(self, piece: chess.Piece, square: int) -> Entity:
        x, z = self._square_to_world(square)
        tone = WHITE_PIECE if piece.color == chess.WHITE else BLACK_PIECE
        root = Entity(position=(x, 0.06, z))
        root.base_y = 0.06
        root.float_seed = square * 0.31
        root.turn_speed = 18 if piece.color == chess.WHITE else -18

        # All pieces share a glowing base ring for consistent style.
        Entity(parent=root, model="cube", y=0.05, scale=(0.54, 0.07, 0.54), color=tone)
        Entity(parent=root, model="cube", y=0.1, scale=(0.4, 0.03, 0.4), color=color.rgba(255, 255, 255, 110))

        ptype = piece.piece_type
        if ptype == chess.PAWN:
            Entity(parent=root, model="cube", y=0.2, scale=(0.28, 0.2, 0.28), color=tone)
            Entity(parent=root, model="sphere", y=0.42, scale=0.24, color=tone)
        elif ptype == chess.ROOK:
            Entity(parent=root, model="cube", y=0.28, scale=(0.4, 0.44, 0.4), color=tone)
            Entity(parent=root, model="cube", y=0.56, scale=(0.48, 0.1, 0.48), color=tone)
        elif ptype == chess.KNIGHT:
            Entity(parent=root, model="cube", y=0.22, scale=(0.32, 0.28, 0.32), color=tone)
            Entity(parent=root, model="cube", y=0.48, scale=(0.24, 0.4, 0.24), color=tone, rotation_x=-18)
            Entity(parent=root, model="sphere", y=0.66, scale=0.2, color=tone)
        elif ptype == chess.BISHOP:
            Entity(parent=root, model="cube", y=0.34, scale=(0.33, 0.52, 0.33), color=tone)
            Entity(parent=root, model="sphere", y=0.64, scale=0.16, color=tone)
        elif ptype == chess.QUEEN:
            Entity(parent=root, model="cube", y=0.28, scale=(0.33, 0.35, 0.33), color=tone)
            Entity(parent=root, model="sphere", y=0.56, scale=(0.46, 0.31, 0.46), color=tone)
            Entity(parent=root, model="sphere", y=0.78, scale=0.16, color=tone)
        elif ptype == chess.KING:
            Entity(parent=root, model="cube", y=0.29, scale=(0.34, 0.42, 0.34), color=tone)
            Entity(parent=root, model="cube", y=0.62, scale=(0.24, 0.24, 0.24), color=tone)
            Entity(parent=root, model="cube", y=0.83, scale=(0.08, 0.3, 0.08), color=tone)
            Entity(parent=root, model="cube", y=0.83, scale=(0.3, 0.08, 0.08), color=tone)

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
        targets = {m.to_square for m in self.board.legal_moves if m.from_square == origin}
        for target in targets:
            x, z = self._square_to_world(target)
            marker = Entity(
                model="sphere",
                position=(x, 0.08, z),
                scale=(0.24, 0.05, 0.24),
                color=LEGAL_MARKER,
            )
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

    def _update_status_text(self) -> None:
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            self.status_text.text = f"Checkmate. {winner} wins!"
            return

        if self.board.is_stalemate():
            self.status_text.text = "Stalemate."
            return

        if self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            self.status_text.text = "Draw."
            return

        turn = "White" if self.board.turn == chess.WHITE else "Black"
        suffix = " (Check!)" if self.board.is_check() else ""
        self.status_text.text = f"{turn} to move{suffix}"

    def _update_camera(self) -> None:
        pitch_rad = math.radians(self.camera_pitch)
        yaw_rad = math.radians(self.camera_yaw)
        horizontal = self.camera_distance * math.cos(pitch_rad)
        x = horizontal * math.sin(yaw_rad)
        z = -horizontal * math.cos(yaw_rad)
        y = self.camera_distance * math.sin(pitch_rad) + 2.6
        from ursina import camera

        camera.position = Vec3(x, y, z)
        camera.look_at(Vec3(0, 0, 0))

    def input(self, key: str) -> None:
        if key == "r":
            self.board.reset()
            self.selected_square = None
            self._set_tile_colors()
            self._clear_legal_markers()
            self._refresh_pieces()
            self._update_status_text()
            return

        if key == "a":
            self.camera_yaw -= 15
        elif key == "d":
            self.camera_yaw += 15
        elif key == "w":
            self.camera_pitch = min(self.camera_pitch + 4, 72)
        elif key == "s":
            self.camera_pitch = max(self.camera_pitch - 4, 18)
        elif key == "z":
            self.camera_distance = max(9, self.camera_distance - 0.8)
        elif key == "x":
            self.camera_distance = min(24, self.camera_distance + 0.8)
        else:
            return

        self._update_camera()

    def update(self) -> None:
        now = pytime.time()
        from ursina import time

        for piece in self.piece_entities:
            piece.rotation_y += piece.turn_speed * time.dt
            piece.y = piece.base_y + math.sin((now * 2.2) + piece.float_seed) * 0.018


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
