@echo off
setlocal
set SCRIPT_DIR=%~dp0
set INNO_SETUP_EXE="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist %INNO_SETUP_EXE% (
    echo Inno Setup was not found. Install it from https://jrsoftware.org/isinfo.php
    exit /b 1
)

call "%SCRIPT_DIR%build.bat"

"%INNO_SETUP_EXE%" /Q /O"%SCRIPT_DIR%Release" "%SCRIPT_DIR%FileCopyUtility.iss"

endlocal
