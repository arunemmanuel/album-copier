# Installation

## Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Package

Windows executable:

```bash
pyinstaller --name FileCopyUtility --windowed --onefile main.py
```

macOS app bundle:

```bash
pyinstaller --name FileCopyUtility --windowed main.py
```

Briefcase:

```bash
python -m pip install briefcase
briefcase create
briefcase build
briefcase package
```
