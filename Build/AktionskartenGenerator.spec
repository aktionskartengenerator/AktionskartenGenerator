# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Bauplan für Windows (exe) und Linux (.deb). Ein Ordner, kein Konsolenfenster.
# Aufruf aus dem Projektordner:  python -m PyInstaller --noconfirm Build/AktionskartenGenerator.spec
import os
import sys

APP = "AktionskartenGenerator"
PROJEKT = os.path.abspath(os.path.join(SPECPATH, ".."))
# Für den Selbsttest des Pakets (Build/Tests/gepackt_selbsttest.py) lässt sich das
# Startskript austauschen; ohne die Variable wird das Programm selbst gepackt.
START = os.environ.get("AKG_STARTSKRIPT") or os.path.join(PROJEKT, "App", APP + ".py")
NAME = os.environ.get("AKG_PAKETNAME") or APP

a = Analysis(
    [START],
    pathex=[os.path.join(PROJEKT, "App")],
    # MapLibre liegt als lokale Dateien bei; das Programm findet sie über _resource_dir().
    datas=[(os.path.join(PROJEKT, "App", "maplibre"), "maplibre")],
    hiddenimports=["theme"],
    excludes=["tkinter", "PIL", "PySide6.QtQuick3D", "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtDataVisualization",
              "PySide6.QtMultimedia", "PySide6.QtBluetooth", "PySide6.QtSql", "PySide6.QtTest"],
    noarchive=False,
)


# Qt-Bibliotheken, die das Programm samt Vektor-Ansicht (QtWebEngine) wirklich braucht.
# Ermittelt über die Abhängigkeiten der verwendeten Module, des Web-Prozesses und der
# Plattform-Plugins. PyInstaller nähme sonst über die QML-Plugins fast ganz Qt mit.
QT_BEHALTEN = {
    "Core", "DBus", "Gui", "Network", "OpenGL", "Pdf", "Positioning", "PrintSupport",
    "Qml", "QmlMeta", "QmlModels", "QmlWorkerScript", "Quick", "QuickWidgets", "Svg",
    "WebChannel", "WebEngineCore", "WebEngineWidgets", "Widgets",
    # nur Linux
    "EglFSDeviceIntegration", "EglFsKmsSupport", "WaylandClient", "WlShellIntegration", "XcbQpa",
}
WEB_SPRACHEN = {"de.pak", "en-us.pak", "en-gb.pak"}


def _unnoetig(ziel):
    name = "/" + ziel.replace("\\", "/").lower()
    basis = name.rsplit("/", 1)[-1]
    # Software-OpenGL für Windows: groß und hier nicht gebraucht.
    if basis == "opengl32sw.dll":
        return True
    # Übersetzungen der Qt-Oberfläche.
    if "/translations/" in name and basis.endswith(".qm"):
        return True
    # Sprachdateien von QtWebEngine: Deutsch und Englisch reichen.
    if "/qtwebengine_locales/" in name and basis.endswith(".pak") and basis not in WEB_SPRACHEN:
        return True
    # Entwicklerwerkzeuge der Web-Ansicht und die Debug-Fassungen ihrer Ressourcen (Windows).
    if basis.startswith("qtwebengine_devtools_resources") or ("/resources/" in name and ".debug." in basis):
        return True
    # QML-Module und ihre Werkzeuge: die Vektor-Ansicht ist ein Widget, kein QML.
    if "/qml/" in name or "/plugins/qmltooling/" in name:
        return True
    # Positionsdienste und Bildschirmtastatur von Qt.
    if "/plugins/position/" in name or "virtualkeyboard" in basis:
        return True
    # GTK-Plattformthema: das Programm stylt sich selbst.
    if basis in ("libqgtk3.so",) or basis.startswith(("libgtk-3.so", "libgdk-3.so")):
        return True
    # Qt-Bibliotheken außerhalb der Liste oben.
    for vor, nach in (("libqt6", ".so"), ("qt6", ".dll")):
        if basis.startswith(vor) and nach in basis:
            modul = basis[len(vor):].split(".", 1)[0]
            return modul not in {m.lower() for m in QT_BEHALTEN}
    return False


a.binaries = [b for b in a.binaries if not _unnoetig(b[0])]
a.datas = [d for d in a.datas if not _unnoetig(d[0])]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(PROJEKT, "Icon", APP + "_Icon.ico") if sys.platform == "win32" else None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=NAME)
