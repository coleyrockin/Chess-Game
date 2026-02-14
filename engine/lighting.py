from dataclasses import dataclass, field
from typing import List, Sequence, Tuple, Union

Vec3 = Tuple[float, float, float]


@dataclass
class DirectionalLightDef:
    direction: Vec3 = (-0.2, -0.96, -0.18)
    color: Vec3 = (1.0, 0.99, 0.96)
    intensity: float = 4.1


@dataclass
class PointLightDef:
    position: Vec3
    color: Vec3
    intensity: float
    light_range: float


@dataclass
class SpotLightDef:
    position: Vec3
    direction: Vec3
    color: Vec3
    intensity: float
    cutoff_cos: float
    light_range: float


@dataclass
class SceneLighting:
    """
    Lighting tuned for board readability:
    - Strong neutral key light for piece definition
    - Neon accents that do not overpower board contrast
    - Turn-biased side lights so current player side is clearer
    """

    ambient_color: Vec3 = (0.1, 0.12, 0.15)
    directional: DirectionalLightDef = field(default_factory=DirectionalLightDef)
    point_lights: List[PointLightDef] = field(default_factory=list)
    spot_lights: List[SpotLightDef] = field(default_factory=list)

    @staticmethod
    def cyberpunk_defaults(board_height: float) -> "SceneLighting":
        return SceneLighting(
            ambient_color=(0.1, 0.12, 0.15),
            directional=DirectionalLightDef(
                direction=(-0.2, -0.96, -0.18),
                color=(1.0, 0.99, 0.96),
                intensity=4.1,
            ),
            point_lights=[
                PointLightDef(
                    position=(-5.5, board_height + 2.6, -6.2),
                    color=(0.25, 0.88, 1.0),
                    intensity=11.0,
                    light_range=26.0,
                ),
                PointLightDef(
                    position=(5.5, board_height + 2.6, 6.2),
                    color=(1.0, 0.32, 0.75),
                    intensity=11.0,
                    light_range=26.0,
                ),
                PointLightDef(
                    position=(0.0, board_height + 3.9, 0.0),
                    color=(0.68, 0.55, 1.0),
                    intensity=7.0,
                    light_range=20.0,
                ),
            ],
            spot_lights=[
                SpotLightDef(
                    position=(0.0, board_height + 5.4, 0.0),
                    direction=(0.0, -1.0, 0.0),
                    color=(0.58, 0.92, 1.0),
                    intensity=12.0,
                    cutoff_cos=0.9,
                    light_range=24.0,
                )
            ],
        )

    def apply_turn_bias(self, white_turn: bool, board_height: float) -> None:
        """
        Moves key accent lights toward the active player's side so the side-to-move
        is visually emphasized without changing chess logic.
        """
        z_side = -5.8 if white_turn else 5.8
        z_other = -z_side

        # Primary cyan accent on current player side, pink on opponent side.
        if len(self.point_lights) >= 1:
            self.point_lights[0].position = (-5.2, board_height + 2.7, z_side)
            self.point_lights[0].intensity = 13.0
            self.point_lights[0].color = (0.24, 0.88, 1.0)
        if len(self.point_lights) >= 2:
            self.point_lights[1].position = (5.2, board_height + 2.7, z_other)
            self.point_lights[1].intensity = 9.5
            self.point_lights[1].color = (1.0, 0.34, 0.78)
        if len(self.point_lights) >= 3:
            self.point_lights[2].position = (0.0, board_height + 4.0, 0.0)
            self.point_lights[2].intensity = 6.2
            self.point_lights[2].color = (0.64, 0.54, 1.0)

        if len(self.spot_lights) >= 1:
            self.spot_lights[0].position = (0.0, board_height + 5.5, z_side * 0.35)
            self.spot_lights[0].direction = (0.0, -1.0, 0.0)
            self.spot_lights[0].intensity = 10.5

    def upload(self, program, max_point_lights: int, max_spot_lights: int) -> None:
        self._set_uniform(program, "uAmbient", self.ambient_color)
        self._set_uniform(program, "uDirLight.direction", self.directional.direction)
        self._set_uniform(program, "uDirLight.color", self.directional.color)
        self._set_uniform(program, "uDirLight.intensity", self.directional.intensity)

        point_count = min(len(self.point_lights), max_point_lights)
        self._set_uniform(program, "uPointLightCount", point_count)
        for i in range(max_point_lights):
            if i < point_count:
                light = self.point_lights[i]
                self._set_uniform(program, f"uPointLights[{i}].position", light.position)
                self._set_uniform(program, f"uPointLights[{i}].color", light.color)
                self._set_uniform(program, f"uPointLights[{i}].intensity", light.intensity)
                self._set_uniform(program, f"uPointLights[{i}].range", light.light_range)
            else:
                self._set_uniform(program, f"uPointLights[{i}].intensity", 0.0)

        spot_count = min(len(self.spot_lights), max_spot_lights)
        self._set_uniform(program, "uSpotLightCount", spot_count)
        for i in range(max_spot_lights):
            if i < spot_count:
                light = self.spot_lights[i]
                self._set_uniform(program, f"uSpotLights[{i}].position", light.position)
                self._set_uniform(program, f"uSpotLights[{i}].direction", light.direction)
                self._set_uniform(program, f"uSpotLights[{i}].color", light.color)
                self._set_uniform(program, f"uSpotLights[{i}].intensity", light.intensity)
                self._set_uniform(program, f"uSpotLights[{i}].cutoffCos", light.cutoff_cos)
                self._set_uniform(program, f"uSpotLights[{i}].range", light.light_range)
            else:
                self._set_uniform(program, f"uSpotLights[{i}].intensity", 0.0)

    @staticmethod
    def _set_uniform(program, name: str, value: Union[Sequence[float], float, int]) -> None:
        if name in program:
            program[name].value = value
