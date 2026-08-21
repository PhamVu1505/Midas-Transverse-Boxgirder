; Inno Setup Script - Midas Transverse Boxgirder
; Requires: PyInstaller output in dist\MidasTransverseBoxgirder\

[Setup]
AppName=Midas Transverse Boxgirder
AppVersion=1.5.0
AppPublisher=CITEC
DefaultDirName={autopf}\MidasTransverseBoxgirder
DefaultGroupName=Midas Transverse Boxgirder
OutputDir=..\dist\installer
OutputBaseFilename=MidasTransverseBoxgirder_Setup_v1.5.0
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MidasTransverseBoxgirder.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
; Muc menu chuot phai cho .dxf. De nguoi dung TU CHON: no sua menu chuot
; phai cua may ho, khong duoc tu y them.
Name: "dxfmenu"; Description: "Them muc ""Tao file MCT"" khi bam chuot phai vao file .dxf"; GroupDescription: "Tich hop Windows:"

[Files]
; Main application (PyInstaller output)
Source: "..\dist\MidasTransverseBoxgirder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Icon
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; User guide
Source: "..\docs\USER-GUIDE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Thu muc du lieu chung: giay phep, so dung thu, nhat ky su dung. Mac dinh
; ProgramData khong cho user thuong ghi, ma app phai ghi duoc CA HAI noi (xem
; src/security/paths.py) - khong cap quyen thi chi con mot ban ghi, va xoa mot
; ban la mat sach.
Name: "{commonappdata}\Midas Transverse Boxgirder"; Permissions: users-modify

[Registry]
; Menu chuot phai -> Tao file MCT. Ghi vao HKCU (installer chay quyen thuong)
; va vao SystemFileAssociations chu KHONG vao ProgID cua .dxf: duoi .dxf gan nhu
; luon thuoc ve AutoCAD/BricsCAD; treo vao ProgID cua ho thi cai lai CAD la mat,
; ma doi ProgID thi ta cuop mat phan mo mac dinh cua nguoi ta.
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.dxf\shell\MidasTransverseBoxgirder.TaoMCT"; ValueType: string; ValueData: "Tao file MCT (Midas Transverse)"; Flags: uninsdeletekey; Tasks: dxfmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.dxf\shell\MidasTransverseBoxgirder.TaoMCT"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\icon.ico"; Tasks: dxfmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.dxf\shell\MidasTransverseBoxgirder.TaoMCT\command"; ValueType: string; ValueData: """{app}\MidasTransverseBoxgirder.exe"" --mct ""%1"""; Tasks: dxfmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\MidasTransverseBoxgirder.TaoMCT"; ValueType: string; ValueData: "Tao MCT cho moi DXF trong thu muc"; Flags: uninsdeletekey; Tasks: dxfmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\MidasTransverseBoxgirder.TaoMCT"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\icon.ico"; Tasks: dxfmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\MidasTransverseBoxgirder.TaoMCT\command"; ValueType: string; ValueData: """{app}\MidasTransverseBoxgirder.exe"" --mct ""%V"""; Tasks: dxfmenu

[Icons]
Name: "{group}\Midas Transverse Boxgirder"; Filename: "{app}\MidasTransverseBoxgirder.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\User Guide"; Filename: "{app}\USER-GUIDE.txt"
Name: "{autodesktop}\Midas Transverse Boxgirder"; Filename: "{app}\MidasTransverseBoxgirder.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\MidasTransverseBoxgirder.exe"; Description: "Launch application"; Flags: nowait postinstall skipifsilent
