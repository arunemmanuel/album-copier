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
    FALLBACK_EXACT_ONLY,
    FALLBACK_EXACT_SUFFIX,
    FALLBACK_SUFFIX_ONLY,
    OVERWRITE_RENAME,
    OVERWRITE_REPLACE,
    OVERWRITE_SKIP,
    AmbiguousFile,
    AlreadyExistsFile,
    CopiedFile,
    MissingFile,
    RequestResult,
    VerificationFailure,
)
from utils.checksum import checksums_match
from utils.file_utils import (
    copy_file_to_path,
    find_source_matches,
    next_available_path,
)


@dataclass(frozen=True)
class CopyOptions:
    """Options that control search and copy behavior."""

    recursive_search: bool = False
    overwrite_policy: str = OVERWRITE_SKIP
    ambiguous_policy: str = AMBIGUOUS_FIRST
    verify_copies: bool = False
    fallback_mode: str = FALLBACK_EXACT_SUFFIX


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
        self._source_index: dict[tuple[str, str], list[Path]] = {}
        self._exact_index: dict[str, list[Path]] = {}

    def index_source_folder(self, source_folder: Path, recursive: bool) -> None:
        """Build in-memory indexes keyed by exact filename and suffix."""

        self._source_index = {}
        self._exact_index = {}
        files = (
            sorted(path for path in source_folder.rglob("*") if path.is_file())
            if recursive
            else sorted(path for path in source_folder.iterdir() if path.is_file())
        )
        for path in files:
            normalized_name = path.name.strip().lower()
            self._exact_index.setdefault(normalized_name, []).append(path)
            suffix_key = self._suffix_key(path)
            if suffix_key:
                self._source_index.setdefault(suffix_key, []).append(path)

    def source_matches(
        self, source_folder: Path, filename: str, recursive: bool
    ) -> list[Path]:
        """Return source matches for a filename."""

        return find_source_matches(source_folder, filename, recursive)

    def resolve_source_match(
        self,
        source_folder: Path,
        filename: str,
        recursive: bool,
        fallback_mode: str,
        ambiguous_policy: str,
    ) -> tuple[list[Path], MissingFile | None, str, str]:
        """Resolve a requested filename using exact and suffix fallback rules."""

        cleaned_filename = filename.strip()
        exact_matches = self._exact_matches(source_folder, cleaned_filename, recursive)
        if exact_matches:
            self.logger.info("Requested: %s", cleaned_filename)
            self.logger.info("Exact Match: Found")
            return exact_matches, None, "Exact Match", ""

        if fallback_mode == FALLBACK_EXACT_ONLY:
            missing = MissingFile(cleaned_filename, searched_suffix=self._suffix_for_filename(cleaned_filename))
            self.logger.info("Requested: %s", cleaned_filename)
            self.logger.info("Exact Match: Not Found")
            self.logger.info("Searching using suffix: %s", missing.searched_suffix)
            return [], missing, "Missing", missing.searched_suffix

        suffix = self._suffix_for_filename(cleaned_filename)
        self.logger.info("Requested: %s", cleaned_filename)
        self.logger.info("Exact Match: Not Found")
        self.logger.info("Searching using suffix: %s", suffix)
        if not suffix:
            missing = MissingFile(cleaned_filename, searched_suffix=suffix)
            return [], missing, "Missing", suffix

        if fallback_mode == FALLBACK_SUFFIX_ONLY:
            suffix_matches = self._suffix_matches(source_folder, cleaned_filename, recursive)
            if not suffix_matches:
                missing = MissingFile(cleaned_filename, searched_suffix=suffix)
                return [], missing, "Missing", suffix
            if len(suffix_matches) == 1:
                return suffix_matches, None, "Last 4 Characters Match", suffix
            return suffix_matches, None, "Multiple Suffix Matches", suffix

        suffix_matches = self._suffix_matches(source_folder, cleaned_filename, recursive)
        if not suffix_matches:
            missing = MissingFile(cleaned_filename, searched_suffix=suffix)
            return [], missing, "Missing", suffix
        if len(suffix_matches) == 1:
            return suffix_matches, None, "Last 4 Characters Match", suffix
        return suffix_matches, None, "Multiple Suffix Matches", suffix

    def _exact_matches(self, source_folder: Path, filename: str, recursive: bool) -> list[Path]:
        if not filename:
            return []

        cleaned = filename.strip().lower()
        if self._exact_index:
            return list(self._exact_index.get(cleaned, []))
        return find_source_matches(source_folder, filename, recursive)

    def _suffix_matches(self, source_folder: Path, filename: str, recursive: bool) -> list[Path]:
        if not filename:
            return []
        suffix = self._suffix_for_filename(filename)
        if not suffix:
            return []
        if self._source_index:
            return list(
                self._source_index.get(
                    self._suffix_key(Path(filename.strip())),
                    [],
                )
            )
        return self._scan_suffix_matches(source_folder, filename, recursive)

    def _scan_suffix_matches(self, source_folder: Path, filename: str, recursive: bool) -> list[Path]:
        suffix = self._suffix_for_filename(filename)
        if not suffix:
            return []
        extension = self._extension_for_filename(filename)
        pattern = f"*{suffix}{extension}"
        if recursive:
            return sorted(
                path
                for path in source_folder.rglob(pattern)
                if path.is_file() and path.name.lower().endswith(f"{suffix}{extension}".lower())
            )
        return sorted(
            path
            for path in source_folder.glob(pattern)
            if path.is_file() and path.name.lower().endswith(f"{suffix}{extension}".lower())
        )

    def _suffix_key(self, path: Path) -> tuple[str, str] | None:
        if not path.name:
            return None
        name = path.name.strip().lower()
        stem = Path(name).stem
        if not stem:
            return None
        suffix = stem[-4:] if len(stem) >= 4 else stem
        return suffix, Path(name).suffix.lower()

    def _suffix_for_filename(self, filename: str) -> str:
        stem = Path(filename.strip()).stem
        if not stem:
            return ""
        stem = stem.strip().lower()
        if len(stem) < 4:
            return stem
        return stem[-4:]

    def _extension_for_filename(self, filename: str) -> str:
        path = Path(filename.strip())
        return path.suffix.lower()

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
