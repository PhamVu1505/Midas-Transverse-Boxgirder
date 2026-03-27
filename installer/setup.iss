; Inno Setup Script - Midas Transverse Boxgirder
; Requires: PyInstaller output in dist\MidasTransverseBoxgirder\

[Setup]
AppName=Midas Transverse Boxgirder
AppVersion=1.0.0
AppPublisher=CITEC
DefaultDirName={autopf}\MidasTransverseBoxgirder
DefaultGroupName=Midas Transverse Boxgirder
OutputDir=..\dist\installer
OutputBaseFilename=MidasTransverseBoxgirder_Setup_v1.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Main application (PyInstaller output)
Source: "..\dist\MidasTransverseBoxgirder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Midas Transverse Boxgirder"; Filename: "{app}\MidasTransverseBoxgirder.exe"
Name: "{autodesktop}\Midas Transverse Boxgirder"; Filename: "{app}\MidasTransverseBoxgirder.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MidasTransverseBoxgirder.exe"; Description: "Launch application"; Flags: nowait postinstall skipifsilent
