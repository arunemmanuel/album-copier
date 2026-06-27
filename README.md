# File Copy Utility

A cross-platform Python desktop application for copying selected files from a source folder to a destination folder using a `.txt` filename list.

## Features

- Source folder, destination folder, and `.txt` filename-list selectors
- Non-blocking copy operation using `QThread`
- Live progress, current filename, and summary counts
- Detection for missing files, duplicate requests, and already existing destination files
- Recursive search with ambiguous match handling
- Overwrite policies: skip, overwrite, or rename new copies safely
- Optional SHA-256 verification after copy
- Drag-and-drop support for folders and `.txt` filename lists
- Persistent settings with `QSettings`
- Light, dark, and system-default theme choices
- Open source, destination, log folder, and log file shortcuts
- Pause/resume, clear results, retry failed requests, toolbar, status bar, and shortcuts
- Timestamp-preserving copies with `shutil.copy2()`
- Searchable results tabs
- CSV export per result tab plus full CSV/HTML/PDF report bundles
- Rotating application logs at `logs/application.log`

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Filename List Format

Use one filename per line:

```text
sample1.pdf
test.docx
abc.xlsx
image01.png
report.csv
```

Blank lines and leading or trailing spaces are ignored.

## Tests

```bash
pytest
```

## Packaging With PyInstaller

Install dependencies first, then run:

```bash
pyinstaller --name "File Copy Utility" --windowed --onefile main.py
```

Windows release executable:

```bash
pyinstaller --name FileCopyUtility --windowed --onefile main.py
```

macOS app bundle:

```bash
pyinstaller --name FileCopyUtility --windowed main.py
```

Spec-based build:

```bash
cd packaging
pyinstaller FileCopyUtility.spec
```

Briefcase commands are documented in `INSTALL.md`; tagged GitHub releases are configured in `.github/workflows/release-build.yml`.

For a directory-based build that is easier to inspect:

```bash
pyinstaller --name "File Copy Utility" --windowed main.py
```

Place final icon files in `resources/` and pass the relevant `--icon` option for your platform.

## Screenshots

Add screenshots here after packaging or during QA:

- Main window
- Copy in progress
- Results tabs
- CSV export

## Troubleshooting

- If the Start Copy button is disabled, confirm that the source folder, destination folder, and filename list all exist.
- If a filename is marked Missing, confirm it exists directly inside the selected source folder. Subfolders are not searched.
- If a file is marked Already Exists, a file with the same name is already present in the destination folder.
- If copying fails, check `logs/application.log` for the complete stack trace.
- On macOS, if the packaged app cannot access folders, check System Settings privacy permissions.
