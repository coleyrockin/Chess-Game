import math
from dataclasses import dataclass

import numpy as np
from pyrr import Matrix44, Vector3


def _exp_smoothing(current: float, target: float, dt: float, speed: float) -> float:
    blend = 1.0 - math.exp(-speed * max(dt, 1e-6))
    return current + ((target - current) * blend)


def _exp_smoothing_vec(current: np.ndarray, target: np.ndarray, dt: float, speed: float) -> np.ndarray:
    blend = 1.0 - math.exp(-speed * max(dt, 1e-6))
    return current + ((target - current) * blend)


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-6:
        return v
    return v / n


@dataclass
class CameraState:
    yaw: float = 45.0
    pitch: float = 33.0
    distance: float = 18.0


class CinematicCamera:
    def __init__(self, look_target: tuple[float, float, float]) -> None:
        self.state = CameraState()
        self.target_state = CameraState()
        self.target = np.array(look_target, dtype="f4")
        self.focus_target = np.array(look_target, dtype="f4")
        self.eye = np.zeros(3, dtype="f4")
        self.prev_eye = np.zeros(3, dtype="f4")
        self.velocity = 0.0
        self.shake = 0.0
        self._noise_phase = 0.0
        self.update(0.016)
        self.prev_eye = self.eye.copy()

    def set_turn_view(self, white_turn: bool) -> None:
        # White sees from White's side, Black from Black's side.
        self.target_state.yaw = 225.0 if white_turn else 45.0
        self.target_state.pitch = 30.0
        self.target_state.distance = 16.0

    def focus_on(self, point: tuple[float, float, float]) -> None:
        self.focus_target = np.array(point, dtype="f4")

    def add_capture_shake(self, amount: float) -> None:
        self.shake = min(1.0, self.shake + amount)

    def orbit(self, dx: float, dy: float) -> None:
        self.target_state.yaw += dx * 0.18
        self.target_state.pitch = float(np.clip(self.target_state.pitch + dy * 0.12, 18.0, 67.0))

    def zoom(self, delta: float) -> None:
        self.target_state.distance = float(np.clip(self.target_state.distance - delta, 10.0, 32.0))

    def update(self, dt: float) -> None:
        self.target = _exp_smoothing_vec(self.target, self.focus_target, dt, speed=7.5)
        self.state.yaw = _exp_smoothing(self.state.yaw, self.target_state.yaw, dt, speed=4.5)
        self.state.pitch = _exp_smoothing(self.state.pitch, self.target_state.pitch, dt, speed=4.5)
        self.state.distance = _exp_smoothing(self.state.distance, self.target_state.distance, dt, speed=5.2)

        yaw_r = math.radians(self.state.yaw)
        pitch_r = math.radians(self.state.pitch)
        horizontal = self.state.distance * math.cos(pitch_r)
        eye = np.array(
            [
                self.target[0] + horizontal * math.sin(yaw_r),
                self.target[1] + self.state.distance * math.sin(pitch_r),
                self.target[2] + horizontal * math.cos(yaw_r),
            ],
            dtype="f4",
        )

        if self.shake > 0.0001:
            self._noise_phase += dt * 30.0
            jitter = np.array(
                [
                    math.sin(self._noise_phase * 1.7),
                    math.cos(self._noise_phase * 2.1) * 0.45,
                    math.sin(self._noise_phase * 1.3) * 0.65,
                ],
                dtype="f4",
            )
            eye += jitter * (0.07 * self.shake)
            self.shake = max(0.0, self.shake - (dt * 2.2))

        self.eye = eye
        self.velocity = float(np.linalg.norm(self.eye - self.prev_eye) / max(dt, 1e-5))
        self.prev_eye = self.eye.copy()

    def view_matrix(self) -> np.ndarray:
        up = Vector3([0.0, 1.0, 0.0])
        return np.array(Matrix44.look_at(self.eye, self.target, up, dtype="f4"), dtype="f4")

    def projection_matrix(self, aspect_ratio: float) -> np.ndarray:
        return np.array(
            Matrix44.perspective_projection(53.0, max(aspect_ratio, 0.1), 0.1, 280.0, dtype="f4"),
            dtype="f4",
        )

    def view_projection(self, aspect_ratio: float) -> np.ndarray:
        return self.projection_matrix(aspect_ratio) @ self.view_matrix()

    def forward(self) -> np.ndarray:
        return _normalize(self.target - self.eye)
