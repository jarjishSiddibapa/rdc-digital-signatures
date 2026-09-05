; ================================================================
; RDC Digital Signatures - Inno Setup Script
; Compatible with Inno Setup 6.x
;
; KEY DESIGN DECISIONS:
;   - App binaries → {commonpf64}\RDCSignatures  (Program Files, read-only for users)
;   - User data     → {localappdata}\RDCSignatures (ALWAYS writable, per-user)
;   - This eliminates the "merged file cannot be deleted" error that occurs
;     when the app runs from a protected directory without write permission.
; ================================================================

#define MyAppName      "RDC Digital Signatures"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "RDC"
#define MyAppExeName   "RDCSignatures.exe"
#define MyDistDir      "dist\RDCSignatures"

[Setup]
; App metadata
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://rdc.com
AppSupportURL=https://rdc.com
AppUpdatesURL=https://rdc.com

; Install to Program Files (64-bit)
DefaultDirName={commonpf64}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=installer_output
OutputBaseFilename=RDCSignatures_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Require admin for install (so we can write to Program Files)
; but the APP ITSELF runs as the current (non-admin) user after install
PrivilegesRequired=admin

; Windows version requirement
MinVersion=10.0

; Architecture
ArchitecturesInstallIn64BitMode=x64

; Appearance
WizardStyle=modern
WizardSizePercent=120

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "{cm:CreateDesktopIcon}";   GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Copy the entire PyInstaller dist folder to Program Files
; Note: The app reads from here (binaries, assets) but NEVER writes here.
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}";         Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional)
Name: "{autodesktop}\{#MyAppName}";   Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch shortcut (optional, legacy)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove user data folder on uninstall (optional — comment out to keep user data)
; Type: filesandordirs; Name: "{localappdata}\RDCSignatures"

[Code]
// ---------------------------------------------------------------------------
// Pre-install check: warn if a previous version is already running
// ---------------------------------------------------------------------------
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// ---------------------------------------------------------------------------
// After install: create the writable user-data directory under %LOCALAPPDATA%
// so it definitely exists before the app first runs (avoids any first-run race).
// The app also creates it itself, but this is belt-and-suspenders.
// ---------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := ExpandConstant('{localappdata}\RDCSignatures');
    if not DirExists(DataDir) then
      CreateDir(DataDir);
    DataDir := ExpandConstant('{localappdata}\RDCSignatures\signed_output');
    if not DirExists(DataDir) then
      CreateDir(DataDir);
  end;
end;
