"""Unit tests for score-global offset resolution fallbacks."""

from __future__ import annotations

import pytest

from granular_v2.offsets import boundary_ql, global_offset, global_ql


def test_global_offset_numeric_float_input():
    assert global_offset(3.5) == pytest.approx(3.5)
    assert global_ql(3.5, score=None, part=None, default=99.0) == pytest.approx(3.5)


def test_global_offset_numeric_int_input():
    assert global_offset(4) == pytest.approx(4.0)
    assert global_ql(0) == pytest.approx(0.0)


def test_global_offset_skips_none_contexts_uses_elem_offset():
    class _Element:
        offset = 2.5

    el = _Element()
    assert global_offset(el, score=None, part=None, default=0.0) == pytest.approx(2.5)


def test_global_offset_uses_get_offset_in_hierarchy():
    score = object()
    part = object()

    class _Element:
        offset = 0.0

        def getOffsetInHierarchy(self, ctx):
            if ctx is score:
                return 6.25
            if ctx is part:
                return 9.0
            raise AssertionError("unexpected context")

    el = _Element()
    assert global_offset(el, score=score, part=part) == pytest.approx(6.25)


def test_global_offset_falls_back_to_offset_when_hierarchy_raises():
    class _Element:
        offset = 7.0

        def getOffsetInHierarchy(self, _ctx):
            raise RuntimeError("hierarchy unavailable")

    el = _Element()
    assert global_offset(el, score=object(), part=object(), default=0.0) == pytest.approx(7.0)


def test_global_offset_falls_back_to_default_when_no_offset_available():
    class _Element:
        def getOffsetInHierarchy(self, _ctx):
            raise RuntimeError("hierarchy unavailable")

    el = _Element()
    assert global_offset(el, score=object(), part=object(), default=12.5) == pytest.approx(12.5)


def test_global_offset_default_when_offset_attribute_is_none():
    class _Element:
        offset = None

        def getOffsetInHierarchy(self, _ctx):
            raise RuntimeError("hierarchy unavailable")

    el = _Element()
    assert global_ql(el, score=None, part=None, default=3.0) == pytest.approx(3.0)


def test_boundary_ql_none_returns_default():
    assert boundary_ql(None, 42.0) == pytest.approx(42.0)


def test_boundary_ql_numeric_input():
    assert boundary_ql(2.5, 0.0) == pytest.approx(2.5)
    assert boundary_ql(3, 0.0) == pytest.approx(3.0)


def test_boundary_ql_object_with_offset_attribute():
    class _Boundary:
        offset = 8.0

    assert boundary_ql(_Boundary(), 0.0) == pytest.approx(8.0)


def test_boundary_ql_falls_back_to_default_without_offset():
    class _Boundary:
        pass

    assert boundary_ql(_Boundary(), 5.5) == pytest.approx(5.5)


def test_boundary_ql_tuple_endpoint_uses_default():
    """metronomeMarkBoundaries tuples are plain floats at call sites, not passed whole."""
    assert boundary_ql((0.0, 4.0, object()), 1.25) == pytest.approx(1.25)
