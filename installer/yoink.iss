; Inno Setup script for Yoink.
;
; Run via: ISCC.exe /DAppVersion=2.0.0 installer\yoink.iss
; (build.py invokes this automatically when ISCC is on PATH.)

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppName        "Yoink"
#define MyAppPublisher   "Hrishikesh Panigrahi"
#define MyAppURL         "https://github.com/Hrishikesh-Panigrahi/yoink"
#define MyAppExeName     "Yoink.exe"

[Setup]
AppId={{B6F3D2D2-8B2A-4A6A-9A6E-46D8B5C03511}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist
OutputBaseFilename=Yoink-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog commandline
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "magnetassoc"; Description: "Open magnet: links with Yoink"; GroupDescription: "File associations:"
Name: "torrentassoc"; Description: "Open .torrent files with Yoink"; GroupDescription: "File associations:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; magnet: protocol handler
Root: HKCU; Subkey: "Software\Classes\magnet"; ValueType: string; ValueName: ""; ValueData: "URL:Magnet Link"; Tasks: magnetassoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\magnet"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Tasks: magnetassoc
Root: HKCU; Subkey: "Software\Classes\magnet\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"",1"; Tasks: magnetassoc
Root: HKCU; Subkey: "Software\Classes\magnet\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: magnetassoc

; .torrent file association
Root: HKCU; Subkey: "Software\Classes\.torrent"; ValueType: string; ValueName: ""; ValueData: "Yoink.Torrent"; Tasks: torrentassoc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Yoink.Torrent"; ValueType: string; ValueName: ""; ValueData: "Torrent File"; Tasks: torrentassoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Yoink.Torrent\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"",1"; Tasks: torrentassoc
Root: HKCU; Subkey: "Software\Classes\Yoink.Torrent\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: torrentassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
