"""Main window for the File Copy Utility."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
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
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QSortFilterProxyModel

from controllers.copy_controller import CopyController
from models.result_model import CopyResults


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self.logger = logger
        self.controller = CopyController(logger)
        self.results = CopyResults()
        self.table_models: dict[str, QStandardItemModel] = {}
        self.proxy_models: dict[str, QSortFilterProxyModel] = {}
        self.tables: dict[str, QTableView] = {}

        self.setWindowTitle("File Copy Utility")
        self.resize(1120, 760)
        self._build_ui()
        self._connect_signals()
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
        self.export_all_button = QPushButton("Export All")
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.export_all_button)
        action_row.addStretch()
        root.addLayout(action_row)

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
            ["Filename", "Source Path", "Destination Path", "Copy Time"],
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
        root.addWidget(self.tabs, stretch=1)

        self.setCentralWidget(central)
        self._apply_style()

    def _path_row(self, button_text: str) -> tuple[QLineEdit, QWidget]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit()
        button = QPushButton(button_text)
        layout.addWidget(edit, stretch=1)
        layout.addWidget(button)
        return edit, row

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
        self.cancel_button.clicked.connect(self.controller.cancel)
        self.export_all_button.clicked.connect(self._export_all)
        for edit in (self.source_edit, self.destination_edit, self.filename_edit):
            edit.textChanged.connect(self._update_start_state)

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

        self.controller.start(
            Path(self.source_edit.text()).expanduser(),
            Path(self.destination_edit.text()).expanduser(),
            Path(self.filename_edit.text()).expanduser(),
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
            label.setText(str(progress[key]))

    def _on_finished(self, results: CopyResults) -> None:
        self.results = results
        self._populate_tables(results)
        self.summary_label.setText(self._summary_text(results))
        self.progress_bar.setValue(100)
        self.current_file_label.setText("Current file: -")
        self._set_running_state(False)
        QMessageBox.information(self, "Copy Complete", "File copy operation completed.")

    def _on_canceled(self, results: CopyResults) -> None:
        self.results = results
        self._populate_tables(results)
        self.summary_label.setText(self._summary_text(results))
        self._set_running_state(False)
        QMessageBox.information(self, "Copy Canceled", "File copy operation was canceled.")

    def _on_failed(self, message: str) -> None:
        self._set_running_state(False)
        QMessageBox.critical(
            self,
            "Copy Failed",
            f"The copy operation could not finish.\n\n{message}\n\nSee logs/application.log.",
        )

    def _set_running_state(self, running: bool) -> None:
        self.start_button.setEnabled(not running and not self._validation_message())
        self.cancel_button.setEnabled(running)
        for widget in (
            self.source_edit,
            self.destination_edit,
            self.filename_edit,
            self.source_button,
            self.destination_button,
            self.filename_button,
        ):
            widget.setEnabled(not running)

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

    def _append_row(self, key: str, values: list[str]) -> None:
        items = [QStandardItem(value) for value in values]
        for item in items:
            item.setEditable(False)
        self.table_models[key].appendRow(items)

    def _summary_text(self, results: CopyResults) -> str:
        return (
            "Total filenames: {total}    Copied: {copied}    Missing: {missing}    "
            "Duplicate Requests: {duplicates}    Already Exists: {exists}    "
            "Elapsed Time: {elapsed:.2f}s"
        ).format(
            total=results.total_filenames,
            copied=results.copied_count,
            missing=results.missing_count,
            duplicates=results.duplicate_count,
            exists=results.already_exists_count,
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
        QMessageBox.information(self, "Export Complete", f"Exported {file_path}")

    def _export_all(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        export_folder = Path(folder)
        for key in self.table_models:
            self._write_table_csv(key, export_folder / f"{key}.csv")
        QMessageBox.information(self, "Export Complete", f"Exported CSV files to {folder}")

    def _write_table_csv(self, key: str, file_path: Path) -> None:
        model = self.table_models[key]
        try:
            with file_path.open("w", newline="", encoding="utf-8") as csv_file:
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

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-size: 13px;
            }
            QLineEdit {
                padding: 7px 9px;
                border: 1px solid #c8cdd2;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px 14px;
                border: 1px solid #9ea7b0;
                border-radius: 4px;
                background: #f7f8fa;
            }
            QPushButton:hover {
                background: #eceff3;
            }
            QPushButton:disabled {
                color: #8a9098;
                background: #f0f1f2;
            }
            QProgressBar {
                min-height: 18px;
                border: 1px solid #c8cdd2;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2f7d6d;
            }
            QLabel#validationLabel {
                color: #a33a2f;
            }
            QTableView {
                border: 1px solid #d6dbe0;
                gridline-color: #e5e8eb;
                selection-background-color: #d9ebe7;
            }
            """
        )
