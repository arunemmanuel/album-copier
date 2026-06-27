"""Service layer for file search, copy, overwrite, and verification logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from models.result_model import (
    AMBIGUOUS_ALL,
    AMBIGUOUS_FIRST,
    AMBIGUOUS_SKIP,
    OVERWRITE_RENAME,
    OVERWRITE_REPLACE,
    OVERWRITE_SKIP,
    AmbiguousFile,
    AlreadyExistsFile,
    CopiedFile,
    MissingFile,
    VerificationFailure,
)
from utils.checksum import checksums_match
from utils.file_utils import copy_file_to_path, find_source_matches, next_available_path


@dataclass(frozen=True)
class CopyOptions:
    """Options that control search and copy behavior."""

    recursive_search: bool = False
    overwrite_policy: str = OVERWRITE_SKIP
    ambiguous_policy: str = AMBIGUOUS_FIRST
    verify_copies: bool = False


@dataclass(frozen=True)
class CopyDecision:
    """Result of processing a single source file."""

    copied: CopiedFile | None = None
    already_exists: AlreadyExistsFile | None = None
    verification_failure: VerificationFailure | None = None


class FileOperationService:
    """Perform file operations without depending on the GUI."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def source_matches(
        self, source_folder: Path, filename: str, recursive: bool
    ) -> list[Path]:
        """Return source matches for a filename."""

        return find_source_matches(source_folder, filename, recursive)

    def resolve_matches(
        self,
        filename: str,
        matches: list[Path],
        ambiguous_policy: str,
    ) -> tuple[list[Path], AmbiguousFile | MissingFile | None]:
        """Resolve missing or ambiguous source matches."""

        if not matches:
            return [], MissingFile(filename)
        if len(matches) == 1:
            return matches, None

        ambiguous = AmbiguousFile(filename, matches, ambiguous_policy)
        if ambiguous_policy == AMBIGUOUS_SKIP:
            return [], ambiguous
        if ambiguous_policy == AMBIGUOUS_ALL:
            return matches, ambiguous
        return [matches[0]], ambiguous

    def copy_one(
        self,
        source_path: Path,
        destination_folder: Path,
        options: CopyOptions,
    ) -> CopyDecision:
        """Copy one source file according to overwrite and verification options."""

        destination_path = destination_folder / source_path.name
        previous_timestamp = None
        overwritten = False

        if destination_path.exists():
            if options.overwrite_policy == OVERWRITE_SKIP:
                return CopyDecision(
                    already_exists=AlreadyExistsFile(source_path.name, destination_path)
                )
            if options.overwrite_policy == OVERWRITE_RENAME:
                destination_path = next_available_path(destination_path)
            elif options.overwrite_policy == OVERWRITE_REPLACE:
                previous_timestamp = datetime.fromtimestamp(destination_path.stat().st_mtime)
                overwritten = True

        copied_to = copy_file_to_path(source_path, destination_path)
        new_timestamp = datetime.fromtimestamp(copied_to.stat().st_mtime)
        file_size = copied_to.stat().st_size
        verification_status = "Not Verified"
        source_checksum = ""
        destination_checksum = ""
        verification_failure = None

        if options.verify_copies:
            matched, source_checksum, destination_checksum = checksums_match(
                source_path, copied_to
            )
            verification_status = "Verified" if matched else "Verification Failed"
            self.logger.info(
                "Checksum verification %s: %s -> %s",
                verification_status,
                source_path,
                copied_to,
            )
            if not matched:
                verification_failure = VerificationFailure(
                    source_path.name,
                    source_path,
                    copied_to,
                    source_checksum,
                    destination_checksum,
                )

        copied = CopiedFile(
            filename=source_path.name,
            source_path=source_path,
            destination_path=copied_to,
            copy_time=datetime.now(),
            verification_status=verification_status,
            source_checksum=source_checksum,
            destination_checksum=destination_checksum,
            file_size=file_size,
            overwritten=overwritten,
            previous_timestamp=previous_timestamp,
            new_timestamp=new_timestamp,
        )
        return CopyDecision(copied=copied, verification_failure=verification_failure)
