; Ableton Brain Installer - NSIS Custom Script
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; Custom pages
!define MUI_CUSTOMFUNCTION_PREINSTALL preInstall
!define MUI_CUSTOMFUNCTION_POSTINSTALL postInstall

; Modern UI
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN ""
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

; Uninstall pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language
!insertmacro MUI_LANGUAGE "English"

; Functions
Function preInstall
  ; Set default install directory
  StrCpy $INSTDIR "$LOCALAPPDATA\AbletonBrain"
FunctionEnd

Function postInstall
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\Ableton Brain"
  CreateShortCut "$SMPROGRAMS\Ableton Brain\Ableton Brain Installer.lnk" "$INSTDIR\Ableton Brain Installer.exe"
  CreateShortCut "$DESKTOP\Ableton Brain Installer.lnk" "$INSTDIR\Ableton Brain Installer.exe"
  
  ; Add to PATH (optional)
  ; System::Call 'kernel32::SetEnvironmentVariable(t "PATH", t "$INSTDIR")'
FunctionEnd

; Custom uninstall
Section "Uninstall"
  ; Remove shortcuts
  Delete "$SMPROGRAMS\Ableton Brain\*.lnk"
  RMDir "$SMPROGRAMS\Ableton Brain"
  Delete "$DESKTOP\Ableton Brain Installer.lnk"
  
  ; Remove installed files
  RMDir /r "$INSTDIR"
SectionEnd