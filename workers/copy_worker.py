"""QThread worker for long-running copy operations."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from traceback import format_exc

from PySide6.QtCore import QObject, Signal, Slot

from models.result_model import (
    AmbiguousFile,
    CopyResults,
    DuplicateRequest,
    MissingFile,
)
from services.file_operation_service import CopyOptions, FileOperationService
from utils.file_utils import (
    duplicate_counts,
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
        options: CopyOptions,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.source_folder = source_folder
        self.destination_folder = destination_folder
        self.filename_list_path = filename_list_path
        self.options = options
        self.logger = logger
        self.service = FileOperationService(logger)
        self._cancel_requested = False
        self._paused = False
        self._start_perf = 0.0

    @Slot()
    def run(self) -> None:
        """Run the copy operation and emit progress/results."""

        start = time.perf_counter()
        self._start_perf = start
        results = CopyResults()

        try:
            self.logger.info("Copy start")
            filenames = read_filename_list(self.filename_list_path)
            duplicate_map = duplicate_counts(filenames)
            unique_filenames = unique_filenames_in_order(filenames)
            results.total_filenames = len(filenames)
            results.source_folder = self.source_folder
            results.destination_folder = self.destination_folder
            results.recursive_search = self.options.recursive_search
            results.overwrite_policy = self.options.overwrite_policy
            results.verify_copies = self.options.verify_copies

            for filename, count in duplicate_map.items():
                results.duplicate_requests.append(DuplicateRequest(filename, count))
                self.logger.info("Duplicate request: %s (%s)", filename, count)

            total_unique = len(unique_filenames)
            for processed, filename in enumerate(unique_filenames, start=1):
                while self._paused and not self._cancel_requested:
                    time.sleep(0.1)

                if self._cancel_requested:
                    results.elapsed_seconds = time.perf_counter() - start
                    self.logger.info("Copy canceled")
                    self.canceled.emit(results)
                    return

                self._emit_progress(results, processed - 1, total_unique, filename)
                matches = self.service.source_matches(
                    self.source_folder, filename, self.options.recursive_search
                )
                resolved, issue = self.service.resolve_matches(
                    filename, matches, self.options.ambiguous_policy
                )
                if isinstance(issue, MissingFile):
                    results.missing_files.append(issue)
                    self.logger.info("Missing file: %s", filename)
                    self._emit_progress(results, processed, total_unique, filename)
                    continue
                if isinstance(issue, AmbiguousFile):
                    results.ambiguous_files.append(issue)
                    self.logger.info("Ambiguous file: %s (%s matches)", filename, len(matches))
                    if not resolved:
                        self._emit_progress(results, processed, total_unique, filename)
                        continue

                for source_path in resolved:
                    decision = self.service.copy_one(
                        source_path, self.destination_folder, self.options
                    )
                    if decision.already_exists:
                        results.already_exists_files.append(decision.already_exists)
                        self.logger.info(
                            "Already exists: %s",
                            decision.already_exists.destination_path,
                        )
                        continue
                    if decision.copied:
                        results.copied_files.append(decision.copied)
                        self.logger.info(
                            "Copied file: %s -> %s",
                            decision.copied.source_path,
                            decision.copied.destination_path,
                        )
                    if decision.verification_failure:
                        results.verification_failures.append(
                            decision.verification_failure
                        )
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

    @Slot()
    def pause(self) -> None:
        """Pause copying after the current file completes."""

        self._paused = True

    @Slot()
    def resume(self) -> None:
        """Resume a paused copy operation."""

        self._paused = False

    def _emit_progress(
        self,
        results: CopyResults,
        processed: int,
        total_unique: int,
        current_filename: str,
    ) -> None:
        elapsed = max(time.perf_counter() - self._start_perf, 0.001)
        completed = (
            results.copied_count
            + results.missing_count
            + results.already_exists_count
            + results.ambiguous_count
        )
        throughput = completed / elapsed
        remaining = max(total_unique - processed, 0)
        eta_seconds = remaining / throughput if throughput > 0 else 0.0
        self.progress_changed.emit(
            {
                "total_files": results.total_filenames,
                "processed": processed,
                "total_unique": total_unique,
                "copied": results.copied_count,
                "missing": results.missing_count,
                "duplicates": results.duplicate_count,
                "already_exists": results.already_exists_count,
                "ambiguous": results.ambiguous_count,
                "verification_passed": results.verification_passed_count,
                "verification_failed": results.verification_failed_count,
                "throughput": throughput,
                "eta_seconds": eta_seconds,
                "average_speed": throughput,
                "current_filename": current_filename,
            }
        )
