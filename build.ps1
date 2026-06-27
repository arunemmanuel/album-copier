$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $scriptDir '.venv'
$pythonExe = Join-Path $venvDir 'Scripts/python.exe'

if (-not (Test-Path $pythonExe)) {
    py -3 -m venv $venvDir
}

& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r (Join-Path $scriptDir 'requirements.txt')
& $pythonExe -m pip install pyinstaller

New-Item -ItemType Directory -Force -Path (Join-Path $scriptDir 'dist') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $scriptDir 'build') | Out-Null

& $pythonExe -m PyInstaller --clean --noconfirm --windowed --onefile --icon (Join-Path $scriptDir 'resources/icon.ico') --name FileCopyUtility --distpath (Join-Path $scriptDir 'dist') --workpath (Join-Path $scriptDir 'build') (Join-Path $scriptDir 'packaging/FileCopyUtility.spec')

New-Item -ItemType Directory -Force -Path (Join-Path $scriptDir 'Release') | Out-Null
Copy-Item -Force (Join-Path $scriptDir 'README.md') (Join-Path $scriptDir 'Release/README.txt')
Copy-Item -Force (Join-Path $scriptDir 'LICENSE') (Join-Path $scriptDir 'Release/LICENSE.txt')
Copy-Item -Force (Join-Path $scriptDir 'CHANGELOG.md') (Join-Path $scriptDir 'Release/CHANGELOG.md')
