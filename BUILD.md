# Build Guide

## Prerequisites

- Windows 10/11 64-bit
- Python 3.10+
- Inno Setup 6 (optional, for creating the installer)

## Build from source

1. Open PowerShell in the repository root.
2. Run:
   ```powershell
   .\build.ps1
   ```
3. The executable will be generated in the dist folder.

## Build the installer

1. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php.
2. Run:
   ```powershell
   .\build_installer.bat
   ```
3. The installer will be created as Release/FileCopyUtilitySetup.exe.

## Updating dependencies

Run:
```powershell
python -m pip install --upgrade -r requirements.txt
```

## Signing the executable (optional)

If you have a code-signing certificate, sign the generated executable with your preferred tool before distribution.

## Troubleshooting

- If PyInstaller is missing, the build scripts install it automatically.
- If Inno Setup is not installed, the installer build step will stop with a clear message.
- Ensure the application icon exists at resources/icon.ico before building.
