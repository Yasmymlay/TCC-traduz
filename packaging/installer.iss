; Instalador do Tradutor de Aulas (Inno Setup 6). Gerado por packaging\build.ps1.
; Instala na pasta do usuário, sem pedir permissão de administrador.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6F2B8C1E-3A47-4B8E-9C2D-5E1A7D3B9F40}
AppName=Tradutor de Aulas
AppVersion={#AppVersion}
AppPublisher=TraduzEdu (TCC)
DefaultDirName={localappdata}\Programs\Tradutor de Aulas
DefaultGroupName=Tradutor de Aulas
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputBaseFilename=TradutorDeAulas-Setup-{#AppVersion}
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\TradutorDeAulas.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Tradutor de Aulas"; Filename: "{app}\TradutorDeAulas.exe"
Name: "{group}\Desinstalar Tradutor de Aulas"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Tradutor de Aulas"; Filename: "{app}\TradutorDeAulas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TradutorDeAulas.exe"; Description: "Abrir o Tradutor de Aulas agora"; Flags: nowait postinstall skipifsilent
