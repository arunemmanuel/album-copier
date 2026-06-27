"""Report export repository for CSV, HTML, and PDF outputs."""

from __future__ import annotations

import csv
import html
import platform
import sys
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.result_model import CopyResults


class ReportRepository:
    """Persist copy reports in supported formats."""

    def export_csv_bundle(self, results: CopyResults, folder: Path) -> list[Path]:
        """Export detailed result tables as CSV files."""

        folder.mkdir(parents=True, exist_ok=True)
        outputs = {
            "copied_files.csv": self._copied_rows(results),
            "request_results.csv": [
                ["Requested Filename", "Matched Filename", "Match Type", "Source Path", "Destination Path", "Status"],
                *[
                    [
                        item.requested_filename,
                        item.matched_filename,
                        item.match_type,
                        str(item.source_path) if item.source_path else "",
                        str(item.destination_path) if item.destination_path else "",
                        item.status,
                    ]
                    for item in results.request_results
                ],
            ],
            "missing_files.csv": [["Filename", "Searched Suffix"], *[[item.filename, item.searched_suffix] for item in results.missing_files]],
            "duplicate_requests.csv": [
                ["Filename", "Occurrence Count"],
                *[
                    [item.filename, str(item.occurrence_count)]
                    for item in results.duplicate_requests
                ],
            ],
            "already_exists.csv": [
                ["Filename", "Destination Path"],
                *[
                    [item.filename, str(item.destination_path)]
                    for item in results.already_exists_files
                ],
            ],
            "ambiguous_files.csv": [
                ["Filename", "Action", "Matches"],
                *[
                    [item.filename, item.action, "\n".join(str(path) for path in item.matches)]
                    for item in results.ambiguous_files
                ],
            ],
            "verification_failures.csv": [
                [
                    "Filename",
                    "Source Path",
                    "Destination Path",
                    "Source Checksum",
                    "Destination Checksum",
                ],
                *[
                    [
                        item.filename,
                        str(item.source_path),
                        str(item.destination_path),
                        item.source_checksum,
                        item.destination_checksum,
                    ]
                    for item in results.verification_failures
                ],
            ],
        }
        written: list[Path] = []
        for filename, rows in outputs.items():
            path = folder / filename
            with path.open("w", newline="", encoding="utf-8") as csv_file:
                csv.writer(csv_file).writerows(rows)
            written.append(path)
        return written

    def export_html(self, results: CopyResults, path: Path) -> Path:
        """Export a responsive HTML report."""

        path.parent.mkdir(parents=True, exist_ok=True)
        summary = self._summary_rows(results)
        sections = [
            ("Copied Files", self._copied_rows(results)),
            (
                "Match Results",
                [
                    ["Requested Filename", "Matched Filename", "Match Type", "Source Path", "Destination Path", "Status"],
                    *[
                        [
                            item.requested_filename,
                            item.matched_filename,
                            item.match_type,
                            str(item.source_path) if item.source_path else "",
                            str(item.destination_path) if item.destination_path else "",
                            item.status,
                        ]
                        for item in results.request_results
                    ],
                ],
            ),
            ("Missing Files", [["Filename", "Searched Suffix"], *[[item.filename, item.searched_suffix] for item in results.missing_files]]),
            (
                "Duplicate Requests",
                [
                    ["Filename", "Occurrence Count"],
                    *[
                        [item.filename, str(item.occurrence_count)]
                        for item in results.duplicate_requests
                    ],
                ],
            ),
            (
                "Existing Files",
                [
                    ["Filename", "Destination Path"],
                    *[
                        [item.filename, str(item.destination_path)]
                        for item in results.already_exists_files
                    ],
                ],
            ),
            (
                "Ambiguous Files",
                [
                    ["Filename", "Action", "Matches"],
                    *[
                        [
                            item.filename,
                            item.action,
                            "<br>".join(html.escape(str(match)) for match in item.matches),
                        ]
                        for item in results.ambiguous_files
                    ],
                ],
            ),
            (
                "Verification Failures",
                [
                    ["Filename", "Source Path", "Destination Path"],
                    *[
                        [
                            item.filename,
                            str(item.source_path),
                            str(item.destination_path),
                        ]
                        for item in results.verification_failures
                    ],
                ],
            ),
        ]
        content = [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            "<title>File Copy Utility Report</title>",
            "<style>",
            "body{font-family:Arial,sans-serif;margin:24px;color:#1f2933;background:#f6f8fb}",
            ".logo{border:2px dashed #98a2b3;padding:18px;text-align:center;background:#fff;margin-bottom:18px}",
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}",
            ".card{background:#fff;border-left:5px solid #2f7d6d;padding:12px;box-shadow:0 1px 3px #d0d5dd}",
            "table{border-collapse:collapse;width:100%;background:#fff;margin:12px 0 28px}",
            "th,td{border:1px solid #d0d5dd;padding:8px;text-align:left;vertical-align:top}",
            "th{background:#e9eef3;cursor:pointer}",
            ".bad{border-left-color:#b42318}.warn{border-left-color:#b7791f}",
            "</style>",
            "<script>function sortTable(t,n){let r=[...t.rows].slice(1),a=t.dataset.asc!=='1';r.sort((x,y)=>x.cells[n].innerText.localeCompare(y.cells[n].innerText));if(!a)r.reverse();r.forEach(row=>t.tBodies[0].appendChild(row));t.dataset.asc=a?'1':'0'}</script>",
            "</head><body><div class='logo'>Company Logo Placeholder</div>",
            "<h1>File Copy Utility Report</h1>",
            "<div class='grid'>",
        ]
        for key, value in summary:
            css_class = "card bad" if "Failed" in key and value != "0" else "card"
            content.append(f"<div class='{css_class}'><strong>{html.escape(key)}</strong><br>{html.escape(value)}</div>")
        content.append("</div>")
        for title, rows in sections:
            content.append(f"<h2>{html.escape(title)}</h2>")
            content.append(self._html_table(rows))
        content.append("</body></html>")
        path.write_text("\n".join(content), encoding="utf-8")
        return path

    def export_pdf(self, results: CopyResults, path: Path) -> Path:
        """Export a professionally formatted PDF report."""

        path.parent.mkdir(parents=True, exist_ok=True)
        document = SimpleDocTemplate(str(path), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph("File Copy Utility Report", styles["Title"]),
            Paragraph("Company Logo Placeholder", styles["Italic"]),
            Spacer(1, 12),
            self._pdf_table([["Metric", "Value"], *self._summary_rows(results)]),
            Spacer(1, 18),
        ]
        for title, rows in (
            ("Copied Files", self._copied_rows(results)),
            ("Match Results", [
                ["Requested Filename", "Matched Filename", "Match Type", "Source Path", "Destination Path", "Status"],
                *[
                    [
                        item.requested_filename,
                        item.matched_filename,
                        item.match_type,
                        str(item.source_path) if item.source_path else "",
                        str(item.destination_path) if item.destination_path else "",
                        item.status,
                    ]
                    for item in results.request_results
                ],
            ]),
            ("Missing Files", [["Filename", "Searched Suffix"], *[[item.filename, item.searched_suffix] for item in results.missing_files]]),
            ("Duplicate Requests", [["Filename", "Occurrence Count"], *[[item.filename, str(item.occurrence_count)] for item in results.duplicate_requests]]),
            ("Existing Files", [["Filename", "Destination Path"], *[[item.filename, str(item.destination_path)] for item in results.already_exists_files]]),
            ("Verification Failures", [["Filename", "Source Path", "Destination Path"], *[[item.filename, str(item.source_path), str(item.destination_path)] for item in results.verification_failures]]),
        ):
            elements.append(Paragraph(title, styles["Heading2"]))
            elements.append(self._pdf_table(rows))
            elements.append(Spacer(1, 12))
        document.build(elements)
        return path

    def _summary_rows(self, results: CopyResults) -> list[list[str]]:
        return [
            ["Application Name", "File Copy Utility"],
            ["Execution Date", datetime.now().strftime("%Y-%m-%d")],
            ["Execution Time", datetime.now().strftime("%H:%M:%S")],
            ["Operating System", platform.platform()],
            ["Python Version", sys.version.split()[0]],
            ["Source Folder", str(results.source_folder or "")],
            ["Destination Folder", str(results.destination_folder or "")],
            ["Recursive Search Enabled", str(results.recursive_search)],
            ["Overwrite Policy", results.overwrite_policy],
            ["Total Requested", str(results.total_filenames)],
            ["Files Copied", str(results.copied_count)],
            ["Files Missing", str(results.missing_count)],
            ["Exact Matches", str(results.exact_match_count)],
            ["Last 4 Characters Matches", str(results.suffix_match_count)],
            ["Multiple Matches Resolved", str(results.multiple_match_count)],
            ["Duplicate Requests", str(results.duplicate_count)],
            ["Already Existing", str(results.already_exists_count)],
            ["Ambiguous Files", str(results.ambiguous_count)],
            ["Verification Passed", str(results.verification_passed_count)],
            ["Verification Failed", str(results.verification_failed_count)],
            ["Elapsed Time", f"{results.elapsed_seconds:.2f}s"],
        ]

    def _copied_rows(self, results: CopyResults) -> list[list[str]]:
        return [
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
            *[
                [
                    item.filename,
                    str(item.source_path),
                    str(item.destination_path),
                    item.copy_time.strftime("%Y-%m-%d %H:%M:%S"),
                    item.verification_status,
                    str(item.file_size),
                    str(item.overwritten),
                    item.previous_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if item.previous_timestamp
                    else "",
                    item.new_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    if item.new_timestamp
                    else "",
                ]
                for item in results.copied_files
            ],
        ]

    def _html_table(self, rows: list[list[str]]) -> str:
        if not rows:
            return "<table></table>"
        headers, body = rows[0], rows[1:]
        table = ["<table><thead><tr>"]
        for index, header in enumerate(headers):
            table.append(
                f"<th onclick='sortTable(this.closest(\"table\"),{index})'>{html.escape(header)}</th>"
            )
        table.append("</tr></thead><tbody>")
        for row in body:
            table.append("<tr>")
            for cell in row:
                table.append(f"<td>{cell if '<br>' in cell else html.escape(cell)}</td>")
            table.append("</tr>")
        table.append("</tbody></table>")
        return "".join(table)

    def _pdf_table(self, rows: list[list[str]]) -> Table:
        display_rows = rows if len(rows) > 1 else [rows[0], ["", ""]]
        table = Table(display_rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9ebe7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table
