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
    BOARD_FRAME = MaterialDef((0.07, 0.11, 0.2), 0.55, 0.42, 0.8, (0.0, 0.0, 0.0))
    BOARD_LIGHT = MaterialDef((0.42, 0.9, 1.0), 0.75, 0.2, 1.0, (0.08, 0.25, 0.35))
    BOARD_DARK = MaterialDef((0.1, 0.14, 0.3), 0.62, 0.28, 0.92, (0.02, 0.03, 0.08))
    BOARD_EDGE_CYAN = MaterialDef((0.35, 0.95, 1.0), 0.9, 0.05, 1.0, (0.85, 1.2, 1.5))
    BOARD_EDGE_PINK = MaterialDef((1.0, 0.4, 0.82), 0.9, 0.06, 1.0, (1.2, 0.5, 1.0))
    CITY_BUILDING = MaterialDef((0.08, 0.1, 0.15), 0.06, 0.72, 0.55, (0.0, 0.0, 0.0))
    CITY_NEON_CYAN = MaterialDef((0.4, 0.92, 1.0), 0.85, 0.07, 1.0, (1.8, 2.4, 2.8))
    CITY_NEON_PINK = MaterialDef((1.0, 0.36, 0.78), 0.83, 0.08, 1.0, (2.4, 1.0, 2.0))
    CITY_NEON_PURPLE = MaterialDef((0.78, 0.46, 1.0), 0.85, 0.09, 1.0, (1.4, 0.9, 2.5))
    WET_GROUND = MaterialDef((0.03, 0.05, 0.08), 0.96, 0.04, 1.0, (0.0, 0.0, 0.0))
    WHITE_PIECE = MaterialDef((0.86, 0.92, 0.96), 1.0, 0.07, 1.0, (0.08, 0.1, 0.12))
    BLACK_PIECE = MaterialDef((0.06, 0.06, 0.09), 0.78, 0.12, 0.95, (0.08, 0.03, 0.12))
    PIECE_SELECTION = MaterialDef((1.0, 0.62, 0.2), 0.9, 0.11, 1.0, (2.0, 1.2, 0.4))
    LEGAL_MARKER = MaterialDef((1.0, 0.95, 0.55), 0.82, 0.13, 1.0, (1.7, 1.5, 0.5))
    RAIN_STREAK = MaterialDef((0.55, 0.7, 0.95), 0.08, 0.08, 0.55, (0.2, 0.3, 0.45))
