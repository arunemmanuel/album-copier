"""Filesystem helpers for the File Copy Utility."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path


def iter_filename_list(filename_list_path: Path):
    """Yield cleaned filenames from a text file, ignoring blank lines."""

    with filename_list_path.open("r", encoding="utf-8") as file:
        for line in file:
            filename = line.strip()
            if filename:
                yield filename


def read_filename_list(filename_list_path: Path) -> list[str]:
    """Read all requested filenames from a text file."""

    return list(iter_filename_list(filename_list_path))


def duplicate_counts(filenames: list[str]) -> dict[str, int]:
    """Return filenames requested more than once with their occurrence count."""

    counts = Counter(filenames)
    return {filename: count for filename, count in counts.items() if count > 1}


def unique_filenames_in_order(filenames: list[str]) -> list[str]:
    """Return first occurrences while preserving the user's input order."""

    seen: set[str] = set()
    unique: list[str] = []
    for filename in filenames:
        if filename not in seen:
            seen.add(filename)
            unique.append(filename)
    return unique


def find_source_file(source_folder: Path, filename: str) -> Path | None:
    """Find a requested file directly inside the source folder."""

    candidate = source_folder / filename
    if candidate.is_file():
        return candidate
    return None


def copy_file(source_path: Path, destination_folder: Path) -> Path:
    """Copy a file to the destination folder with metadata preserved."""

    destination_path = destination_folder / source_path.name
    shutil.copy2(source_path, destination_path)
    return destination_path
