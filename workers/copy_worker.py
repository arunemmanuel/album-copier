"""QThread worker for long-running copy operations."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from traceback import format_exc

from PySide6.QtCore import QObject, Signal, Slot

from models.result_model import (
    AlreadyExistsFile,
    CopiedFile,
    CopyResults,
    DuplicateRequest,
    MissingFile,
)
from utils.file_utils import (
    copy_file,
    duplicate_counts,
    find_source_file,
    read_filename_list,
    unique_filenames_in_order,
)


class CopyWorker(QObject):
    """Perform a copy operation without blocking the GUI thread."""

    progress_changed = Signal(dict)
    finished = Signal(object)
    failed = Signal(str)
    canceled = Signal(object)

    def __init__(
        self,
        source_folder: Path,
        destination_folder: Path,
        filename_list_path: Path,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.source_folder = source_folder
        self.destination_folder = destination_folder
        self.filename_list_path = filename_list_path
        self.logger = logger
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        """Run the copy operation and emit progress/results."""

        start = time.perf_counter()
        results = CopyResults()

        try:
            self.logger.info("Copy start")
            filenames = read_filename_list(self.filename_list_path)
            duplicate_map = duplicate_counts(filenames)
            unique_filenames = unique_filenames_in_order(filenames)
            results.total_filenames = len(filenames)

            for filename, count in duplicate_map.items():
                results.duplicate_requests.append(DuplicateRequest(filename, count))
                self.logger.info("Duplicate request: %s (%s)", filename, count)

            total_unique = len(unique_filenames)
            for processed, filename in enumerate(unique_filenames, start=1):
                if self._cancel_requested:
                    results.elapsed_seconds = time.perf_counter() - start
                    self.logger.info("Copy canceled")
                    self.canceled.emit(results)
                    return

                self._emit_progress(results, processed - 1, total_unique, filename)
                destination_path = self.destination_folder / filename

                if destination_path.exists():
                    results.already_exists_files.append(
                        AlreadyExistsFile(filename, destination_path)
                    )
                    self.logger.info("Already exists: %s", destination_path)
                    self._emit_progress(results, processed, total_unique, filename)
                    continue

                source_path = find_source_file(self.source_folder, filename)
                if source_path is None:
                    results.missing_files.append(MissingFile(filename))
                    self.logger.info("Missing file: %s", filename)
                    self._emit_progress(results, processed, total_unique, filename)
                    continue

                copied_to = copy_file(source_path, self.destination_folder)
                copied = CopiedFile(filename, source_path, copied_to, datetime.now())
                results.copied_files.append(copied)
                self.logger.info("Copied file: %s -> %s", source_path, copied_to)
                self._emit_progress(results, processed, total_unique, filename)

            results.elapsed_seconds = time.perf_counter() - start
            self.logger.info("Completion summary: %s", results.summary())
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001 - logged with traceback for UI display.
            self.logger.error("Copy failed: %s\n%s", exc, format_exc())
            self.failed.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        """Request cancellation at the next safe point."""

        self._cancel_requested = True

    def _emit_progress(
        self,
        results: CopyResults,
        processed: int,
        total_unique: int,
        current_filename: str,
    ) -> None:
        self.progress_changed.emit(
            {
                "total_files": results.total_filenames,
                "processed": processed,
                "total_unique": total_unique,
                "copied": results.copied_count,
                "missing": results.missing_count,
                "duplicates": results.duplicate_count,
                "already_exists": results.already_exists_count,
                "current_filename": current_filename,
            }
        )
