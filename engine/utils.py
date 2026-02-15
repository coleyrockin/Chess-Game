"""Shared utility functions for the engine package."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def normalize(v: np.ndarray) -> np.ndarray:
    """Return unit-length vector, or the original vector if near-zero length."""
    n = np.linalg.norm(v)
    if n < 1e-6:
        return v
    return v / n


def normalize_safe(v: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    """Return unit-length vector with a configurable fallback for zero-length input."""
    n = np.linalg.norm(v)
    if n < 1e-6:
        if fallback is not None:
            return fallback
        return v
    return v / n


def read_shader(path: Path) -> str:
    """Read a shader or other text asset from disk."""
    return path.read_text(encoding="utf-8")
