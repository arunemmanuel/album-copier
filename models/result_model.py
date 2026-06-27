"""Dataclasses and summary helpers for file copy results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


OVERWRITE_SKIP = "Skip Existing"
OVERWRITE_REPLACE = "Overwrite Existing"
OVERWRITE_RENAME = "Rename New File"

AMBIGUOUS_FIRST = "Copy first match only"
AMBIGUOUS_ALL = "Copy all matches"
AMBIGUOUS_SKIP = "Skip ambiguous files"


@dataclass(frozen=True)
class CopiedFile:
    """Information about a successfully copied file."""

    filename: str
    source_path: Path
    destination_path: Path
    copy_time: datetime
    verification_status: str = "Not Verified"
    source_checksum: str = ""
    destination_checksum: str = ""
    file_size: int = 0
    overwritten: bool = False
    previous_timestamp: datetime | None = None
    new_timestamp: datetime | None = None


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


@dataclass(frozen=True)
class AmbiguousFile:
    """Information about a filename found in multiple source locations."""

    filename: str
    matches: list[Path]
    action: str


@dataclass(frozen=True)
class VerificationFailure:
    """Information about a copied file that failed checksum verification."""

    filename: str
    source_path: Path
    destination_path: Path
    source_checksum: str
    destination_checksum: str


@dataclass
class CopyResults:
    """Aggregated results for a copy operation."""

    total_filenames: int = 0
    copied_files: list[CopiedFile] = field(default_factory=list)
    missing_files: list[MissingFile] = field(default_factory=list)
    duplicate_requests: list[DuplicateRequest] = field(default_factory=list)
    already_exists_files: list[AlreadyExistsFile] = field(default_factory=list)
    ambiguous_files: list[AmbiguousFile] = field(default_factory=list)
    verification_failures: list[VerificationFailure] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    source_folder: Path | None = None
    destination_folder: Path | None = None
    recursive_search: bool = False
    overwrite_policy: str = OVERWRITE_SKIP
    verify_copies: bool = False

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

    @property
    def ambiguous_count(self) -> int:
        return len(self.ambiguous_files)

    @property
    def verification_passed_count(self) -> int:
        return sum(
            1
            for copied in self.copied_files
            if copied.verification_status == "Verified"
        )

    @property
    def verification_failed_count(self) -> int:
        return len(self.verification_failures)

    def summary(self) -> dict[str, int | float]:
        """Return a compact summary suitable for UI display or tests."""

        return {
            "total_filenames": self.total_filenames,
            "copied": self.copied_count,
            "missing": self.missing_count,
            "duplicate_requests": self.duplicate_count,
            "already_exists": self.already_exists_count,
            "ambiguous": self.ambiguous_count,
            "verification_passed": self.verification_passed_count,
            "verification_failed": self.verification_failed_count,
            "elapsed_seconds": self.elapsed_seconds,
        }
