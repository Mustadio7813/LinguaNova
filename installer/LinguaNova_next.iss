; Local experimental installer SOURCE ONLY. Windows/Inno execution pending.
#ifndef BundleVersion
  #define BundleVersion "1.1.2"
#endif
#ifndef NextSource
  #define NextSource "..\dist\LinguaNovaNext"
#endif
[Setup]
AppId={{8E3B5C1A-6F2D-4B7E-9A41-3C5D7E9F1B20}
AppName=LinguaNova
AppVersion={#BundleVersion}
AppVerName=LinguaNova Next 0.2.0 Diccionario experimental (base 1.1.2)
DefaultDirName={sd}\LinguaNova
UsePreviousAppDir=yes
PrivilegesRequired=lowest
OutputDir=..\dist-next-installer
OutputBaseFilename=LinguaNova_Setup_{#BundleVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\LinguaNova.exe
[Files]
Source: "{#NextSource}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{autoprograms}\LinguaNova"; Filename: "{app}\LinguaNova.exe"
Name: "{autoprograms}\LinguaNova clásico"; Filename: "{app}\LinguaNova.exe"; Parameters: "classic"
[Run]
Filename: "{app}\LinguaNova.exe"; Description: "Abrir LinguaNova Next experimental"; Flags: postinstall nowait skipifsilent
; No settings, player persistent, caches, models or API keys are installed/deleted.
; Never publish this local 1.1.2 installer over the existing official release.
