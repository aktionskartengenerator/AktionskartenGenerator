#!/usr/bin/env bash
# Baut das Linux-Paket (.deb) von AktionskartenGenerator.
#
# Gebaut wird auf Ubuntu 24.04 / Linux Mint 22 (glibc 2.39) mit Python 3.12.
# Aufruf aus einer Kopie des Projektordners auf der Linux-Seite (nicht im verbundenen Ordner):
#     bash Build/build_deb.sh
# Ergebnis: Installer/AktionskartenGenerator_<Version mit _>_linux_amd64.deb
set -euo pipefail
cd "$(dirname "$0")/.."
PROJEKT="$(pwd)"
APP="AktionskartenGenerator"
PAKET="aktionskartengenerator"
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"$/\1/p' "App/$APP.py")"
[ -n "$VERSION" ] || { echo "APP_VERSION nicht gefunden"; exit 1; }
BAU="$PROJEKT/Build/_temp/deb"
VENV="$PROJEKT/Build/_temp/venv_linux"
rm -rf "$BAU"
mkdir -p "$BAU" "$PROJEKT/Installer"

if [ ! -x "$VENV/bin/python" ]; then
    python3.12 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install -r App/requirements.txt pyinstaller
fi

"$VENV/bin/python" -m PyInstaller --noconfirm --distpath "$BAU/dist" --workpath "$BAU/work" Build/$APP.spec

WURZEL="$BAU/wurzel"
mkdir -p "$WURZEL/DEBIAN" "$WURZEL/opt" "$WURZEL/usr/bin" "$WURZEL/usr/share/applications" \
         "$WURZEL/usr/share/icons/hicolor/128x128/apps" "$WURZEL/usr/share/doc/$PAKET"
cp -a "$BAU/dist/$APP" "$WURZEL/opt/$PAKET"
ln -s "/opt/$PAKET/$APP" "$WURZEL/usr/bin/$PAKET"
cp Info_Linux.txt "$WURZEL/usr/share/doc/$PAKET/Info.txt"
# Icon: die Vorlage hat 149 px; ohne Vergrößern passt 128 px.
"$VENV/bin/python" - "$PROJEKT/Icon/${APP}_Icon.png" "$WURZEL/usr/share/icons/hicolor/128x128/apps/$PAKET.png" <<'PY'
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
bild = QImage(sys.argv[1]).scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
assert not bild.isNull() and bild.save(sys.argv[2], "PNG")
PY

cat > "$WURZEL/usr/share/applications/$PAKET.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP
Comment=Aktionskarten erstellen
Comment[en]=Create action maps
Exec=/opt/$PAKET/$APP
Icon=$PAKET
Terminal=false
Categories=Graphics;
StartupWMClass=$APP
DESKTOP

GROESSE="$(du -sk "$WURZEL" | cut -f1)"
cat > "$WURZEL/DEBIAN/control" <<CONTROL
Package: $PAKET
Version: $VERSION
Architecture: amd64
Maintainer: unknown <unknown@invalid>
Section: graphics
Priority: optional
Installed-Size: $GROESSE
Depends: libc6 (>= 2.39), libegl1, libgl1, libglx0, libdrm2, libxcb1, libxcb-cursor0, libxcb-dri3-0, libwayland-client0, libwayland-cursor0, libwayland-egl1, fonts-dejavu-core | fonts-liberation | fonts-noto-core
Description: Aktionskarten erstellen
 Karten mit Symbol-Punkten, Routen, Zonen, Bildern, Titel und Legende
 gestalten und als JPG oder PDF ausgeben.
CONTROL

for skript in postinst postrm; do
    {
        echo '#!/bin/sh'
        echo 'set -e'
        if [ "$skript" = postrm ]; then
            # Leere Unterordner, die zur Laufzeit entstanden sein können, mit entfernen.
            echo 'if [ "$1" = remove ] || [ "$1" = purge ]; then rm -rf /opt/'"$PAKET"'; fi'
        fi
        echo 'update-desktop-database -q /usr/share/applications 2>/dev/null || true'
        echo 'gtk-update-icon-cache -q -f /usr/share/icons/hicolor 2>/dev/null || true'
        echo 'exit 0'
    } > "$WURZEL/DEBIAN/$skript"
    chmod 755 "$WURZEL/DEBIAN/$skript"
done

find "$WURZEL" -type d -exec chmod 755 {} +
find "$WURZEL/usr/share" "$WURZEL/DEBIAN/control" -type f -exec chmod 644 {} +
chmod 755 "$WURZEL/opt/$PAKET/$APP"

ZIEL="$PROJEKT/Installer/${APP}_${VERSION//./_}_linux_amd64.deb"
dpkg-deb --root-owner-group -Zxz --build "$WURZEL" "$ZIEL"
ls -la "$ZIEL"
