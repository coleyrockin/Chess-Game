"""Tests for engine.utils — shared utility helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from engine.utils import normalize, normalize_safe, read_shader


class TestNormalize:
    def test_unit_vector_unchanged(self):
        v = np.array([1.0, 0.0, 0.0], dtype="f4")
        result = normalize(v)
        np.testing.assert_allclose(result, [1.0, 0.0, 0.0], atol=1e-5)

    def test_scales_to_unit(self):
        v = np.array([3.0, 4.0, 0.0], dtype="f4")
        result = normalize(v)
        np.testing.assert_allclose(np.linalg.norm(result), 1.0, atol=1e-5)
        np.testing.assert_allclose(result, [0.6, 0.8, 0.0], atol=1e-5)

    def test_zero_vector_returns_self(self):
        v = np.array([0.0, 0.0, 0.0], dtype="f4")
        result = normalize(v)
        np.testing.assert_array_equal(result, v)

    def test_near_zero_returns_self(self):
        v = np.array([1e-8, 0.0, 0.0], dtype="f4")
        result = normalize(v)
        np.testing.assert_array_equal(result, v)


class TestNormalizeSafe:
    def test_normal_input(self):
        v = np.array([0.0, 5.0, 0.0], dtype="f4")
        result = normalize_safe(v)
        np.testing.assert_allclose(result, [0.0, 1.0, 0.0], atol=1e-5)

    def test_zero_with_fallback(self):
        v = np.array([0.0, 0.0, 0.0], dtype="f4")
        fallback = np.array([0.0, -1.0, 0.0], dtype="f4")
        result = normalize_safe(v, fallback=fallback)
        np.testing.assert_array_equal(result, fallback)

    def test_zero_without_fallback(self):
        v = np.array([0.0, 0.0, 0.0], dtype="f4")
        result = normalize_safe(v)
        np.testing.assert_array_equal(result, v)


class TestReadShader:
    def test_reads_file_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".glsl", delete=False) as f:
            f.write("void main() {}")
            f.flush()
            content = read_shader(Path(f.name))
            assert content == "void main() {}"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_shader(Path("/nonexistent/shader.glsl"))
