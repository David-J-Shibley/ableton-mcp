#!/usr/bin/env python3
"""Install the AbletonMCP Remote Script into Ableton Live's User Remote Scripts folder."""

from __future__ import annotations

import argparse
import platform
import shutil
import sys
from pathlib import Path

REMOTE_SCRIPT_NAME = "AbletonMCP"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def remote_script_source() -> Path:
    source = project_root() / "AbletonMCP_Remote_Script"
    if not source.is_dir():
        raise FileNotFoundError(f"Remote Script source not found: {source}")
    return source


def candidate_dirs() -> list[Path]:
    system = platform.system()
    if system == "Darwin":
        candidates = [
            Path.home() / "Music" / "Ableton" / "User Library" / "Remote Scripts",
        ]
        prefs = Path.home() / "Library" / "Preferences" / "Ableton"
        if prefs.is_dir():
            for version_dir in sorted(prefs.iterdir(), reverse=True):
                user_remote = version_dir / "User Remote Scripts"
                if user_remote.is_dir():
                    candidates.append(user_remote)
        return candidates

    if system == "Windows":
        candidates = [
            Path.home() / "Documents" / "Ableton" / "User Library" / "Remote Scripts",
        ]
        appdata = Path.home() / "AppData" / "Roaming" / "Ableton"
        if appdata.is_dir():
            for version_dir in sorted(appdata.iterdir(), reverse=True):
                user_remote = version_dir / "Preferences" / "User Remote Scripts"
                if user_remote.is_dir():
                    candidates.append(user_remote)
        return candidates

    raise SystemExit(f"Unsupported platform: {system}")


def choose_target(explicit: Path | None) -> Path:
    if explicit is not None:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit

    existing = [path for path in candidate_dirs() if path.is_dir()]
    if existing:
        return existing[0]

    default = candidate_dirs()[0]
    default.mkdir(parents=True, exist_ok=True)
    return default


def install(target_dir: Path, *, dry_run: bool = False) -> Path:
    source = remote_script_source()
    destination = target_dir / REMOTE_SCRIPT_NAME

    if dry_run:
        print(f"Would copy {source} -> {destination}")
        return destination

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    print(f"Installed Remote Script to {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dir",
        type=Path,
        help="Ableton User Remote Scripts directory",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = choose_target(args.target_dir)
    install(target, dry_run=args.dry_run)
    print()
    print("Next steps:")
    print("1. Open Ableton Live")
    print("2. Preferences → Link, Tempo & MIDI")
    print(f'3. Control Surface: choose "{REMOTE_SCRIPT_NAME}"')
    print("4. Set Input and Output to None")


if __name__ == "__main__":
    main()
