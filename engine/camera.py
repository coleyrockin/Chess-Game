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
    yaw: float = 180.0
    pitch: float = 27.5
    distance: float = 14.0


class CinematicCamera:
    """
    Game-directed camera that behaves like a personal drone for each player.

    Turn changes trigger a visible side swap with a short cinematic arc.
    The player never controls orbit/zoom directly.
    """

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

        self.white_side = True
        self.turn_transition = 0.0
        self.transition_sign = 1.0

        self.update(0.016)
        self.prev_eye = self.eye.copy()

    def set_turn_view(self, white_turn: bool) -> None:
        if self.white_side != white_turn:
            self.turn_transition = 1.0
            self.transition_sign = 1.0 if white_turn else -1.0
            self.white_side = white_turn

        # Online chess convention: player sees from their own side.
        self.target_state.yaw = 180.0 if white_turn else 0.0
        self.target_state.pitch = 32.0
        self.target_state.distance = 15.4

    def focus_on(self, point: tuple[float, float, float]) -> None:
        self.focus_target = np.array(point, dtype="f4")

    def add_capture_shake(self, amount: float) -> None:
        self.shake = min(1.0, self.shake + amount)

    def update(self, dt: float) -> None:
        self.target = _exp_smoothing_vec(self.target, self.focus_target, dt, speed=9.2)
        self.state.yaw = _exp_smoothing(self.state.yaw, self.target_state.yaw, dt, speed=4.8)
        self.state.pitch = _exp_smoothing(self.state.pitch, self.target_state.pitch, dt, speed=5.2)
        self.state.distance = _exp_smoothing(self.state.distance, self.target_state.distance, dt, speed=5.6)

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

        # Turn handoff "drone" motion to make side swap obvious.
        if self.turn_transition > 0.0001:
            progress = 1.0 - self.turn_transition
            arc = math.sin(progress * math.pi)
            side_sway = arc * 1.55 * self.transition_sign
            up_lift = arc * 2.1

            right = np.array([math.cos(yaw_r), 0.0, -math.sin(yaw_r)], dtype="f4")
            eye += right * side_sway
            eye[1] += up_lift
            self.turn_transition = max(0.0, self.turn_transition - (dt * 1.65))

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
            eye += jitter * (0.06 * self.shake)
            self.shake = max(0.0, self.shake - (dt * 2.2))

        self.eye = eye
        self.velocity = float(np.linalg.norm(self.eye - self.prev_eye) / max(dt, 1e-5))
        self.prev_eye = self.eye.copy()

    def view_matrix(self) -> np.ndarray:
        up = Vector3([0.0, 1.0, 0.0])
        return np.array(Matrix44.look_at(self.eye, self.target, up, dtype="f4"), dtype="f4")

    def projection_matrix(self, aspect_ratio: float) -> np.ndarray:
        return np.array(
            Matrix44.perspective_projection(50.0, max(aspect_ratio, 0.1), 0.1, 280.0, dtype="f4"),
            dtype="f4",
        )

    def forward(self) -> np.ndarray:
        return _normalize(self.target - self.eye)
