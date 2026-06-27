from datetime import datetime
from pathlib import Path

from models.result_model import CopiedFile, CopyResults, MissingFile
from utils.file_utils import (
    copy_file,
    duplicate_counts,
    find_source_file,
    read_filename_list,
    unique_filenames_in_order,
)


def test_read_filename_list_ignores_blank_lines_and_strips_spaces(tmp_path: Path):
    filename_list = tmp_path / "filenames.txt"
    filename_list.write_text(" sample1.pdf \n\nreport.csv\n   \n", encoding="utf-8")

    assert read_filename_list(filename_list) == ["sample1.pdf", "report.csv"]


def test_duplicate_detection_counts_repeated_requests():
    filenames = ["a.pdf", "b.pdf", "a.pdf", "c.pdf", "b.pdf", "b.pdf"]

    assert duplicate_counts(filenames) == {"a.pdf": 2, "b.pdf": 3}
    assert unique_filenames_in_order(filenames) == ["a.pdf", "b.pdf", "c.pdf"]


def test_missing_file_detection(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "exists.pdf").write_text("content", encoding="utf-8")

    assert find_source_file(source, "exists.pdf") == source / "exists.pdf"
    assert find_source_file(source, "missing.pdf") is None


def test_copy_function_preserves_filename(tmp_path: Path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    source_file = source / "document.txt"
    source_file.write_text("hello", encoding="utf-8")

    copied_to = copy_file(source_file, destination)

    assert copied_to == destination / "document.txt"
    assert copied_to.read_text(encoding="utf-8") == "hello"


def test_summary_calculation(tmp_path: Path):
    results = CopyResults(total_filenames=3, elapsed_seconds=1.25)
    copied = tmp_path / "copied.txt"
    results.copied_files.append(CopiedFile("copied.txt", copied, copied, datetime.now()))
    results.missing_files.append(MissingFile("missing.txt"))

    summary = results.summary()

    assert summary["total_filenames"] == 3
    assert summary["copied"] == 1
    assert summary["missing"] == 1
    assert summary["duplicate_requests"] == 0
    assert summary["already_exists"] == 0
    assert summary["elapsed_seconds"] == 1.25
