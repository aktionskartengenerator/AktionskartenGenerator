#!/usr/bin/env bash
# Baut den Windows-Installer von AktionskartenGenerator unter Linux mit Wine.
#
# Einmalig je Sitzung:  apt-get install -y wine64 wine nsis gcc-mingw-w64-x86-64 xvfb
# Aufruf aus einer Kopie des Projektordners auf der Linux-Seite (nicht im verbundenen Ordner):
#     bash Build/build_wine.sh <python-laufzeit.zip>
#
# <python-laufzeit.zip> ist der Python-Installationsordner des Windows-PCs als Zip, ohne
# Lib\site-packages (python.org ist aus der Cloud nicht erreichbar). pip kommt über ensurepip
# aus der Laufzeit selbst, die Windows-Pakete kommen von PyPI.
# Ergebnis: Installer/AktionskartenGenerator_<Version mit _>_win_amd64.exe
set -euo pipefail
cd "$(dirname "$0")/.."
PROJEKT="$(pwd)"
APP="AktionskartenGenerator"
LAUFZEIT="${1:?Aufruf: bash Build/build_wine.sh <python-laufzeit.zip>}"
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"$/\1/p' "App/$APP.py")"
[ -n "$VERSION" ] || { echo "APP_VERSION nicht gefunden"; exit 1; }
BAU="$PROJEKT/Build/_temp/wine"
export WINEPREFIX="$BAU/prefix" WINEDEBUG=-all WINEARCH=win64
C="$WINEPREFIX/drive_c"
PY='C:\Python\python.exe'
# Ausgabe von Wine nie in eine Datei umleiten, nur durch cat schicken.
wein() { xvfb-run -a wine "$@" 2>&1 | cat | grep -v "X connection\|XIO:\|after [0-9]* requests" || true; }

mkdir -p "$BAU" "$PROJEKT/Installer"
[ -d "$C" ] || wein wineboot -i

# 1. Python-Laufzeit. Die Namen im Zip tragen Backslashes, deshalb mit Python entpacken.
if [ ! -f "$C/Python/python.exe" ]; then
    python3 - "$LAUFZEIT" "$C/Python" <<'PY'
import os, sys, zipfile
quelle, ziel = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(quelle) as z:
    for eintrag in z.infolist():
        name = eintrag.filename.replace("\\", "/")
        if name.endswith("/") or name.startswith(("Scripts/", "share/", "include/", "libs/")):
            continue
        pfad = os.path.join(ziel, name)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "wb") as f:
            f.write(z.read(eintrag))
os.makedirs(os.path.join(ziel, "Lib", "site-packages"), exist_ok=True)
# Wine kennt KERNEL32.CopyFile2 nicht; ohne den Eintrag nimmt shutil den normalen Weg.
with open(os.path.join(ziel, "Lib", "sitecustomize.py"), "w") as f:
    f.write("try:\n    import _winapi\n    if hasattr(_winapi, 'CopyFile2'):\n        del _winapi.CopyFile2\nexcept Exception:\n    pass\n")
PY
fi

# 2. Qt6Core.dll verlangt icuuc.dll. Windows 10/11 bringt sie mit, Wine nicht: ein Platzhalter
#    mit genau den verlangten Funktionen kommt nach system32 des Prefix (nicht ins Paket).
if [ ! -f "$C/windows/system32/icuuc.dll" ]; then
    {
        echo '#include <stddef.h>'
        for f in ucnv_open ucnv_close UCNV_FROM_U_CALLBACK_SUBSTITUTE UCNV_TO_U_CALLBACK_SUBSTITUTE ucnv_reset \
                 ucnv_getMaxCharSize ucnv_getName ucnv_getToUCallBack ucnv_getFromUCallBack ucnv_setToUCallBack \
                 ucnv_setFromUCallBack ucnv_cbToUWriteUChars ucnv_toUnicode ucnv_cbFromUWriteUChars \
                 ucnv_toUCountPending ucnv_fromUCountPending ucnv_getStandardName ucnv_getAvailableName \
                 ucnv_countAvailable ucnv_fromUnicode; do
            echo "__declspec(dllexport) void* $f(void* a, void* b, void* c, void* d, void* e, void* f, void* g, void* h) { return NULL; }"
        done
    } > "$BAU/icuuc_stub.c"
    x86_64-w64-mingw32-gcc -shared -o "$C/windows/system32/icuuc.dll" "$BAU/icuuc_stub.c"
fi

# 3. Windows-Pakete von PyPI holen und ohne Netz in die Laufzeit installieren.
if [ ! -d "$C/Python/Lib/site-packages/PyInstaller" ]; then
    mkdir -p "$C/wheels"
    python3 -m pip download --only-binary=:all: --platform win_amd64 --python-version 3.12 --implementation cp \
        -d "$C/wheels" -r App/requirements.txt pyinstaller pyinstaller-hooks-contrib pywin32-ctypes pefile altgraph packaging setuptools
    wein "$PY" -m ensurepip
    wein "$PY" -m pip install --no-index --find-links 'C:\wheels' -r 'Z:'"$(echo "$PROJEKT/App/requirements.txt" | tr / '\\')" pyinstaller
fi

# 4. Programm packen. Gebaut wird in einer Kopie auf Laufwerk C: des Prefix.
rm -rf "$C/proj"
mkdir -p "$C/proj"
tar cf - --exclude=Build/_temp --exclude=__pycache__ App Build Icon | tar xf - -C "$C/proj"
( cd "$C/proj" && wein "$PY" -m PyInstaller --noconfirm --distpath 'C:\proj\dist' --workpath 'C:\proj\work' 'Build\AktionskartenGenerator.spec' | tail -2 )
[ -f "$C/proj/dist/$APP/$APP.exe" ] || { echo "PyInstaller hat keine exe erzeugt"; exit 1; }
! find "$C/proj/dist" -iname 'icuuc*' | grep -q . || { echo "Platzhalter icuuc.dll ist im Paket gelandet"; exit 1; }

# 5. Lizenztexte fuer das Paket zusammenstellen.
LIZ="$BAU/Lizenzen"
rm -rf "$LIZ"; mkdir -p "$LIZ"
cp LICENSE "$LIZ/LICENSE.txt"
cp THIRD-PARTY-NOTICES.md Lizenzen/* "$LIZ/"
cp App/maplibre/LICENSE.txt "$LIZ/MapLibre-LICENSE.txt"
cp "$C/Python/LICENSE.txt" "$LIZ/Python-LICENSE.txt"

# 6. Setup bauen.
ZIEL="$PROJEKT/Installer/${APP}_${VERSION//./_}_win_amd64.exe"
makensis -V2 -DVERSION="$VERSION" -DDIST="$C/proj/dist/$APP" -DPROJEKT="$PROJEKT" -DLIZENZEN="$LIZ" -DOUTFILE="$ZIEL" Build/$APP.nsi
ls -la "$ZIEL"
