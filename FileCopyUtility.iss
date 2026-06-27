[Setup]
AppName=File Copy Utility
AppVersion=0.2.0
DefaultDirName={autopf}\File Copy Utility
DefaultGroupName=File Copy Utility
OutputBaseFilename=FileCopyUtilitySetup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
OutputDir=.
AppPublisher=File Copy Utility Contributors
AppPublisherURL=https://github.com/arunemmanuel/album-copier
AppSupportURL=https://github.com/arunemmanuel/album-copier
AppUpdatesURL=https://github.com/arunemmanuel/album-copier
LicenseFile=LICENSE
InfoBeforeFile=README.md
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\FileCopyUtility.exe
AppId={{C7A5B0FE4-7D98-43C6-BE3C-63E9DB33D7F7}}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "fileassoc"; Description: "Associate .txt files with File Copy Utility"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
Source: "dist\FileCopyUtility.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestName: "README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestName: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs
Source: "samples\*"; DestDir: "{app}\samples"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\File Copy Utility"; Filename: "{app}\FileCopyUtility.exe"
Name: "{userdesktop}\File Copy Utility"; Filename: "{app}\FileCopyUtility.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FileCopyUtility.exe"; Description: "Launch File Copy Utility"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\File Copy Utility"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.txt\OpenWithList\FileCopyUtility.exe"; Flags: uninsdeletekey; Tasks: fileassoc

[UninstallRun]
Filename: "{uninstallexe}"; Parameters: "/SILENT"

[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;
