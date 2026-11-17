# -*- coding: utf-8 -*-
r"""
Selbsttest des gepackten Programms (exe/.deb), ohne Bildschirm.

Wird mit demselben Bauplan gepackt wie das Programm (Variablen AKG_STARTSKRIPT und
AKG_PAKETNAME, siehe Build/AktionskartenGenerator.spec) und prüft im gepackten Zustand:
kein Debug, MapLibre-Dateien gefunden, Vektor-Ansicht lädt, Export geht, nichts wird neben
das Programm geschrieben. Das Ergebnis steht in der Datei, die als erstes Argument
übergeben wird (ein Programm ohne Konsolenfenster hat keine Ausgabe).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ZEILEN = []
FEHLER = []


ZIEL = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def schreib(zeile):
    # Nach jedem Schritt speichern: bleibt der Test hängen, steht der Stand trotzdem in der Datei.
    ZEILEN.append(zeile)
    if ZIEL is not None:
        ZIEL.write_text("\n".join(ZEILEN) + "\n", encoding="utf-8")


def pruef(name, bedingung, info=""):
    schreib(("OK   " if bedingung else "FEHL ") + name + (f"  [{info}]" if info else ""))
    if not bedingung:
        FEHLER.append(name)


def main():
    ziel = ZIEL
    try:
        import AktionskartenGenerator as akg
        import theme
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication

        def warte(ms):
            loop = QEventLoop()
            QTimer.singleShot(ms, loop.quit)
            loop.exec()

        schreib("gestartet")
        app = QApplication(sys.argv[:1])
        app.setApplicationName(akg.APP_NAME)
        app.setStyleSheet(theme.QSS)
        schreib("QApplication angelegt")
        win = akg.MainWindow()
        schreib("Hauptfenster angelegt")
        win.show()
        warte(500)
        pruef("gepackt erkannt", akg.FROZEN is True)
        pruef("Version", akg.APP_VERSION == "2.9", akg.APP_VERSION)
        pruef("Fenstertitel", win.windowTitle() == f"{akg.APP_NAME} {akg.APP_VERSION}", win.windowTitle())
        pruef("Schalter Debugging ausgeblendet", not win.debug_action.isVisible())
        akg.DEBUG_LOG_ENABLED = True
        akg.log_debug("darf nicht geschrieben werden")
        akg.DEBUG_LOG_ENABLED = False
        pruef("kein Debug-Log", not akg._debug_log_path().exists(), str(akg._debug_log_path()))
        pruef("MapLibre-Dateien gefunden", not akg.maplibre_files_missing(), str(akg.maplibre_files_missing()))
        pruef("QtWebEngine vorhanden", bool(akg.HAS_WEBENGINE))
        pruef("Vektor-Ansicht verfuegbar", bool(win.canvas.vector_preview))
        if win.canvas.vector_preview:
            zustand = {}

            def frage():
                loop = QEventLoop()
                win.map_container.web.page().runJavaScript(
                    "window.aktionsMapSet ? 'bereit' : 'wartet'", lambda v: (zustand.__setitem__("v", v), loop.quit()))
                QTimer.singleShot(3000, loop.quit)
                loop.exec()
                return zustand.get("v")

            for _ in range(80):
                warte(250)
                if frage() == "bereit":
                    break
            pruef("Kartenseite geladen (MapLibre lokal)", zustand.get("v") == "bereit", str(zustand.get("v")))
            bild = win._render_export_image(1240, 877)
            pruef("Export-Bild Vektor", bild is not None and not bild.isNull())
            win.map_mode_raster_btn.click()
        bild = win._render_export_image(1240, 877)
        pruef("Export-Bild Raster", bild is not None and not bild.isNull())
        ordner = Path(sys.executable).resolve().parent
        neu = sorted(p.name for p in ordner.iterdir() if p.suffix.lower() in (".log", ".json", ".txt") and p != ziel)
        pruef("nichts neben das Programm geschrieben", not neu, str(neu))
        win.close()
        warte(300)
    except Exception as exc:  # der Test soll immer ein Ergebnis hinterlassen
        import traceback
        schreib("FEHL Ausnahme: " + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        FEHLER.append("Ausnahme")
    schreib("Ergebnis: " + ("alle gruen" if not FEHLER else "FEHLER: " + ", ".join(FEHLER)))
    if ziel is None:
        print("\n".join(ZEILEN))
    return 1 if FEHLER else 0


if __name__ == "__main__":
    sys.exit(main())
