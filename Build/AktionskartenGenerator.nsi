; AktionskartenGenerator - Installer (NSIS 3, 64 Bit, fuer alle Benutzer)
; Abgeleitet aus der Installer-Vorlage (AktionskartenGenerator.nsi): gleiche Seiten,
; gleiches dunkles Design. Weggelassen: mitgelieferte Hilfsprogramme und die
; Firewall-Freigabe (dieses Programm oeffnet keinen Port). Dazu: Info.txt
; im Programmordner und das Entfernen des Cache-Ordners bei der Deinstallation.
;
; Bauen:  makensis -DVERSION=2.9 -DDIST=<Ordner aus PyInstaller> Build/AktionskartenGenerator.nsi
;   (build_wine.sh liest die Version aus APP_VERSION in App/AktionskartenGenerator.py)
;   erwartet dist/AktionskartenGenerator aus PyInstaller (Build/AktionskartenGenerator.spec).
;   Ergebnis: Installer/AktionskartenGenerator_2_9_win_amd64.exe - "_" statt ".", Zielsystem im Namen
;
; Vor dem Schreiben/Loeschen: laeuft AktionskartenGenerator, bricht das Setup mit
; Hinweis ab. Eine vorhandene alte Version wird KOMPLETT entfernt (ihr eigener
; Deinstaller laeuft still durch), bevor die neue geschrieben wird.
;
; Installiert nach "C:\Program Files\AktionskartenGenerator" (Adminrechte), legt
; auf Wunsch Startmenue- und Desktop-Verknuepfung fuer alle Benutzer an
; (eigene Seite mit zwei Haken, Vorgabe Startmenue an / Desktop aus; still mit /S
; gelten die Vorgaben) und traegt sich in "Apps & Features" ein. Zum Schluss eine
; eigene dunkle Seite "Fertig" mit dem Knopf "Starten": schliesst das Setup und
; startet das Programm - ueber explorer.exe, damit es ohne die Adminrechte des
; Setups laeuft. Das Programm hat keinen Datenordner. Die Deinstallation entfernt
; ausser den eigenen Dateien den Cache-Ordner des Programms im Profil des
; angemeldeten Benutzers (Ansage 15.11.2026); Reste aelterer, kopierter Versionen
; im selben Ordner bleiben unberuehrt.

Unicode true
Target amd64-unicode
SetCompressor /SOLID lzma
SetCompressorDictSize 64

!define APPNAME "AktionskartenGenerator"
!ifndef VERSION
  !error "VERSION fehlt - makensis -DVERSION=1.0 (Wert aus APP_VERSION)"
!endif
!searchreplace VERSION_FILE "${VERSION}" "." "_"   ; 1.0 -> 1_0 fuer den Dateinamen
!define EXENAME "AktionskartenGenerator.exe"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
!ifndef DIST
  !define DIST "../dist/AktionskartenGenerator"
!endif
!ifndef PROJEKT
  !define PROJEKT ".."            ; Projektordner: Icon und Info
!endif
!ifndef OUTFILE
  !define OUTFILE "../Installer/AktionskartenGenerator_${VERSION_FILE}_win_amd64.exe"
!endif

Name "${APPNAME}"
OutFile "${OUTFILE}"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${APPNAME}" "InstallDir"
RequestExecutionLevel admin
ShowInstDetails show
ShowUninstDetails show
BrandingText " "

!include "MUI2.nsh"
!include "nsDialogs.nsh"

; ---- Verknuepfungen: Wahl des Nutzers (Vorgabe Startmenue an, Desktop aus) --
Var WahlStartmenue      ; ${BST_CHECKED} / ${BST_UNCHECKED}
Var WahlDesktop
Var HakenStartmenue     ; Fenstergriffe der beiden Haken auf der Seite
Var HakenDesktop
Var InstallOk           ; 1 = Section komplett durchgelaufen (Seite "Fertig")
Var KnopfStarten

Function .onInit
  StrCpy $WahlStartmenue ${BST_CHECKED}
  StrCpy $WahlDesktop ${BST_UNCHECKED}
  StrCpy $InstallOk 0
FunctionEnd

; ---- dunkles Design (Palette wie theme.py) --------------------------------
!define C_BG      "16181D"
!define C_SURFACE "1B1E24"
!define C_TEXT    "D7DAE0"
!define C_MUTED   "AAB2BF"

!define MUI_ICON "${PROJEKT}/Icon/AktionskartenGenerator_Icon.ico"
!define MUI_UNICON "${PROJEKT}/Icon/AktionskartenGenerator_Icon.ico"
!define MUI_BGCOLOR "${C_SURFACE}"                 ; Kopfzeile
!define MUI_TEXTCOLOR "${C_TEXT}"
!define MUI_INSTFILESPAGE_COLORS "${C_TEXT} ${C_BG}" ; Detailliste
!define MUI_CUSTOMFUNCTION_GUIINIT DarkOuter
!define MUI_CUSTOMFUNCTION_UNGUIINIT un.DarkOuter

!macro DARK_BUTTON PARENT ID
  GetDlgItem $0 ${PARENT} ${ID}
  SetCtlColors $0 ${C_TEXT} ${C_BG}
  System::Call 'uxtheme::SetWindowTheme(p r0, w "DarkMode_Explorer", p 0)'
!macroend

; Haken: mit Windows-Theme bleibt die Beschriftung schwarz (das Theme malt
; den Text selbst, SetCtlColors greift nicht). Deshalb das Theme abschalten -
; klassischer Haken (weisses Kaestchen) mit heller Schrift auf dunklem Grund.
!macro DARK_CHECKBOX HWND
  System::Call 'uxtheme::SetWindowTheme(p ${HWND}, w " ", w " ")'
  SetCtlColors ${HWND} ${C_TEXT} ${C_BG}
!macroend

; Rahmenfenster: Titelleiste, Hintergrund, Knoepfe, Branding-Zeile
; Innerer Dialog jeder Seite: alle Elemente dunkel. Den Gruppenrahmen
; ("Zielverzeichnis") ausblenden - seine Beschriftung laesst sich nicht
; zuverlaessig dunkel faerben.
!macro DARK_FUNCS UN
Function ${UN}DarkOuter
  System::Call 'dwmapi::DwmSetWindowAttribute(p $HWNDPARENT, i 20, *i 1, i 4)'
  SetCtlColors $HWNDPARENT ${C_TEXT} ${C_BG}
  !insertmacro DARK_BUTTON $HWNDPARENT 1
  !insertmacro DARK_BUTTON $HWNDPARENT 2
  !insertmacro DARK_BUTTON $HWNDPARENT 3
  GetDlgItem $0 $HWNDPARENT 1028
  SetCtlColors $0 /BRANDING ${C_MUTED} ${C_BG}
  GetDlgItem $0 $HWNDPARENT 1256
  SetCtlColors $0 /BRANDING ${C_MUTED} ${C_BG}
FunctionEnd

Function ${UN}DarkInner
  FindWindow $R0 "#32770" "" $HWNDPARENT
  SetCtlColors $R0 ${C_TEXT} ${C_BG}
  StrCpy $R1 0
  next:
    FindWindow $R1 "" "" $R0 $R1
    StrCmp $R1 0 done
    SetCtlColors $R1 ${C_TEXT} ${C_BG}
    System::Call 'user32::GetClassNameW(p R1, w .R2, i 64)'
    System::Call 'user32::GetWindowLongW(p R1, i -16) i .R3'
    IntOp $R3 $R3 & 0xF
    StrCmp $R2 "Button" 0 themed
    IntCmp $R3 7 0 themed themed
      ShowWindow $R1 0
      Goto next
    themed:
      System::Call 'uxtheme::SetWindowTheme(p R1, w "DarkMode_Explorer", p 0)'
    Goto next
  done:
FunctionEnd
!macroend
!insertmacro DARK_FUNCS ""
!insertmacro DARK_FUNCS "un."

; ---- Seite "Verknuepfungen" (Ansage 09.10.2026, gebaut fuer 1.6) ------------
; Zwei Haken: Startmenue (Vorgabe an), Desktop (Vorgabe aus). Die Wahl steht
; in $WahlStartmenue/$WahlDesktop; still (/S) wird die Seite nicht gezeigt,
; dann gelten die Vorgaben aus .onInit.
Function VerknuepfungenErstellen
  !insertmacro MUI_HEADER_TEXT "Verknüpfungen" "Wo soll AktionskartenGenerator erreichbar sein?"
  nsDialogs::Create 1018
  Pop $0
  StrCmp $0 error 0 +2
    Abort
  SetCtlColors $0 ${C_TEXT} ${C_BG}

  ${NSD_CreateLabel} 0 0 100% 24u "Verknüpfungen für alle Benutzer anlegen:"
  Pop $1
  SetCtlColors $1 ${C_TEXT} ${C_BG}

  ${NSD_CreateCheckbox} 0 30u 100% 12u "Startmenü"
  Pop $HakenStartmenue
  !insertmacro DARK_CHECKBOX $HakenStartmenue
  ${NSD_SetState} $HakenStartmenue $WahlStartmenue

  ${NSD_CreateCheckbox} 0 48u 100% 12u "Desktop"
  Pop $HakenDesktop
  !insertmacro DARK_CHECKBOX $HakenDesktop
  ${NSD_SetState} $HakenDesktop $WahlDesktop

  nsDialogs::Show
FunctionEnd

Function VerknuepfungenVerlassen
  ${NSD_GetState} $HakenStartmenue $WahlStartmenue
  ${NSD_GetState} $HakenDesktop $WahlDesktop
FunctionEnd

; ---- Seite "Fertig" mit Knopf "Starten" (Ansage 21.10.2026, gebaut fuer 1.7)
; Die MUI-Abschlussseite bleibt aus (hell). Diese Seite ist dunkel wie die
; anderen: Hinweis + Knopf "Starten"; unten steht NSIS' "Beenden". Nach einem
; Abbruch in der Section (InstallOk bleibt 0) wird die Seite uebersprungen.
Function FertigErstellen
  StrCmp $InstallOk 1 +2
    Abort
  !insertmacro MUI_HEADER_TEXT "Fertig" "AktionskartenGenerator ${VERSION} ist installiert."
  nsDialogs::Create 1018
  Pop $0
  StrCmp $0 error 0 +2
    Abort
  SetCtlColors $0 ${C_TEXT} ${C_BG}

  ${NSD_CreateLabel} 0 0 100% 36u "Die Installation ist abgeschlossen.$\r$\n$\r$\n„Starten“ beendet das Setup und startet AktionskartenGenerator, „Beenden“ schließt nur das Setup."
  Pop $1
  SetCtlColors $1 ${C_TEXT} ${C_BG}

  ${NSD_CreateButton} 0 48u 90u 16u "Starten"
  Pop $KnopfStarten
  SetCtlColors $KnopfStarten ${C_TEXT} ${C_BG}
  System::Call 'uxtheme::SetWindowTheme(p $KnopfStarten, w "DarkMode_Explorer", p 0)'
  ${NSD_OnClick} $KnopfStarten StartenKlick

  nsDialogs::Show
FunctionEnd

Function StartenKlick
  ; Ueber explorer.exe starten: das Setup laeuft mit Adminrechten, das
  ; Programm soll als normaler Benutzer laufen (sonst laege der Cache-Ordner
  ; u. U. im Profil eines anderen Kontos). Bekannter Umweg -
  ; die Explorer-Shell startet die exe im Benutzerkontext.
  Exec '"$WINDIR\explorer.exe" "$INSTDIR\${EXENAME}"'
  ; dann wie ein Klick auf "Schliessen" (Knopf 1 des Rahmenfensters) - so
  ; endet das Setup auf dem normalen Weg
  SendMessage $HWNDPARENT ${WM_COMMAND} 1 0
FunctionEnd

!define MUI_PAGE_CUSTOMFUNCTION_SHOW DarkInner
!insertmacro MUI_PAGE_DIRECTORY
Page custom VerknuepfungenErstellen VerknuepfungenVerlassen
!define MUI_PAGE_CUSTOMFUNCTION_SHOW DarkInner
!insertmacro MUI_PAGE_INSTFILES
Page custom FertigErstellen

!define MUI_PAGE_CUSTOMFUNCTION_SHOW un.DarkInner
!insertmacro MUI_UNPAGE_CONFIRM
!define MUI_PAGE_CUSTOMFUNCTION_SHOW un.DarkInner
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "German"

; ---- vor dem Schreiben/Loeschen pruefen -----------------------------------
; Laeuft das Programm noch? Test: die exe zum Schreiben oeffnen. Eine laufende
; exe laesst sich nicht oeffnen - dann lieber sauber abbrechen als halb
; ueberschreiben.
!macro PREPARE UN
Function ${UN}PrepareFiles
  IfFileExists "$INSTDIR\${EXENAME}" 0 fertig
    ClearErrors
    FileOpen $0 "$INSTDIR\${EXENAME}" a
    IfErrors programm_laeuft
    FileClose $0
    Goto fertig

  programm_laeuft:
    ClearErrors
    DetailPrint "AktionskartenGenerator läuft noch - abgebrochen."
    Abort "AktionskartenGenerator läuft noch. Bitte beenden und das Setup neu starten."
  fertig:
FunctionEnd
!macroend
!insertmacro PREPARE ""
!insertmacro PREPARE "un."

Section "AktionskartenGenerator"
  SetShellVarContext all
  Call PrepareFiles

  ; -- alte Version zuerst entfernen ----------------------------------------
  ; Eine fruehere Installation in einem ANDEREN Ordner (Pfad aus der Registry)
  ReadRegStr $R5 HKLM "Software\${APPNAME}" "InstallDir"
  StrCmp $R5 "" anderer_fertig
  StrCmp $R5 "$INSTDIR" anderer_fertig
  IfFileExists "$R5\Uninstall.exe" 0 anderer_fertig
    DetailPrint "Alte Installation in $R5 wird entfernt ..."
    ExecWait '"$R5\Uninstall.exe" /S _?=$R5'
    Delete "$R5\Uninstall.exe"
    RMDir "$R5"
  anderer_fertig:

  ; Die Installation im Zielordner: ihr eigener Deinstaller raeumt Dateien,
  ; Verknuepfungen und Registry weg. "_?=" laesst ihn im Ordner
  ; laufen, damit ExecWait wirklich wartet - dafuer bleibt die Uninstall.exe
  ; stehen und wird hier geloescht.
  IfFileExists "$INSTDIR\Uninstall.exe" 0 kein_alter
    DetailPrint "Alte Version wird entfernt ..."
    ExecWait '"$INSTDIR\Uninstall.exe" /S _?=$INSTDIR'
    Delete "$INSTDIR\Uninstall.exe"
    Sleep 500
  kein_alter:
  ; Reste einer aelteren Installation ohne Deinstaller
  RMDir /r "$INSTDIR\_internal"

  SetOutPath "$INSTDIR"
  File /r "${DIST}/*"
  File "/oname=Info.txt" "${PROJEKT}/Info_Win.txt"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Verknuepfungen nur nach Wahl (Seite "Verknuepfungen"; still: Vorgaben).
  ; Die alte Version hat ihre Verknuepfungen eben selbst entfernt - was hier
  ; nicht angehakt ist, gibt es danach also nicht mehr.
  ${If} $WahlStartmenue == ${BST_CHECKED}
    CreateShortcut "$SMPROGRAMS\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
    DetailPrint "Startmenü-Verknüpfung angelegt."
  ${EndIf}
  ${If} $WahlDesktop == ${BST_CHECKED}
    CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
    DetailPrint "Desktop-Verknüpfung angelegt."
  ${EndIf}

  WriteRegStr HKLM "Software\${APPNAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${EXENAME}"
  WriteRegStr HKLM "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "${UNINSTKEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoRepair" 1
  SectionGetSize 0 $0                     ; Groesse in KB, beim Bauen berechnet
  WriteRegDWORD HKLM "${UNINSTKEY}" "EstimatedSize" "$0"

  StrCpy $InstallOk 1
SectionEnd

Section "Uninstall"
  SetShellVarContext all
  Call un.PrepareFiles

  Delete "$SMPROGRAMS\${APPNAME}.lnk"
  Delete "$DESKTOP\${APPNAME}.lnk"

  ; nur die eigenen Dateien entfernen - nie den ganzen Ordner blind loeschen
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\${EXENAME}"
  Delete "$INSTDIR\Info.txt"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKLM "${UNINSTKEY}"
  DeleteRegKey HKLM "Software\${APPNAME}"

  ; Cache-Ordner des Programms im Profil des angemeldeten Benutzers (Rasterkacheln,
  ; Zwischenspeicher von Qt). Nur diese beiden Unterordner; der Ordner selbst nur,
  ; wenn er danach leer ist - ein "venv" aelterer, kopierter Versionen bleibt.
  SetShellVarContext current
  RMDir /r "$LOCALAPPDATA\${APPNAME}\cache"
  RMDir /r "$LOCALAPPDATA\${APPNAME}\QtWebEngine"
  RMDir "$LOCALAPPDATA\${APPNAME}"
SectionEnd
