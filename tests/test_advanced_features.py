from __future__ import annotations

import logging
from pathlib import Path

from models.result_model import (
    AMBIGUOUS_ALL,
    AMBIGUOUS_SKIP,
    OVERWRITE_RENAME,
    OVERWRITE_REPLACE,
    OVERWRITE_SKIP,
    FALLBACK_EXACT_ONLY,
    FALLBACK_EXACT_SUFFIX,
    FALLBACK_SUFFIX_ONLY,
    AmbiguousFile,
    MissingFile,
)
from reports.report_repository import ReportRepository
from services.file_operation_service import CopyOptions, FileOperationService
from utils.checksum import checksums_match, sha256_file
from utils.file_utils import find_source_matches, next_available_path


def service() -> FileOperationService:
    return FileOperationService(logging.getLogger("tests"))


def test_recursive_search_finds_nested_matches(tmp_path: Path):
    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    (nested / "report.pdf").write_text("nested", encoding="utf-8")

    assert find_source_matches(source, "report.pdf", recursive=False) == []
    assert find_source_matches(source, "report.pdf", recursive=True) == [
        nested / "report.pdf"
    ]


def test_ambiguous_policy_skip_records_ambiguous_file(tmp_path: Path):
    matches = [tmp_path / "a" / "same.txt", tmp_path / "b" / "same.txt"]

    resolved, issue = service().resolve_matches("same.txt", matches, AMBIGUOUS_SKIP)

    assert resolved == []
    assert isinstance(issue, AmbiguousFile)
    assert issue.action == AMBIGUOUS_SKIP


def test_ambiguous_policy_all_returns_all_matches(tmp_path: Path):
    matches = [tmp_path / "a" / "same.txt", tmp_path / "b" / "same.txt"]

    resolved, issue = service().resolve_matches("same.txt", matches, AMBIGUOUS_ALL)

    assert resolved == matches
    assert isinstance(issue, AmbiguousFile)


def test_rename_policy_never_overwrites_existing_file(tmp_path: Path):
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "example.pdf").write_text("old", encoding="utf-8")
    (destination / "example (1).pdf").write_text("older", encoding="utf-8")

    assert next_available_path(destination / "example.pdf") == (
        destination / "example (2).pdf"
    )


def test_suffix_fallback_matches_last_four_characters(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    target = source / "Customer_2345.pdf"
    target.write_text("fallback", encoding="utf-8")

    resolved, issue, match_type, suffix = service().resolve_source_match(
        source,
        "Invoice_ABC12345.pdf",
        recursive=False,
        fallback_mode=FALLBACK_EXACT_SUFFIX,
        ambiguous_policy=AMBIGUOUS_SKIP,
    )

    assert issue is None
    assert match_type == "Last 4 Characters Match"
    assert suffix == "2345"
    assert resolved == [target]


def test_suffix_fallback_missing_includes_searched_suffix(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()

    resolved, issue, match_type, suffix = service().resolve_source_match(
        source,
        "Invoice_ABC12345.pdf",
        recursive=False,
        fallback_mode=FALLBACK_EXACT_SUFFIX,
        ambiguous_policy=AMBIGUOUS_SKIP,
    )

    assert resolved == []
    assert isinstance(issue, MissingFile)
    assert issue.searched_suffix == "2345"
    assert match_type == "Missing"
    assert suffix == "2345"


def test_exact_only_mode_skips_suffix_fallback(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    target = source / "Customer_2345.pdf"
    target.write_text("fallback", encoding="utf-8")

    resolved, issue, match_type, suffix = service().resolve_source_match(
        source,
        "Invoice_ABC12345.pdf",
        recursive=False,
        fallback_mode=FALLBACK_EXACT_ONLY,
        ambiguous_policy=AMBIGUOUS_SKIP,
    )

    assert resolved == []
    assert isinstance(issue, MissingFile)
    assert match_type == "Missing"
    assert suffix == "2345"


def test_copy_skip_existing_returns_already_exists(tmp_path: Path):
    source = tmp_path / "source"
    destination = tmp_path / "dest"
    source.mkdir()
    destination.mkdir()
    source_file = source / "file.txt"
    source_file.write_text("new", encoding="utf-8")
    (destination / "file.txt").write_text("old", encoding="utf-8")

    decision = service().copy_one(
        source_file, destination, CopyOptions(overwrite_policy=OVERWRITE_SKIP)
    )

    assert decision.copied is None
    assert decision.already_exists is not None
    assert (destination / "file.txt").read_text(encoding="utf-8") == "old"


def test_copy_overwrite_existing_replaces_file(tmp_path: Path):
    source = tmp_path / "source"
    destination = tmp_path / "dest"
    source.mkdir()
    destination.mkdir()
    source_file = source / "file.txt"
    source_file.write_text("new", encoding="utf-8")
    (destination / "file.txt").write_text("old", encoding="utf-8")

    decision = service().copy_one(
        source_file, destination, CopyOptions(overwrite_policy=OVERWRITE_REPLACE)
    )

    assert decision.copied is not None
    assert decision.copied.overwritten is True
    assert (destination / "file.txt").read_text(encoding="utf-8") == "new"


def test_copy_rename_new_file_keeps_existing_file(tmp_path: Path):
    source = tmp_path / "source"
    destination = tmp_path / "dest"
    source.mkdir()
    destination.mkdir()
    source_file = source / "file.txt"
    source_file.write_text("new", encoding="utf-8")
    (destination / "file.txt").write_text("old", encoding="utf-8")

    decision = service().copy_one(
        source_file, destination, CopyOptions(overwrite_policy=OVERWRITE_RENAME)
    )

    assert decision.copied is not None
    assert decision.copied.destination_path == destination / "file (1).txt"
    assert (destination / "file.txt").read_text(encoding="utf-8") == "old"


def test_checksum_verification(tmp_path: Path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"
    source.write_text("same", encoding="utf-8")
    destination.write_text("same", encoding="utf-8")

    matched, source_checksum, destination_checksum = checksums_match(source, destination)

    assert matched is True
    assert source_checksum == destination_checksum == sha256_file(source)


def test_report_generation_writes_html_pdf_and_csv(tmp_path: Path):
    from models.result_model import CopyResults

    results = CopyResults(total_filenames=1, elapsed_seconds=0.5)
    repository = ReportRepository()

    csv_paths = repository.export_csv_bundle(results, tmp_path)
    html_path = repository.export_html(results, tmp_path / "report.html")
    pdf_path = repository.export_pdf(results, tmp_path / "report.pdf")

    assert csv_paths
    assert html_path.exists()
    assert "File Copy Utility Report" in html_path.read_text(encoding="utf-8")
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
