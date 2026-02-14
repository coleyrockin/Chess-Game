from dataclasses import dataclass
from typing import Tuple

Color3 = Tuple[float, float, float]


@dataclass(frozen=True)
class MaterialDef:
    albedo: Color3
    metallic: float
    roughness: float
    specular: float
    emissive: Color3


class CyberpunkMaterials:
    BOARD_FRAME = MaterialDef((0.07, 0.1, 0.17), 0.5, 0.48, 0.8, (0.0, 0.0, 0.0))
    BOARD_LIGHT = MaterialDef((0.2, 0.28, 0.38), 0.58, 0.34, 0.95, (0.012, 0.016, 0.024))
    BOARD_DARK = MaterialDef((0.06, 0.09, 0.15), 0.52, 0.48, 0.9, (0.004, 0.006, 0.012))
    BOARD_EDGE_CYAN = MaterialDef((0.35, 0.95, 1.0), 0.88, 0.07, 1.0, (0.22, 0.34, 0.42))
    BOARD_EDGE_PINK = MaterialDef((1.0, 0.4, 0.82), 0.88, 0.08, 1.0, (0.34, 0.16, 0.28))
    CITY_BUILDING = MaterialDef((0.08, 0.1, 0.15), 0.06, 0.72, 0.55, (0.0, 0.0, 0.0))
    CITY_NEON_CYAN = MaterialDef((0.4, 0.92, 1.0), 0.85, 0.07, 1.0, (1.5, 2.0, 2.3))
    CITY_NEON_PINK = MaterialDef((1.0, 0.36, 0.78), 0.83, 0.08, 1.0, (1.95, 0.85, 1.6))
    CITY_NEON_PURPLE = MaterialDef((0.78, 0.46, 1.0), 0.85, 0.09, 1.0, (1.1, 0.75, 1.9))
    WET_GROUND = MaterialDef((0.03, 0.05, 0.08), 0.96, 0.06, 1.0, (0.0, 0.0, 0.0))
    WHITE_PIECE = MaterialDef((0.93, 0.95, 0.98), 0.95, 0.09, 1.0, (0.05, 0.05, 0.06))
    BLACK_PIECE = MaterialDef((0.03, 0.04, 0.06), 0.8, 0.16, 0.98, (0.035, 0.016, 0.04))
    PIECE_SELECTION = MaterialDef((1.0, 0.62, 0.2), 0.9, 0.13, 1.0, (0.9, 0.48, 0.18))
    LEGAL_MARKER = MaterialDef((1.0, 0.95, 0.55), 0.82, 0.16, 1.0, (0.65, 0.6, 0.2))
    RAIN_STREAK = MaterialDef((0.55, 0.7, 0.95), 0.08, 0.08, 0.55, (0.2, 0.3, 0.45))
