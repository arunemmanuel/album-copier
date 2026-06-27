"""Controller for coordinating copy worker threads."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread

from services.file_operation_service import CopyOptions
from workers.copy_worker import CopyWorker


class CopyController:
    """Create and manage the lifetime of the copy worker thread."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.thread: QThread | None = None
        self.worker: CopyWorker | None = None

    def start(
        self,
        source_folder: Path,
        destination_folder: Path,
        filename_list_path: Path,
        options: CopyOptions,
        on_progress,
        on_finished,
        on_failed,
        on_canceled,
    ) -> None:
        """Start a copy operation."""

        self.thread = QThread()
        self.worker = CopyWorker(
            source_folder, destination_folder, filename_list_path, options, self.logger
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(on_progress)
        self.worker.finished.connect(on_finished)
        self.worker.failed.connect(on_failed)
        self.worker.canceled.connect(on_canceled)

        for signal in (
            self.worker.finished,
            self.worker.failed,
            self.worker.canceled,
        ):
            signal.connect(self.thread.quit)
            signal.connect(self.worker.deleteLater)

        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_worker)
        self.thread.start()

    def cancel(self) -> None:
        """Request cancellation of the active copy operation."""

        if self.worker is not None:
            self.worker.cancel()

    def pause(self) -> None:
        """Pause the active copy operation."""

        if self.worker is not None:
            self.worker.pause()

    def resume(self) -> None:
        """Resume the active copy operation."""

        if self.worker is not None:
            self.worker.resume()

    def is_running(self) -> bool:
        """Return whether the worker thread is active."""

        return self.thread is not None and self.thread.isRunning()

    def _clear_worker(self) -> None:
        self.thread = None
        self.worker = None
