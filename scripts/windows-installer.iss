; Compile with /DSourceRoot=<release source checkout>. Inno Setup 6 or later.
#ifndef SourceRoot
  #define SourceRoot ".."
#endif
#define AppVersion "2.0.0-beta.2"

[Setup]
AppId={{9C16D58C-4C66-45A5-A748-225428BE996B}
AppName=BROWSOR
AppVersion={#AppVersion}
AppVerName=BROWSOR 2.0 beta 2
AppPublisher=WALDEX451
AppPublisherURL=https://github.com/WALDEX451/BROWSOR
AppSupportURL=https://github.com/WALDEX451/BROWSOR/issues
AppUpdatesURL=https://github.com/WALDEX451/BROWSOR/releases
DefaultDirName={localappdata}\Programs\BROWSOR Beta
DefaultGroupName=BROWSOR Beta
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#SourceRoot}\dist
OutputBaseFilename=BROWSOR-{#AppVersion}-windows-x64-setup
SetupIconFile={#SourceRoot}\build\BROWSOR.ico
UninstallDisplayIcon={app}\BROWSOR.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion=2.0.0.1
VersionInfoProductVersion=2.0.0.1
VersionInfoProductTextVersion={#AppVersion}
VersionInfoDescription=BROWSOR 2.0 beta 2 Installer
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceRoot}\dist\BROWSOR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\BROWSOR Beta"; Filename: "{app}\BROWSOR.exe"
Name: "{autodesktop}\BROWSOR Beta"; Filename: "{app}\BROWSOR.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\BROWSOR.exe"; Description: "Open BROWSOR 2.0 beta 2"; Flags: nowait postinstall skipifsilent
