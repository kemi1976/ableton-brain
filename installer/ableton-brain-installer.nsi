; Ableton Brain Installer - NSIS Script
!include "MUI2.nsh"

; General
Name "Ableton Brain"
OutFile "Ableton-Brain-Installer.exe"
InstallDir "$PROGRAMFILES64\Ableton Brain"
InstallDirRegKey HKLM "Software\Ableton Brain" "Install_Dir"
RequestExecutionLevel admin

; Modern UI
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Files
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "dist\win-unpacked\*"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Registry
    WriteRegStr HKLM "Software\Ableton Brain" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "DisplayName" "Ableton Brain"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "DisplayIcon" "$INSTDIR\Ableton Brain Installer.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "DisplayVersion" "1.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "Publisher" "KEMERTARIAN"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "NoModify" "1"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain" \
        "NoRepair" "1"
    
    ; Start Menu
    CreateDirectory "$SMPROGRAMS\Ableton Brain"
    CreateShortCut "$SMPROGRAMS\Ableton Brain\Ableton Brain.lnk" \
        "$INSTDIR\Ableton Brain Installer.exe"
    CreateShortCut "$SMPROGRAMS\Ableton Brain\Uninstall.lnk" \
        "$INSTDIR\Uninstall.exe"
    
    ; Desktop shortcut
    CreateShortCut "$DESKTOP\Ableton Brain.lnk" \
        "$INSTDIR\Ableton Brain Installer.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\*.*"
    RMDir /r "$INSTDIR"
    
    Delete "$SMPROGRAMS\Ableton Brain\*.*"
    RMDir "$SMPROGRAMS\Ableton Brain"
    
    Delete "$DESKTOP\Ableton Brain.lnk"
    
    DeleteRegKey HKLM "Software\Ableton Brain"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AbletonBrain"
SectionEnd