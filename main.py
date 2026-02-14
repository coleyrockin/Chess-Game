from __future__ import annotations

import time
from pathlib import Path

try:
    import glfw
except ModuleNotFoundError as exc:
    raise SystemExit("Missing dependency: glfw. Run: pip install -r requirements.txt") from exc

try:
    import moderngl
except ModuleNotFoundError as exc:
    raise SystemExit("Missing dependency: moderngl. Run: pip install -r requirements.txt") from exc

from engine import ChessRenderer

WINDOW_TITLE = "Neon City Chess | Modern OpenGL Renderer"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 800


class App:
    def __init__(self) -> None:
        if not glfw.init():
            raise SystemExit("Failed to initialize GLFW.")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.window_hint(glfw.SAMPLES, 4)
        glfw.window_hint(glfw.SRGB_CAPABLE, glfw.TRUE)
        glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)

        self.window = glfw.create_window(DEFAULT_WIDTH, DEFAULT_HEIGHT, WINDOW_TITLE, None, None)
        if not self.window:
            glfw.terminate()
            raise SystemExit("Failed to create OpenGL window.")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

        self.ctx = moderngl.create_context()
        self.ctx.gc_mode = "auto"

        asset_root = Path(__file__).parent
        fb_width, fb_height = glfw.get_framebuffer_size(self.window)
        self.renderer = ChessRenderer(self.ctx, fb_width, fb_height, asset_root)
        self.last_time = time.perf_counter()

        glfw.set_window_user_pointer(self.window, self)
        glfw.set_framebuffer_size_callback(self.window, self._on_resize)
        glfw.set_cursor_pos_callback(self.window, self._on_cursor)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_key_callback(self.window, self._on_key)
        self.last_title = ""

    @staticmethod
    def _instance(window) -> "App":
        app = glfw.get_window_user_pointer(window)
        if app is None:
            raise RuntimeError("Window user pointer not set.")
        return app

    @staticmethod
    def _on_resize(window, width: int, height: int) -> None:
        app = App._instance(window)
        app.renderer.resize(width, height)

    @staticmethod
    def _on_cursor(window, x: float, y: float) -> None:
        app = App._instance(window)
        fx, fy = app._window_to_framebuffer_coords(x, y)
        app.renderer.on_mouse_move(fx, fy)

    @staticmethod
    def _on_mouse_button(window, button: int, action: int, mods: int) -> None:
        del mods
        app = App._instance(window)
        x, y = glfw.get_cursor_pos(window)
        fx, fy = app._window_to_framebuffer_coords(x, y)
        app.renderer.on_mouse_button(button, action, fx, fy)

    @staticmethod
    def _on_key(window, key: int, scancode: int, action: int, mods: int) -> None:
        del scancode, mods
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)
            return
        app = App._instance(window)
        app.renderer.on_key(key, action)

    def run(self) -> None:
        try:
            while not glfw.window_should_close(self.window):
                now = time.perf_counter()
                dt = min(0.05, now - self.last_time)
                self.last_time = now

                glfw.poll_events()
                self.renderer.update(dt)
                title = f"{WINDOW_TITLE} | {self.renderer.turn_status_text()} | {self.renderer.score_status_text()}"
                if title != self.last_title:
                    glfw.set_window_title(self.window, title)
                    self.last_title = title
                self.renderer.render()
                glfw.swap_buffers(self.window)
        finally:
            glfw.destroy_window(self.window)
            glfw.terminate()

    def _window_to_framebuffer_coords(self, x: float, y: float) -> tuple[float, float]:
        win_w, win_h = glfw.get_window_size(self.window)
        fb_w, fb_h = glfw.get_framebuffer_size(self.window)
        if win_w <= 0 or win_h <= 0:
            return x, y
        sx = fb_w / win_w
        sy = fb_h / win_h
        return x * sx, y * sy


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()
