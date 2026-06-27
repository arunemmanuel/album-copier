"""Filesystem helpers for the File Copy Utility."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Iterable

from models.result_model import OVERWRITE_RENAME, OVERWRITE_REPLACE, OVERWRITE_SKIP


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


def find_source_matches(
    source_folder: Path, filename: str, recursive: bool = False
) -> list[Path]:
    """Find matching files in the source folder."""

    if recursive:
        return sorted(path for path in source_folder.rglob(filename) if path.is_file())

    candidate = source_folder / filename
    return [candidate] if candidate.is_file() else []


def find_source_file(
    source_folder: Path, filename: str, recursive: bool = False
) -> Path | None:
    """Find the first matching source file."""

    matches = find_source_matches(source_folder, filename, recursive)
    return matches[0] if matches else None


def next_available_path(destination_path: Path) -> Path:
    """Return a non-existing destination path by appending a numeric suffix."""

    if not destination_path.exists():
        return destination_path

    stem = destination_path.stem
    suffix = destination_path.suffix
    parent = destination_path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def destination_for_policy(destination_folder: Path, filename: str, policy: str) -> Path:
    """Resolve the destination path for an overwrite policy."""

    destination_path = destination_folder / filename
    if policy == OVERWRITE_RENAME:
        return next_available_path(destination_path)
    return destination_path


def copy_file_to_path(source_path: Path, destination_path: Path) -> Path:
    """Copy a file to an explicit destination path with metadata preserved."""

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    return destination_path


def copy_file_with_policy(
    source_path: Path, destination_folder: Path, policy: str = OVERWRITE_SKIP
) -> Path | None:
    """Copy a file according to the selected overwrite policy."""

    destination_path = destination_folder / source_path.name
    if destination_path.exists() and policy == OVERWRITE_SKIP:
        return None
    if destination_path.exists() and policy == OVERWRITE_RENAME:
        destination_path = next_available_path(destination_path)
    elif policy == OVERWRITE_REPLACE:
        destination_path = destination_folder / source_path.name
    return copy_file_to_path(source_path, destination_path)


def copy_file(source_path: Path, destination_folder: Path) -> Path:
    """Copy a file to the destination folder with metadata preserved."""

    return copy_file_to_path(source_path, destination_folder / source_path.name)


def table_rows(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> list[list[str]]:
    """Build a CSV-friendly table with headers and rows."""

    return [list(headers), *[list(row) for row in rows]]
