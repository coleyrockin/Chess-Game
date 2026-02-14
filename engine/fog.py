from dataclasses import dataclass
from typing import Tuple

Vec3 = Tuple[float, float, float]


@dataclass
class FogSettings:
    color: Vec3 = (0.05, 0.07, 0.11)
    density: float = 0.045
    height_falloff: float = 0.18

    def upload(self, program) -> None:
        if "uFogColor" in program:
            program["uFogColor"].value = self.color
        if "uFogDensity" in program:
            program["uFogDensity"].value = self.density
        if "uFogHeightFalloff" in program:
            program["uFogHeightFalloff"].value = self.height_falloff
