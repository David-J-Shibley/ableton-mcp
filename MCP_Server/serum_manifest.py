"""Curated Serum 2 parameter manifest (128 params for Ableton Configure)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "docs" / "serum2_params_128.json"


@lru_cache(maxsize=1)
def load_serum_manifest() -> dict:
    with _MANIFEST_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def serum_aliases() -> dict[str, dict]:
    manifest = load_serum_manifest()
    return {entry["alias"]: entry for entry in manifest["parameters"]}


def serum_names() -> dict[str, dict]:
    manifest = load_serum_manifest()
    return {entry["serum_name"].lower(): entry for entry in manifest["parameters"]}
