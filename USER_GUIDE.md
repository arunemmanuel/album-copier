# User Guide

1. Select a source folder.
2. Select a destination folder.
3. Select a `.txt` file containing one filename per line.
4. Choose Search Subfolders when recursive source lookup is needed.
5. Choose an overwrite policy: Skip Existing, Overwrite Existing, or Rename New File.
6. Choose how ambiguous recursive matches should be handled.
7. Enable Verify copied files to compare SHA-256 checksums after each copy.
8. Start the copy operation.
9. Review results in the tabs and export CSV, HTML, or PDF reports.

The app remembers your most recent paths, theme, window placement, search option, verification option, overwrite policy, and export folder.

Screenshot placeholders:

- Main window
- Copy progress
- Report output

Architecture diagram placeholder:

```text
UI -> Controller -> Worker -> FileOperationService -> File Utils / Checksum
                         \-> ReportRepository
```
