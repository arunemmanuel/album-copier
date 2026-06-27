"""Main window for the File Copy Utility."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSettings, QSortFilterProxyModel, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from controllers.copy_controller import CopyController
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
    CopyResults,
)
from reports.report_repository import ReportRepository
from services.file_operation_service import CopyOptions


class DropLineEdit(QLineEdit):
    """Line edit that accepts dropped folders or text files."""

    path_dropped = Signal(str)
    rejected_drop = Signal(str)

    def __init__(self, accepts_folder: bool, accepts_text_file: bool) -> None:
        super().__init__()
        self.accepts_folder = accepts_folder
        self.accepts_text_file = accepts_text_file
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt method name.
        if self._path_from_event(event):
            self.setProperty("dropActive", True)
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt method name.
        self.setProperty("dropActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt method name.
        self.setProperty("dropActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        path = self._path_from_event(event)
        if path:
            self.path_dropped.emit(str(path))
            event.acceptProposedAction()
        else:
            self.rejected_drop.emit("Drop a folder or .txt file supported by this field.")
            event.ignore()

    def _path_from_event(self, event) -> Path | None:
        if not event.mimeData().hasUrls():
            return None
        urls = event.mimeData().urls()
        if not urls:
            return None
        path = Path(urls[0].toLocalFile())
        if self.accepts_folder and path.is_dir():
            return path
        if self.accepts_text_file and path.is_file() and path.suffix.lower() == ".txt":
            return path
        return None


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self.logger = logger
        self.controller = CopyController(logger)
        self.report_repository = ReportRepository()
        self.settings = QSettings("FileCopyUtility", "FileCopyUtility")
        self.results = CopyResults()
        self.table_models: dict[str, QStandardItemModel] = {}
        self.proxy_models: dict[str, QSortFilterProxyModel] = {}
        self.tables: dict[str, QTableView] = {}
        self.last_export_folder = Path.cwd()

        self.setWindowTitle("File Copy Utility")
        self.resize(1120, 760)
        self._build_ui()
        self._build_actions()
        self._connect_signals()
        self._restore_settings()
        self._update_start_state()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setSpacing(14)

        input_layout = QFormLayout()
        input_layout.setLabelAlignment(Qt.AlignRight)
        self.source_edit, source_row = self._path_row("Browse")
        self.destination_edit, destination_row = self._path_row("Browse")
        self.filename_edit, filename_row = self._path_row("Browse")
        input_layout.addRow("Source Folder", source_row)
        input_layout.addRow("Destination Folder", destination_row)
        input_layout.addRow("Filename List", filename_row)
        root.addLayout(input_layout)

        self.source_button = source_row.findChild(QPushButton)
        self.destination_button = destination_row.findChild(QPushButton)
        self.filename_button = filename_row.findChild(QPushButton)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("Start Copy")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.resume_button = QPushButton("Resume")
        self.resume_button.setEnabled(False)
        self.clear_button = QPushButton("Clear Results")
        self.retry_button = QPushButton("Retry Failed Files")
        self.retry_button.setEnabled(False)
        self.export_all_button = QPushButton("Export Report")
        self.open_source_button = QPushButton("Open Source Folder")
        self.open_destination_button = QPushButton("Open Destination Folder")
        self.open_log_button = QPushButton("Open Log Folder")
        self.view_log_button = QPushButton("View Log")
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.pause_button)
        action_row.addWidget(self.resume_button)
        action_row.addWidget(self.export_all_button)
        action_row.addWidget(self.clear_button)
        action_row.addWidget(self.retry_button)
        action_row.addStretch()
        root.addLayout(action_row)

        open_row = QHBoxLayout()
        open_row.addWidget(self.open_source_button)
        open_row.addWidget(self.open_destination_button)
        open_row.addWidget(self.open_log_button)
        open_row.addWidget(self.view_log_button)
        open_row.addStretch()
        root.addLayout(open_row)

        option_row = QHBoxLayout()
        self.recursive_checkbox = QCheckBox("Search Subfolders")
        self.verify_checkbox = QCheckBox("Verify copied files")
        self.overwrite_combo = QComboBox()
        self.overwrite_combo.addItems([OVERWRITE_SKIP, OVERWRITE_REPLACE, OVERWRITE_RENAME])
        self.ambiguous_combo = QComboBox()
        self.ambiguous_combo.addItems([AMBIGUOUS_FIRST, AMBIGUOUS_ALL, AMBIGUOUS_SKIP])
        self.fallback_combo = QComboBox()
        self.fallback_combo.addItems([
            FALLBACK_EXACT_ONLY,
            FALLBACK_EXACT_SUFFIX,
            FALLBACK_SUFFIX_ONLY,
        ])
        option_row.addWidget(self.recursive_checkbox)
        option_row.addWidget(QLabel("Overwrite Policy"))
        option_row.addWidget(self.overwrite_combo)
        option_row.addWidget(QLabel("Ambiguous Matches"))
        option_row.addWidget(self.ambiguous_combo)
        option_row.addWidget(QLabel("Fallback Matching"))
        option_row.addWidget(self.fallback_combo)
        option_row.addWidget(self.verify_checkbox)
        option_row.addStretch()
        root.addLayout(option_row)

        progress_grid = QGridLayout()
        self.progress_bar = QProgressBar()
        self.current_file_label = QLabel("Current file: -")
        self.validation_label = QLabel("")
        self.validation_label.setObjectName("validationLabel")
        self.stats_labels = {
            "total_files": QLabel("0"),
            "processed": QLabel("0"),
            "copied": QLabel("0"),
            "missing": QLabel("0"),
            "duplicates": QLabel("0"),
            "already_exists": QLabel("0"),
            "ambiguous": QLabel("0"),
            "verification_passed": QLabel("0"),
            "verification_failed": QLabel("0"),
            "throughput": QLabel("0.00"),
            "eta_seconds": QLabel("0.00"),
        }
        progress_grid.addWidget(QLabel("Progress"), 0, 0)
        progress_grid.addWidget(self.progress_bar, 0, 1, 1, 5)
        progress_grid.addWidget(self.current_file_label, 1, 0, 1, 6)
        progress_grid.addWidget(self.validation_label, 2, 0, 1, 6)

        labels = [
            ("Total files", "total_files"),
            ("Processed", "processed"),
            ("Copied", "copied"),
            ("Missing", "missing"),
            ("Duplicate requests", "duplicates"),
            ("Already exists", "already_exists"),
            ("Ambiguous", "ambiguous"),
            ("Verified", "verification_passed"),
            ("Verification failed", "verification_failed"),
            ("Files/sec", "throughput"),
            ("ETA seconds", "eta_seconds"),
        ]
        for index, (label, key) in enumerate(labels):
            progress_grid.addWidget(QLabel(label), 3 + index // 3, (index % 3) * 2)
            progress_grid.addWidget(self.stats_labels[key], 3 + index // 3, (index % 3) * 2 + 1)
        root.addLayout(progress_grid)

        self.summary_label = QLabel(self._summary_text(self.results))
        self.summary_label.setAlignment(Qt.AlignLeft)
        root.addWidget(self.summary_label)

        self.tabs = QTabWidget()
        self._add_result_tab(
            "copied",
            "Copied Files",
            [
                "Filename",
                "Source Path",
                "Destination Path",
                "Copy Time",
                "Verification",
                "File Size",
                "Overwritten",
                "Previous Timestamp",
                "New Timestamp",
            ],
        )
        self._add_result_tab("missing", "Missing Files", ["Filename"])
        self._add_result_tab(
            "duplicates",
            "Duplicate Requests",
            ["Filename", "Occurrence Count"],
        )
        self._add_result_tab(
            "already_exists",
            "Already Exists",
            ["Filename", "Destination Path"],
        )
        self._add_result_tab(
            "ambiguous",
            "Ambiguous Files",
            ["Filename", "Action", "Matches"],
        )
        self._add_result_tab(
            "verification_failures",
            "Verification Failures",
            ["Filename", "Source Path", "Destination Path"],
        )
        self._add_result_tab(
            "request_results",
            "Match Results",
            [
                "Requested Filename",
                "Matched Filename",
                "Match Type",
                "Source Path",
                "Destination Path",
                "Status",
            ],
        )
        root.addWidget(self.tabs, stretch=1)

        self.setCentralWidget(central)
        self._apply_style()

    def _path_row(self, button_text: str) -> tuple[QLineEdit, QWidget]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = DropLineEdit(False, False)
        button = QPushButton(button_text)
        layout.addWidget(edit, stretch=1)
        layout.addWidget(button)
        return edit, row

    def _build_actions(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        self.start_action = QAction("Start", self)
        self.start_action.setShortcut("Ctrl+Return")
        self.cancel_action = QAction("Cancel", self)
        self.cancel_action.setShortcut("Esc")
        self.export_action = QAction("Export Report", self)
        self.export_action.setShortcut("Ctrl+E")
        self.clear_action = QAction("Clear Results", self)
        self.clear_action.setShortcut("Ctrl+L")

        for action in (
            self.start_action,
            self.cancel_action,
            self.export_action,
            self.clear_action,
        ):
            toolbar.addAction(action)

        theme_menu = self.menuBar().addMenu("Theme")
        self.theme_actions: dict[str, QAction] = {}
        for theme in ("System Default", "Light", "Dark"):
            action = QAction(theme, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, value=theme: self._set_theme(value))
            theme_menu.addAction(action)
            self.theme_actions[theme] = action

        self.statusBar().showMessage("Ready")

    def _add_result_tab(self, key: str, title: str, headers: list[str]) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        search_row = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("Search")
        export_button = QPushButton(f"Export {title}")
        search_row.addWidget(search, stretch=1)
        search_row.addWidget(export_button)
        layout.addLayout(search_row)

        model = QStandardItemModel(0, len(headers), self)
        model.setHorizontalHeaderLabels(headers)
        proxy = QSortFilterProxyModel(self)
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setFilterKeyColumn(-1)

        table = QTableView()
        table.setModel(proxy)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        export_action = QAction("Export This Table", table)
        export_action.triggered.connect(lambda _=False, table_key=key: self._export_table(table_key))
        table.addAction(export_action)
        layout.addWidget(table)

        search.textChanged.connect(proxy.setFilterFixedString)
        export_button.clicked.connect(lambda _=False, table_key=key: self._export_table(table_key))

        self.table_models[key] = model
        self.proxy_models[key] = proxy
        self.tables[key] = table
        self.tabs.addTab(tab, title)

    def _connect_signals(self) -> None:
        self.source_button.clicked.connect(self._browse_source)
        self.destination_button.clicked.connect(self._browse_destination)
        self.filename_button.clicked.connect(self._browse_filename_list)
        self.start_button.clicked.connect(self._start_copy)
        self.start_action.triggered.connect(self._start_copy)
        self.cancel_button.clicked.connect(self.controller.cancel)
        self.cancel_action.triggered.connect(self.controller.cancel)
        self.pause_button.clicked.connect(self._pause_copy)
        self.resume_button.clicked.connect(self._resume_copy)
        self.export_all_button.clicked.connect(self._export_report)
        self.export_action.triggered.connect(self._export_report)
        self.clear_button.clicked.connect(self._clear_results)
        self.clear_action.triggered.connect(self._clear_results)
        self.retry_button.clicked.connect(self._start_copy)
        self.open_source_button.clicked.connect(lambda: self._open_path(Path(self.source_edit.text())))
        self.open_destination_button.clicked.connect(lambda: self._open_path(Path(self.destination_edit.text())))
        self.open_log_button.clicked.connect(lambda: self._open_path(Path("logs")))
        self.view_log_button.clicked.connect(lambda: self._open_path(Path("logs/application.log")))
        self.overwrite_combo.currentTextChanged.connect(self._save_settings)
        self.ambiguous_combo.currentTextChanged.connect(self._save_settings)
        self.fallback_combo.currentTextChanged.connect(self._save_settings)
        self.recursive_checkbox.toggled.connect(self._save_settings)
        self.verify_checkbox.toggled.connect(self._save_settings)
        for edit in (self.source_edit, self.destination_edit, self.filename_edit):
            edit.textChanged.connect(self._update_start_state)
            edit.textChanged.connect(self._save_settings)
            if isinstance(edit, DropLineEdit):
                edit.path_dropped.connect(edit.setText)
                edit.rejected_drop.connect(self._show_drop_rejected)

        self.source_edit.accepts_folder = True
        self.destination_edit.accepts_folder = True
        self.filename_edit.accepts_text_file = True

    def _browse_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.logger.info("Source folder selected: %s", folder)
            self.source_edit.setText(folder)

    def _browse_destination(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.logger.info("Destination folder selected: %s", folder)
            self.destination_edit.setText(folder)

    def _browse_filename_list(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Filename List", "", "Text Files (*.txt)"
        )
        if file_path:
            self.logger.info("Filename list selected: %s", file_path)
            self.filename_edit.setText(file_path)

    def _update_start_state(self) -> None:
        message = self._validation_message()
        self.validation_label.setText(message)
        self.start_button.setEnabled(not message and not self.controller.is_running())
        self.start_action.setEnabled(self.start_button.isEnabled())
        self.retry_button.setEnabled(bool(self.results.missing_files))
        self.open_source_button.setEnabled(Path(self.source_edit.text()).is_dir())
        self.open_destination_button.setEnabled(Path(self.destination_edit.text()).is_dir())
        self.open_log_button.setEnabled(Path("logs").is_dir())
        self.view_log_button.setEnabled(Path("logs/application.log").is_file())

    def _validation_message(self) -> str:
        source = Path(self.source_edit.text()).expanduser()
        destination = Path(self.destination_edit.text()).expanduser()
        filename_list = Path(self.filename_edit.text()).expanduser()

        if not self.source_edit.text().strip():
            return "Select a source folder."
        if not source.is_dir():
            return "Source folder is invalid."
        if not self.destination_edit.text().strip():
            return "Select a destination folder."
        if not destination.is_dir():
            return "Destination folder is invalid."
        if not self.filename_edit.text().strip():
            return "Select a .txt filename list."
        if filename_list.suffix.lower() != ".txt" or not filename_list.is_file():
            return "Filename list must be an existing .txt file."
        return ""

    def _start_copy(self) -> None:
        message = self._validation_message()
        if message:
            QMessageBox.warning(self, "Validation", message)
            return

        self._set_running_state(True)
        self._clear_tables()
        self.results = CopyResults()
        self.summary_label.setText(self._summary_text(self.results))
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Copying...")

        if self.overwrite_combo.currentText() == OVERWRITE_REPLACE:
            confirmed = QMessageBox.question(
                self,
                "Confirm Overwrite",
                "Overwrite Existing will replace files in the destination folder. Continue?",
            )
            if confirmed != QMessageBox.Yes:
                self._set_running_state(False)
                return

        self.controller.start(
            Path(self.source_edit.text()).expanduser(),
            Path(self.destination_edit.text()).expanduser(),
            Path(self.filename_edit.text()).expanduser(),
            CopyOptions(
                recursive_search=self.recursive_checkbox.isChecked(),
                overwrite_policy=self.overwrite_combo.currentText(),
                ambiguous_policy=self.ambiguous_combo.currentText(),
                verify_copies=self.verify_checkbox.isChecked(),
                fallback_mode=self.fallback_combo.currentText(),
            ),
            self._on_progress,
            self._on_finished,
            self._on_failed,
            self._on_canceled,
        )

    def _on_progress(self, progress: dict) -> None:
        total_unique = max(progress["total_unique"], 1)
        self.progress_bar.setValue(int(progress["processed"] / total_unique * 100))
        self.current_file_label.setText(f"Current file: {progress['current_filename']}")
        for key, label in self.stats_labels.items():
            value = progress[key]
            label.setText(f"{value:.2f}" if isinstance(value, float) else str(value))
        self.statusBar().showMessage(
            f"{progress['processed']} processed | {progress['throughput']:.2f} files/sec"
        )

    def _on_finished(self, results: CopyResults) -> None:
        self.results = results
        self._populate_tables(results)
        self.summary_label.setText(self._summary_text(results))
        self.progress_bar.setValue(100)
        self.current_file_label.setText("Current file: -")
        self._set_running_state(False)
        self._save_settings()
        self.statusBar().showMessage("Copy complete")
        QMessageBox.information(self, "Copy Complete", "File copy operation completed.")

    def _on_canceled(self, results: CopyResults) -> None:
        self.results = results
        self._populate_tables(results)
        self.summary_label.setText(self._summary_text(results))
        self._set_running_state(False)
        self.statusBar().showMessage("Copy canceled")
        QMessageBox.information(self, "Copy Canceled", "File copy operation was canceled.")

    def _on_failed(self, message: str) -> None:
        self._set_running_state(False)
        self.statusBar().showMessage("Copy failed")
        QMessageBox.critical(
            self,
            "Copy Failed",
            f"The copy operation could not finish.\n\n{message}\n\nSee logs/application.log.",
        )

    def _set_running_state(self, running: bool) -> None:
        self.start_button.setEnabled(not running and not self._validation_message())
        self.cancel_button.setEnabled(running)
        self.pause_button.setEnabled(running)
        self.resume_button.setEnabled(False)
        self.cancel_action.setEnabled(running)
        for widget in (
            self.source_edit,
            self.destination_edit,
            self.filename_edit,
            self.source_button,
            self.destination_button,
            self.filename_button,
            self.recursive_checkbox,
            self.verify_checkbox,
            self.overwrite_combo,
            self.ambiguous_combo,
            self.fallback_combo,
        ):
            widget.setEnabled(not running)

    def _pause_copy(self) -> None:
        self.controller.pause()
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.statusBar().showMessage("Paused")

    def _resume_copy(self) -> None:
        self.controller.resume()
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.statusBar().showMessage("Copying...")

    def _clear_tables(self) -> None:
        for model in self.table_models.values():
            model.removeRows(0, model.rowCount())

    def _populate_tables(self, results: CopyResults) -> None:
        self._clear_tables()
        for copied in results.copied_files:
            self._append_row(
                "copied",
                [
                    copied.filename,
                    str(copied.source_path),
                    str(copied.destination_path),
                    copied.copy_time.strftime("%Y-%m-%d %H:%M:%S"),
                    copied.verification_status,
                    str(copied.file_size),
                    str(copied.overwritten),
                    copied.previous_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if copied.previous_timestamp
                    else "",
                    copied.new_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if copied.new_timestamp
                    else "",
                ],
            )
        for missing in results.missing_files:
            self._append_row("missing", [missing.filename])
        for duplicate in results.duplicate_requests:
            self._append_row(
                "duplicates", [duplicate.filename, str(duplicate.occurrence_count)]
            )
        for existing in results.already_exists_files:
            self._append_row(
                "already_exists", [existing.filename, str(existing.destination_path)]
            )
        for ambiguous in results.ambiguous_files:
            self._append_row(
                "ambiguous",
                [
                    ambiguous.filename,
                    ambiguous.action,
                    "\n".join(str(path) for path in ambiguous.matches),
                ],
            )
        for failure in results.verification_failures:
            self._append_row(
                "verification_failures",
                [
                    failure.filename,
                    str(failure.source_path),
                    str(failure.destination_path),
                ],
            )
        for item in results.request_results:
            self._append_row(
                "request_results",
                [
                    item.requested_filename,
                    item.matched_filename,
                    item.match_type,
                    str(item.source_path) if item.source_path else "",
                    str(item.destination_path) if item.destination_path else "",
                    item.status,
                ],
            )

    def _append_row(self, key: str, values: list[str]) -> None:
        items = [QStandardItem(value) for value in values]
        for item in items:
            item.setEditable(False)
        self.table_models[key].appendRow(items)

    def _summary_text(self, results: CopyResults) -> str:
        return (
            "Total filenames: {total}    Copied: {copied}    Missing: {missing}    "
            "Duplicate Requests: {duplicates}    Already Exists: {exists}    "
            "Ambiguous: {ambiguous}    Exact Matches: {exact}    "
            "Last 4 Matches: {suffix}    Multiple Matches: {multiple}    "
            "Verified: {verified}    Verification Failed: {failed}    Elapsed Time: {elapsed:.2f}s"
        ).format(
            total=results.total_filenames,
            copied=results.copied_count,
            missing=results.missing_count,
            duplicates=results.duplicate_count,
            exists=results.already_exists_count,
            ambiguous=results.ambiguous_count,
            exact=results.exact_match_count,
            suffix=results.suffix_match_count,
            multiple=results.multiple_match_count,
            verified=results.verification_passed_count,
            failed=results.verification_failed_count,
            elapsed=results.elapsed_seconds,
        )

    def _export_table(self, key: str) -> None:
        default_name = f"{key}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default_name, "CSV Files (*.csv)"
        )
        if not file_path:
            return
        self._write_table_csv(key, Path(file_path))
        self.last_export_folder = Path(file_path).parent
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported {file_path}")

    def _export_report(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Export Folder", str(self.last_export_folder)
        )
        if not folder:
            return
        export_folder = Path(folder)
        try:
            self.report_repository.export_csv_bundle(self.results, export_folder)
            self.report_repository.export_html(self.results, export_folder / "report.html")
            self.report_repository.export_pdf(self.results, export_folder / "report.pdf")
            self.last_export_folder = export_folder
            self._save_settings()
            self.logger.info("Exported report bundle: %s", export_folder)
            QMessageBox.information(self, "Export Complete", f"Exported reports to {folder}")
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Report export failed")
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _write_table_csv(self, key: str, file_path: Path) -> None:
        model = self.table_models[key]
        try:
            with file_path.open("w", newline="", encoding="utf-8") as csv_file:
                import csv

                writer = csv.writer(csv_file)
                headers = [
                    model.headerData(col, Qt.Horizontal)
                    for col in range(model.columnCount())
                ]
                writer.writerow(headers)
                for row in range(model.rowCount()):
                    writer.writerow(
                        [
                            model.item(row, col).text() if model.item(row, col) else ""
                            for col in range(model.columnCount())
                        ]
                    )
            self.logger.info("Exported CSV: %s", file_path)
        except Exception as exc:  # noqa: BLE001 - friendly UI plus log traceback.
            self.logger.exception("CSV export failed")
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _clear_results(self) -> None:
        self.results = CopyResults()
        self._clear_tables()
        self.summary_label.setText(self._summary_text(self.results))
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Results cleared")
        self._update_start_state()

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "Open Folder", f"{path} does not exist.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def _show_drop_rejected(self, message: str) -> None:
        QMessageBox.warning(self, "Unsupported Drop", message)

    def _set_theme(self, theme: str) -> None:
        for name, action in self.theme_actions.items():
            action.setChecked(name == theme)
        self.settings.setValue("theme", theme)
        self._apply_style(theme)

    def _restore_settings(self) -> None:
        self.source_edit.setText(self.settings.value("source_folder", "", str))
        self.destination_edit.setText(self.settings.value("destination_folder", "", str))
        self.filename_edit.setText(self.settings.value("filename_list", "", str))
        self.last_export_folder = Path(self.settings.value("last_export_folder", str(Path.cwd()), str))
        self.recursive_checkbox.setChecked(self.settings.value("recursive_search", False, bool))
        self.verify_checkbox.setChecked(self.settings.value("verify_copies", False, bool))
        self.overwrite_combo.setCurrentText(self.settings.value("overwrite_policy", OVERWRITE_SKIP, str))
        self.ambiguous_combo.setCurrentText(self.settings.value("ambiguous_policy", AMBIGUOUS_FIRST, str))
        self.fallback_combo.setCurrentText(self.settings.value("fallback_mode", FALLBACK_EXACT_SUFFIX, str))
        self.resize(self.settings.value("window_size", self.size()))
        position = self.settings.value("window_position")
        if position:
            self.move(position)
        self._set_theme(self.settings.value("theme", "System Default", str))

    def _save_settings(self) -> None:
        self.settings.setValue("source_folder", self.source_edit.text())
        self.settings.setValue("destination_folder", self.destination_edit.text())
        self.settings.setValue("filename_list", self.filename_edit.text())
        self.settings.setValue("last_export_folder", str(self.last_export_folder))
        self.settings.setValue("recursive_search", self.recursive_checkbox.isChecked())
        self.settings.setValue("verify_copies", self.verify_checkbox.isChecked())
        self.settings.setValue("overwrite_policy", self.overwrite_combo.currentText())
        self.settings.setValue("ambiguous_policy", self.ambiguous_combo.currentText())
        self.settings.setValue("fallback_mode", self.fallback_combo.currentText())

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt method name.
        self.settings.setValue("window_size", self.size())
        self.settings.setValue("window_position", self.pos())
        self._save_settings()
        self.logger.info("Application shutdown")
        super().closeEvent(event)

    def _apply_style(self, theme: str = "System Default") -> None:
        dark = theme == "Dark"
        if theme == "System Default":
            self.setStyleSheet("")
            return
        palette = {
            "bg": "#172026" if dark else "#ffffff",
            "panel": "#202b33" if dark else "#f7f8fa",
            "text": "#edf2f7" if dark else "#1f2933",
            "border": "#51606c" if dark else "#c8cdd2",
            "hover": "#2b3944" if dark else "#eceff3",
            "accent": "#52b6a3" if dark else "#2f7d6d",
            "error": "#ffb4a8" if dark else "#a33a2f",
        }
        self.setStyleSheet(
            f"""
            QWidget {{
                font-size: 13px;
                background: {palette["bg"]};
                color: {palette["text"]};
            }}
            QLineEdit {{
                padding: 7px 9px;
                border: 1px solid {palette["border"]};
                border-radius: 4px;
                background: {palette["panel"]};
                color: {palette["text"]};
            }}
            QLineEdit[dropActive="true"] {{
                border: 2px solid {palette["accent"]};
            }}
            QPushButton {{
                padding: 8px 14px;
                border: 1px solid {palette["border"]};
                border-radius: 4px;
                background: {palette["panel"]};
                color: {palette["text"]};
            }}
            QPushButton:hover {{
                background: {palette["hover"]};
            }}
            QPushButton:disabled {{
                color: #8a9098;
                background: {palette["panel"]};
            }}
            QProgressBar {{
                min-height: 18px;
                border: 1px solid {palette["border"]};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {palette["accent"]};
            }}
            QLabel#validationLabel {{
                color: {palette["error"]};
            }}
            QTableView {{
                border: 1px solid {palette["border"]};
                gridline-color: #e5e8eb;
                selection-background-color: #d9ebe7;
            }}
            """
        )
