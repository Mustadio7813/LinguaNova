; SPDX-License-Identifier: GPL-3.0-or-later
; LinguaNova installer (Inno Setup 6.5 or later). Added 2026-10-18.
;
; Build:   build_installer.bat   (or: ISCC /DMyAppVersion=1.1.0 installer\LinguaNova.iss)
; Input:   dist\LinguaNova\ produced by build_windows.bat / LinguaNova.spec
; Output:  installer\Output\LinguaNova_Setup_<version>.exe
;
; Behaviour
; - The user picks one of the PC's internal drives; LinguaNova is always
;   installed in <drive>:\LinguaNova. USB drives, memory cards, network drives
;   and CD/DVD drives are not offered.
; - Per-user install (no administrator rights): installing and updating never
;   show the Windows permission prompt.
; - Updates (same AppId) reuse the previous folder without asking. The
;   automatic updater runs this installer with /VERYSILENT /DIR=... /LNUPDATE
;   and the installer reopens LinguaNova when it finishes.
; - Settings live in %APPDATA%\LinguaNova and are never touched.
; - Desktop shortcut (optional, on by default) and Start menu entry, both with
;   the AppUserModelID "LinguaNova" used by run.py, so a pinned taskbar icon
;   keeps working after updates. Windows does not allow installers to pin to
;   the taskbar; the last page explains how to do it.

#if Ver < EncodeVer(6, 5, 0)
  #error LinguaNova's installer needs Inno Setup 6.5 or later.
#endif

#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\LinguaNova"
#endif

#define MyAppName "LinguaNova"
#define MyAppExe "LinguaNova.exe"
#define MyAppUserModelID "LinguaNova"
#define MyRepoUrl "https://github.com/Mustadio7813/LinguaNova"
; Never change this id: updates find the existing installation through it.
#define MyAppIdGuid "8E3B5C1A-6F2D-4B7E-9A41-3C5D7E9F1B20"

[Setup]
AppId={{{#MyAppIdGuid}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Mustadio7813
AppPublisherURL={#MyRepoUrl}
AppSupportURL={#MyRepoUrl}/issues
AppUpdatesURL={#MyRepoUrl}/releases
DefaultDirName={sd}\LinguaNova
DisableDirPage=yes
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=Output
OutputBaseFilename=LinguaNova_Setup_{#MyAppVersion}
SetupIconFile=..\linguanova.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto
LanguageDetectionMethod=uilanguage
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
; Shipped with LinguaNova (see installer\languages\INNO_SETUP_LICENSE.txt).
Name: "chinesesimplified"; MessagesFile: "languages\ChineseSimplified.isl"
Name: "persian"; MessagesFile: "languages\Farsi.isl"

[CustomMessages]
english.DriveTitle=Choose a drive
english.DriveDescription=LinguaNova will be installed in the \LinguaNova folder of the drive you choose.
english.DriveSubCaption=Only this computer's internal drives are listed. USB drives, memory cards and network drives cannot be used.
english.DriveItem=%1\LinguaNova   —   %2 GB free
english.DriveItemLow=%1\LinguaNova   —   not enough free space
english.DriveWindows=(Windows)
english.DriveNone=No internal drive with enough free space was found. LinguaNova cannot be installed on USB drives, memory cards or network drives.
english.DriveChoose=Choose a drive to continue.
english.TaskbarHint=Tip: to pin LinguaNova to the taskbar, open it, right-click its icon on the taskbar and choose "Pin to taskbar".

spanish.DriveTitle=Elija un disco
spanish.DriveDescription=LinguaNova se instalará en la carpeta \LinguaNova del disco que elija.
spanish.DriveSubCaption=Solo se muestran los discos internos de este equipo. No se pueden usar pendrives, tarjetas de memoria ni unidades de red.
spanish.DriveItem=%1\LinguaNova   —   %2 GB libres
spanish.DriveItemLow=%1\LinguaNova   —   espacio libre insuficiente
spanish.DriveWindows=(Windows)
spanish.DriveNone=No se encontró ningún disco interno con espacio suficiente. LinguaNova no se puede instalar en pendrives, tarjetas de memoria ni unidades de red.
spanish.DriveChoose=Elija un disco para continuar.
spanish.TaskbarHint=Consejo: para anclar LinguaNova a la barra de tareas, ábralo, haga clic derecho en su icono de la barra de tareas y elija "Anclar a la barra de tareas".

german.DriveTitle=Laufwerk auswählen
german.DriveDescription=LinguaNova wird im Ordner \LinguaNova des gewählten Laufwerks installiert.
german.DriveSubCaption=Es werden nur die internen Laufwerke dieses Computers angezeigt. USB-Sticks, Speicherkarten und Netzlaufwerke können nicht verwendet werden.
german.DriveItem=%1\LinguaNova   —   %2 GB frei
german.DriveItemLow=%1\LinguaNova   —   nicht genügend freier Speicher
german.DriveWindows=(Windows)
german.DriveNone=Es wurde kein internes Laufwerk mit genügend freiem Speicher gefunden. LinguaNova kann nicht auf USB-Sticks, Speicherkarten oder Netzlaufwerken installiert werden.
german.DriveChoose=Wählen Sie ein Laufwerk, um fortzufahren.
german.TaskbarHint=Tipp: Um LinguaNova an die Taskleiste anzuheften, öffnen Sie das Programm, klicken Sie mit der rechten Maustaste auf sein Symbol in der Taskleiste und wählen Sie „An Taskleiste anheften“.

french.DriveTitle=Choisissez un disque
french.DriveDescription=LinguaNova sera installé dans le dossier \LinguaNova du disque choisi.
french.DriveSubCaption=Seuls les disques internes de cet ordinateur sont affichés. Les clés USB, cartes mémoire et lecteurs réseau ne peuvent pas être utilisés.
french.DriveItem=%1\LinguaNova   —   %2 Go libres
french.DriveItemLow=%1\LinguaNova   —   espace libre insuffisant
french.DriveWindows=(Windows)
french.DriveNone=Aucun disque interne disposant d'assez d'espace libre n'a été trouvé. LinguaNova ne peut pas être installé sur une clé USB, une carte mémoire ou un lecteur réseau.
french.DriveChoose=Choisissez un disque pour continuer.
french.TaskbarHint=Astuce : pour épingler LinguaNova à la barre des tâches, ouvrez-le, faites un clic droit sur son icône dans la barre des tâches et choisissez « Épingler à la barre des tâches ».

japanese.DriveTitle=ドライブの選択
japanese.DriveDescription=LinguaNova は選択したドライブの \LinguaNova フォルダーにインストールされます。
japanese.DriveSubCaption=このコンピューターの内蔵ドライブのみが表示されます。USB メモリ、メモリーカード、ネットワークドライブは使用できません。
japanese.DriveItem=%1\LinguaNova   —   空き容量 %2 GB
japanese.DriveItemLow=%1\LinguaNova   —   空き容量が不足しています
japanese.DriveWindows=(Windows)
japanese.DriveNone=十分な空き容量のある内蔵ドライブが見つかりませんでした。LinguaNova は USB メモリ、メモリーカード、ネットワークドライブにはインストールできません。
japanese.DriveChoose=続行するにはドライブを選択してください。
japanese.TaskbarHint=ヒント: LinguaNova をタスクバーにピン留めするには、起動してタスクバーのアイコンを右クリックし、「タスクバーにピン留めする」を選択してください。

russian.DriveTitle=Выбор диска
russian.DriveDescription=LinguaNova будет установлена в папку \LinguaNova на выбранном диске.
russian.DriveSubCaption=Показаны только внутренние диски этого компьютера. USB-накопители, карты памяти и сетевые диски использовать нельзя.
russian.DriveItem=%1\LinguaNova   —   свободно %2 ГБ
russian.DriveItemLow=%1\LinguaNova   —   недостаточно свободного места
russian.DriveWindows=(Windows)
russian.DriveNone=Не найден внутренний диск с достаточным свободным местом. LinguaNova нельзя установить на USB-накопитель, карту памяти или сетевой диск.
russian.DriveChoose=Выберите диск, чтобы продолжить.
russian.TaskbarHint=Совет: чтобы закрепить LinguaNova на панели задач, запустите программу, щёлкните правой кнопкой мыши по её значку на панели задач и выберите «Закрепить на панели задач».

turkish.DriveTitle=Bir sürücü seçin
turkish.DriveDescription=LinguaNova, seçtiğiniz sürücüdeki \LinguaNova klasörüne kurulacak.
turkish.DriveSubCaption=Yalnızca bu bilgisayarın dahili sürücüleri listelenir. USB bellekler, hafıza kartları ve ağ sürücüleri kullanılamaz.
turkish.DriveItem=%1\LinguaNova   —   %2 GB boş
turkish.DriveItemLow=%1\LinguaNova   —   yeterli boş alan yok
turkish.DriveWindows=(Windows)
turkish.DriveNone=Yeterli boş alana sahip dahili bir sürücü bulunamadı. LinguaNova USB belleklere, hafıza kartlarına veya ağ sürücülerine kurulamaz.
turkish.DriveChoose=Devam etmek için bir sürücü seçin.
turkish.TaskbarHint=İpucu: LinguaNova'yı görev çubuğuna sabitlemek için programı açın, görev çubuğundaki simgesine sağ tıklayın ve "Görev çubuğuna sabitle"yi seçin.

chinesesimplified.DriveTitle=选择磁盘
chinesesimplified.DriveDescription=LinguaNova 将安装到所选磁盘的 \LinguaNova 文件夹中。
chinesesimplified.DriveSubCaption=仅列出本机的内部磁盘。不能使用 U 盘、存储卡或网络驱动器。
chinesesimplified.DriveItem=%1\LinguaNova   —   可用 %2 GB
chinesesimplified.DriveItemLow=%1\LinguaNova   —   可用空间不足
chinesesimplified.DriveWindows=(Windows)
chinesesimplified.DriveNone=未找到可用空间足够的内部磁盘。LinguaNova 不能安装到 U 盘、存储卡或网络驱动器上。
chinesesimplified.DriveChoose=请选择一个磁盘以继续。
chinesesimplified.TaskbarHint=提示：要将 LinguaNova 固定到任务栏，请打开它，在任务栏上右键单击其图标，然后选择“固定到任务栏”。

persian.DriveTitle=انتخاب درایو
persian.DriveDescription=LinguaNova در پوشهٔ \LinguaNova درایوی که انتخاب می‌کنید نصب می‌شود.
persian.DriveSubCaption=فقط درایوهای داخلی این رایانه نمایش داده می‌شوند. از فلش‌مموری، کارت حافظه و درایو شبکه نمی‌توان استفاده کرد.
persian.DriveItem=%1\LinguaNova   —   %2 گیگابایت فضای آزاد
persian.DriveItemLow=%1\LinguaNova   —   فضای آزاد کافی نیست
persian.DriveWindows=(Windows)
persian.DriveNone=هیچ درایو داخلی با فضای آزاد کافی پیدا نشد. LinguaNova را نمی‌توان روی فلش‌مموری، کارت حافظه یا درایو شبکه نصب کرد.
persian.DriveChoose=برای ادامه یک درایو انتخاب کنید.
persian.TaskbarHint=نکته: برای سنجاق کردن LinguaNova به نوار وظیفه، آن را باز کنید، روی نماد آن در نوار وظیفه راست‌کلیک کنید و «Pin to taskbar» را انتخاب کنید.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; AppUserModelID: "{#MyAppUserModelID}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon; AppUserModelID: "{#MyAppUserModelID}"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
; Automatic update: reopen LinguaNova after a silent install.
Filename: "{app}\{#MyAppExe}"; Flags: nowait; Check: IsAutoUpdate

[UninstallDelete]
Type: files; Name: "{app}\linguanova_installed.json"

[Code]
const
  DRIVE_FIXED = 3;
  MinFreeMB = 1024;

var
  DrivePage: TInputOptionWizardPage;
  DriveLetters: String;   { letter of each option, same order as the list }

function GetDriveType(lpRootPathName: String): Cardinal;
  external 'GetDriveTypeW@kernel32.dll stdcall';

function IsAutoUpdate: Boolean;
begin
  Result := Pos('/LNUPDATE', Uppercase(GetCmdTail)) > 0;
end;

function WqlEscape(const S: String): String;
begin
  Result := S;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '''', '\''', True);
end;

{ Drive letters that belong to disks connected by USB. Win32_DiskDrive covers
  most USB drives; MSFT_Disk (BusType 7 = USB) also covers UAS enclosures that
  report "SCSI". Any WMI error leaves the list as it is: the drive type check
  still excludes removable and network drives. }
function UsbDriveLetters: String;
var
  Locator, Svc, Disks, Disk, Parts, Part, Logicals, Logical, Storage, UsbDisks, Partitions, P: Variant;
  I, J, K: Integer;
  UsbNumbers: String;
  Letter: Integer;
begin
  Result := '';
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Svc := Locator.ConnectServer('.', 'root\CIMV2');
    Disks := Svc.ExecQuery('SELECT DeviceID FROM Win32_DiskDrive WHERE InterfaceType = ''USB''');
    for I := 0 to Disks.Count - 1 do
    begin
      Disk := Disks.ItemIndex(I);
      Parts := Svc.ExecQuery('ASSOCIATORS OF {Win32_DiskDrive.DeviceID=''' + WqlEscape(Disk.DeviceID) +
        '''} WHERE AssocClass = Win32_DiskDriveToDiskPartition');
      for J := 0 to Parts.Count - 1 do
      begin
        Part := Parts.ItemIndex(J);
        Logicals := Svc.ExecQuery('ASSOCIATORS OF {Win32_DiskPartition.DeviceID=''' + WqlEscape(Part.DeviceID) +
          '''} WHERE AssocClass = Win32_LogicalDiskToPartition');
        for K := 0 to Logicals.Count - 1 do
        begin
          Logical := Logicals.ItemIndex(K);
          Result := Result + Uppercase(Copy(Logical.DeviceID, 1, 1));
        end;
      end;
    end;
  except
    Log('USB detection (Win32_DiskDrive) failed: ' + GetExceptionMessage);
  end;

  try
    Storage := Locator.ConnectServer('.', 'root\Microsoft\Windows\Storage');
    UsbDisks := Storage.ExecQuery('SELECT Number FROM MSFT_Disk WHERE BusType = 7');
    UsbNumbers := ',';
    for I := 0 to UsbDisks.Count - 1 do
      UsbNumbers := UsbNumbers + IntToStr(UsbDisks.ItemIndex(I).Number) + ',';
    if UsbNumbers <> ',' then
    begin
      Partitions := Storage.ExecQuery('SELECT DiskNumber, DriveLetter FROM MSFT_Partition');
      for I := 0 to Partitions.Count - 1 do
      begin
        P := Partitions.ItemIndex(I);
        if Pos(',' + IntToStr(P.DiskNumber) + ',', UsbNumbers) > 0 then
        begin
          Letter := P.DriveLetter;
          if Letter > 0 then
            Result := Result + Uppercase(Chr(Letter));
        end;
      end;
    end;
  except
    Log('USB detection (MSFT_Disk) failed: ' + GetExceptionMessage);
  end;
end;

function FreeGB(const Root: String; var EnoughSpace: Boolean): String;
var
  Free, Total: Int64;
begin
  Result := '?';
  EnoughSpace := True;
  if GetSpaceOnDisk64(Root, Free, Total) then
  begin
    EnoughSpace := (Free div (1024 * 1024)) >= MinFreeMB;
    Result := IntToStr(Free div (1024 * 1024 * 1024));
  end;
end;

procedure BuildDriveList;
var
  N: Integer;
  C: String;
  Root, Usb, Item, SystemLetter, GB: String;
  Enough: Boolean;
  Index, SelectIndex: Integer;
begin
  Usb := UsbDriveLetters;
  Log('USB drive letters: ' + Usb);
  SystemLetter := Uppercase(Copy(ExpandConstant('{sd}'), 1, 1));
  DriveLetters := '';
  SelectIndex := -1;
  for N := Ord('A') to Ord('Z') do
  begin
    C := Chr(N);
    Root := C + ':\';
    if GetDriveType(Root) <> DRIVE_FIXED then
      continue;
    if Pos(C, Usb) > 0 then
      continue;
    GB := FreeGB(Root, Enough);
    if Enough then
      Item := FmtMessage(CustomMessage('DriveItem'), [C + ':', GB])
    else
      Item := FmtMessage(CustomMessage('DriveItemLow'), [C + ':']);
    if C = SystemLetter then
      Item := Item + '   ' + CustomMessage('DriveWindows');
    Index := DrivePage.Add(Item);
    DriveLetters := DriveLetters + C;
    if not Enough then
      DrivePage.CheckListBox.ItemEnabled[Index] := False
    else if (SelectIndex < 0) or (C = SystemLetter) then
      SelectIndex := Index;
  end;
  if SelectIndex >= 0 then
    DrivePage.SelectedValueIndex := SelectIndex;
end;

procedure InitializeWizard;
begin
  DrivePage := CreateInputOptionPage(wpWelcome,
    CustomMessage('DriveTitle'), CustomMessage('DriveDescription'),
    CustomMessage('DriveSubCaption'), True, True);
  BuildDriveList;
end;

function IsUpgrade: Boolean;
begin
  Result := WizardForm.PrevAppDir <> '';
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { An update keeps the folder of the existing installation. }
  Result := (PageID = DrivePage.ID) and IsUpgrade;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Index: Integer;
begin
  Result := True;
  if CurPageID = DrivePage.ID then
  begin
    if DriveLetters = '' then
    begin
      MsgBox(CustomMessage('DriveNone'), mbError, MB_OK);
      Result := False;
      exit;
    end;
    Index := DrivePage.SelectedValueIndex;
    if (Index < 0) or not DrivePage.CheckListBox.ItemEnabled[Index] then
    begin
      MsgBox(CustomMessage('DriveChoose'), mbInformation, MB_OK);
      Result := False;
      exit;
    end;
    WizardForm.DirEdit.Text := Copy(DriveLetters, Index + 1, 1) + ':\LinguaNova';
  end;
end;

function UiLanguageCode: String;
var
  L: String;
begin
  L := ActiveLanguage;
  if L = 'spanish' then Result := 'es'
  else if L = 'german' then Result := 'de'
  else if L = 'french' then Result := 'fr'
  else if L = 'japanese' then Result := 'ja'
  else if L = 'russian' then Result := 'ru'
  else if L = 'turkish' then Result := 'tr'
  else if L = 'chinesesimplified' then Result := 'zh-CN'
  else if L = 'persian' then Result := 'fa'
  else Result := 'en';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Lines: TArrayOfString;
begin
  if CurStep = ssPostInstall then
  begin
    { Read by LinguaNova: marks an installed build (automatic updates) and
      gives the first-run interface language. }
    SetArrayLength(Lines, 5);
    Lines[0] := '{';
    Lines[1] := '  "installed_by": "LinguaNova installer",';
    Lines[2] := '  "version": "{#MyAppVersion}",';
    Lines[3] := '  "installer_language": "' + UiLanguageCode + '"';
    Lines[4] := '}';
    if not SaveStringsToUTF8File(ExpandConstant('{app}\linguanova_installed.json'), Lines, False) then
      Log('Could not write linguanova_installed.json');
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 + CustomMessage('TaskbarHint');
    WizardForm.AdjustLabelHeight(WizardForm.FinishedLabel);
    WizardForm.RunList.Top := WizardForm.FinishedLabel.Top + WizardForm.FinishedLabel.Height + ScaleY(12);
  end;
end;
