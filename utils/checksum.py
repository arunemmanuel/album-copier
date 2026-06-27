"""Checksum utilities for copy verification."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest for a file."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def checksums_match(source_path: Path, destination_path: Path) -> tuple[bool, str, str]:
    """Compare source and destination SHA-256 checksums."""

    source_checksum = sha256_file(source_path)
    destination_checksum = sha256_file(destination_path)
    return (
        source_checksum == destination_checksum,
        source_checksum,
        destination_checksum,
    )
