#define MyAppName "Fix My Folder"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Fix My Folder"
#define MyAppExeName "FixMyFolder.exe"

[Setup]
AppId={{7D971467-3F22-44B8-9AE7-AF86DD81351C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Fix My Folder
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=FixMyFolderSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\PRIVACY.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "docs\TERMS.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "docs\SECURITY.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\Classes\.zip\shell\FixMyFolderExtract"; ValueType: string; ValueName: ""; ValueData: "Extract with Fix My Folder"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.zip\shell\FixMyFolderExtract"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.zip\shell\FixMyFolderExtract\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --extract-archive ""%1"""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\FixMyFolderExtract"; ValueType: string; ValueName: ""; ValueData: "Extract with Fix My Folder"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\FixMyFolderExtract"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\FixMyFolderExtract\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --extract-archive ""%1"""; Flags: uninsdeletekey

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
