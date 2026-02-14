from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

Vec3 = Tuple[float, float, float]


@dataclass
class DirectionalLightDef:
    direction: Vec3 = (-0.38, -0.9, -0.3)
    color: Vec3 = (0.96, 0.98, 1.0)
    intensity: float = 2.0


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
    ambient_color: Vec3 = (0.07, 0.09, 0.12)
    directional: DirectionalLightDef = field(default_factory=DirectionalLightDef)
    point_lights: List[PointLightDef] = field(default_factory=list)
    spot_lights: List[SpotLightDef] = field(default_factory=list)

    @staticmethod
    def cyberpunk_defaults(board_height: float) -> "SceneLighting":
        return SceneLighting(
            ambient_color=(0.08, 0.09, 0.13),
            directional=DirectionalLightDef(
                direction=(-0.45, -0.85, -0.25),
                color=(0.92, 0.95, 1.0),
                intensity=2.2,
            ),
            point_lights=[
                PointLightDef(
                    position=(-5.0, board_height + 2.8, -5.5),
                    color=(0.35, 0.95, 1.0),
                    intensity=22.0,
                    light_range=22.0,
                ),
                PointLightDef(
                    position=(5.8, board_height + 2.6, 5.0),
                    color=(1.0, 0.35, 0.82),
                    intensity=24.0,
                    light_range=24.0,
                ),
                PointLightDef(
                    position=(0.0, board_height + 3.8, 0.0),
                    color=(0.78, 0.45, 1.0),
                    intensity=16.0,
                    light_range=20.0,
                ),
            ],
            spot_lights=[
                SpotLightDef(
                    position=(0.0, board_height + 5.2, 0.0),
                    direction=(0.0, -1.0, 0.0),
                    color=(0.42, 0.92, 1.0),
                    intensity=20.0,
                    cutoff_cos=0.92,
                    light_range=20.0,
                )
            ],
        )

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
    def _set_uniform(program, name: str, value: Sequence[float] | float | int) -> None:
        if name in program:
            program[name].value = value
