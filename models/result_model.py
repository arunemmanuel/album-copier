"""Dataclasses and summary helpers for file copy results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CopiedFile:
    """Information about a successfully copied file."""

    filename: str
    source_path: Path
    destination_path: Path
    copy_time: datetime


@dataclass(frozen=True)
class MissingFile:
    """Information about a requested file that was not found."""

    filename: str


@dataclass(frozen=True)
class DuplicateRequest:
    """Information about a repeated filename request."""

    filename: str
    occurrence_count: int


@dataclass(frozen=True)
class AlreadyExistsFile:
    """Information about a requested file already present at destination."""

    filename: str
    destination_path: Path


@dataclass
class CopyResults:
    """Aggregated results for a copy operation."""

    total_filenames: int = 0
    copied_files: list[CopiedFile] = field(default_factory=list)
    missing_files: list[MissingFile] = field(default_factory=list)
    duplicate_requests: list[DuplicateRequest] = field(default_factory=list)
    already_exists_files: list[AlreadyExistsFile] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def copied_count(self) -> int:
        return len(self.copied_files)

    @property
    def missing_count(self) -> int:
        return len(self.missing_files)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_requests)

    @property
    def already_exists_count(self) -> int:
        return len(self.already_exists_files)

    def summary(self) -> dict[str, int | float]:
        """Return a compact summary suitable for UI display or tests."""

        return {
            "total_filenames": self.total_filenames,
            "copied": self.copied_count,
            "missing": self.missing_count,
            "duplicate_requests": self.duplicate_count,
            "already_exists": self.already_exists_count,
            "elapsed_seconds": self.elapsed_seconds,
        }
