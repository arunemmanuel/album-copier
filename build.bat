@echo off
setlocal
set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%.venv
set PYTHON_EXE=%VENV_DIR%\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    py -3 -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "%SCRIPT_DIR%requirements.txt"
pip install pyinstaller

if not exist "%SCRIPT_DIR%dist" mkdir "%SCRIPT_DIR%dist"
if not exist "%SCRIPT_DIR%build" mkdir "%SCRIPT_DIR%build"

pyinstaller --clean --noconfirm --windowed --onefile --icon "%SCRIPT_DIR%resources\icon.ico" --name FileCopyUtility --distpath "%SCRIPT_DIR%dist" --workpath "%SCRIPT_DIR%build" "%SCRIPT_DIR%packaging\FileCopyUtility.spec"

if not exist "%SCRIPT_DIR%Release" mkdir "%SCRIPT_DIR%Release"
copy /Y "%SCRIPT_DIR%README.md" "%SCRIPT_DIR%Release\README.txt"
copy /Y "%SCRIPT_DIR%LICENSE" "%SCRIPT_DIR%Release\LICENSE.txt"
copy /Y "%SCRIPT_DIR%CHANGELOG.md" "%SCRIPT_DIR%Release\CHANGELOG.md"

endlocal
