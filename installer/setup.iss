; Instalador Inno Setup para AZeroCraft Launcher.
; Compilar con: ISCC installer\setup.iss  (o build.ps1 -Installer)

#define AppName "AZeroCraft"
#define AppVersion "4.37.58"
#define AppPublisher "Liebe Black"
#define AppExeName "AZeroCraft.exe"
#define AppURL "https://github.com/LiebeBlack/MD"

[Setup]
AppId={{8F3E2A1C-4B5D-4E6F-9A0B-1C2D3E4F5A6B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
AppCopyright=Copyright (C) 2026 {#AppPublisher}
AppComments=Launcher de Minecraft Java Edition para Windows.
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Launcher Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
LicenseFile=license.txt
InfoBeforeFile=features.txt
InfoAfterFile=nextsteps.txt
MinVersion=10.0
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
UsePreviousAppDir=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=AZeroCraft-Setup-{#AppVersion}
SetupIconFile=..\assets\azero.ico
WizardImageFile=..\assets\wizard.bmp
WizardSmallImageFile=..\assets\wizard-small.bmp
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageStretch=yes
SetupLogging=yes
CloseApplications=yes
CloseApplicationsFilter=AZeroCraft.exe
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\AZeroCraft\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent runasoriginaluser
