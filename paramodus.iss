; paramodus.iss — Inno Setup script for Paramodus
; ============================================================================
; Produces a single ParamodusSetup.exe installer that:
;   - Installs the full dist/Paramodus/ folder to Program Files
;   - Creates a Desktop shortcut and Start Menu entry
;   - Registers an uninstaller in Windows Settings
;   - Runs silently with no extra prompts for the end user
;
; Prerequisites:
;   1. Build the app first:  python build.py
;   2. Install Inno Setup 6: https://jrsoftware.org/isdl.php
;   3. Open this file in Inno Setup Compiler and press F9
;      OR run from CLI:  iscc paramodus.iss
;
; Output: installer\ParamodusSetup.exe
; ============================================================================

#define AppName        "Paramodus"
#define AppVersion     "1.0"
#define AppPublisher   "Centrale73"
#define AppURL         "https://github.com/Centrale73/Paramodus"
#define AppExeName     "Paramodus.exe"
#define DistDir        "dist\Paramodus"

[Setup]
AppId={{A3F2B1C4-7E8D-4F9A-B0C2-D3E4F5A6B7C8}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Output: a single installer exe in installer\
OutputDir=installer
OutputBaseFilename=ParamodusSetup
; LZMA solid compression — significantly reduces installer size
Compression=lzma2/ultra64
SolidCompression=yes
; Require 64-bit Windows (Bonsai + llama-server are 64-bit)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Desktop icon task shown during install
WizardStyle=modern
DisableProgramGroupPage=yes
; The installer does NOT require admin rights — installs per-user by default
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupName: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Bundle the entire dist\Paramodus\ folder, including _internal\ (DLLs, GGUF, Python libs)
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: The Bonsai-8B.gguf (~1.15 GB) is inside _internal\models\ and is included above.

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";       Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (only if user checked the task)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch Paramodus after installation completes
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up the app data folder that Paramodus creates at runtime
; (chat history, vector DB, downloaded models) — only if user wants
; We do NOT auto-delete user data; they can remove ~/.myapp manually
Type: dirifempty; Name: "{app}"
