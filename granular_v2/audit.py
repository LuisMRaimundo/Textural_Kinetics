"""Structured processing warnings for exported analysis."""

from __future__ import annotations

from typing import Any, Dict, List, MutableMapping


def append_warning(audit: MutableMapping[str, Any], code: str, message: str) -> None:
    """Add a machine-readable warning to an audit dict (e.g. tempo_audit)."""
    w = audit.setdefault("warnings", [])
    if not isinstance(w, list):
        w = []
        audit["warnings"] = w
    warnings: List[Dict[str, str]] = w
    warnings.append({"code": code, "message": message})


def merge_audits(*audits: Dict[str, Any]) -> Dict[str, Any]:
    """Merge audit dicts; later keys override, warnings are concatenated."""
    out: Dict[str, Any] = {}
    all_warnings: List[Dict[str, str]] = []
    for a in audits:
        if not a:
            continue
        w = a.get("warnings") or []
        if isinstance(w, list):
            all_warnings.extend(w)
        for k, v in a.items():
            if k != "warnings":
                out[k] = v
    if all_warnings:
        out["warnings"] = all_warnings
    return out
