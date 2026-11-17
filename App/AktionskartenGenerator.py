#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AktionskartenGenerator
"""

import base64
import html
import json
import math
import re
import sys
import traceback
import shutil
from urllib.parse import quote
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QMarginsF,
    QObject,
    QPointF,
    QRectF,
    QSize,
    Qt,
    Signal,
    Slot,
    QStandardPaths,
    QUrl,
    QTimer,
    QEventLoop,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QIcon,
    QKeySequence,
    QShortcut,
    QPainter,
    QPainterPath,
    QPageLayout,
    QPageSize,
    QPdfWriter,
    QPen,
    QPixmap,
    QPolygonF,
    QTextCharFormat,
    QTextDocument,
    QTextCursor,
    QValidator,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedLayout,
    QTextEdit,
    QToolBar,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

import theme

APP_NAME = "AktionskartenGenerator"
APP_VERSION = "2.9"
# Gepackt (exe/.deb) schreibt das Programm keine eigenen Dateien: kein Debug-Log,
# kein Datenordner. Aus dem Quelltext liegt das Debug-Log im Ordner App.
FROZEN = bool(getattr(sys, "frozen", False))

DEBUG_LOG_ENABLED = False
NETWORK_USER_AGENT = "unknown-map-client/1.0"
FIXED_PDF_DATE = "D:19700101000000+00'00'"

def _app_dir() -> Path:
    try:
        if FROZEN:
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()

def _resource_dir() -> Path:
    # Mitgelieferte, nur gelesene Dateien (MapLibre). Gepackt liegen sie im Paketordner.
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", _app_dir()))
    return _app_dir()

def _debug_log_path() -> Path:
    return _app_dir() / "aktionskarten_debug.log"

def log_debug(message: str, exc: Optional[BaseException] = None) -> None:
    if not DEBUG_LOG_ENABLED or FROZEN:
        return
    try:
        with _debug_log_path().open("a", encoding="utf-8") as fh:
            fh.write(str(message) + "\n")
            if exc is not None:
                fh.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            fh.write("\n")
    except Exception:
        return

# Für die Vektor-Ansicht wird MapLibre in QtWebEngine verwendet. Die Bibliothek liegt
# als lokale Dateien im Ordner maplibre; es wird nichts von einem CDN geladen.
# Die Seite und die Dateien werden über ein eigenes Schema ausgeliefert, das vor dem
# Anlegen der QApplication registriert sein muss.
MAPLIBRE_SCHEME = b"akg"
MAPLIBRE_PAGE_URL = "akg://karte/karte.html"
try:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtWebEngineCore import (
        QWebEnginePage,
        QWebEngineProfile,
        QWebEngineUrlRequestJob,
        QWebEngineUrlScheme,
        QWebEngineUrlSchemeHandler,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _scheme = QWebEngineUrlScheme(MAPLIBRE_SCHEME)
    _scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    _scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.CorsEnabled
        | QWebEngineUrlScheme.Flag.FetchApiAllowed
    )
    QWebEngineUrlScheme.registerScheme(_scheme)
    HAS_WEBENGINE = True
except Exception as exc:
    QWebEngineView = None
    HAS_WEBENGINE = False
    log_debug("QtWebEngine nicht verfügbar", exc)

EN_TEXT = {
    "Projekt speichern": "Save project",
    "Projekt laden": "Load project",
    "JPG A4 exportieren": "Export A4 JPG",
    "PDF A4 exportieren": "Export A4 PDF",
    "JPG exportieren": "Export JPG",
    "PDF exportieren": "Export PDF",
    "Kacheln neu laden": "Reload tiles",
    "Map neu laden": "Reload map",
    "Neu / zurücksetzen": "New / reset",
    "Sprache:": "Language:",
    "Debugging aktivieren": "Enable debugging",
    "Titel der Aktionskarte": "Map title",
    "Ortssuche": "Place search",
    "Karte / Gitter": "Map / grid",
    "Symbol-Punkte": "Symbol points",
    "Route": "Route",
    "Bilddatei": "Image file",
    "Legende / Textfeld": "Legend / text box",
    "A4 / Gitter": "A4 / grid",
    "Papier / Gitter": "Paper / grid",
    "Papiergröße:": "Paper size:",
    "Format:": "Orientation:",
    "Randbreite:": "Border width:",
    "Gitter:": "Grid:",
    "roten Rand anzeigen": "Show red border",
    "Gitterlinien anzeigen": "Show grid lines",
    "Mausrad: Zoom | Ziehen: Karte schieben": "Mouse wheel: zoom | drag: move map",
    "Suche:": "Search:",
    "Suchen": "Search",
    "Zentrieren": "Center",
    "Ergebnis:": "Result:",
    "Ergebnis als Punkt setzen": "Set result as point",
    "Ort, Adresse oder Platz suchen": "Search city, address or place",
    "Neuer Symbol-Punkt": "New symbol point",
    "Aktiv, sobald dieses Menü geöffnet ist: Klick in die Karte setzt einen Symbol-Punkt. Vorhandene Punkte bleiben verschiebbar.": "Active while this section is open: clicking the map places a symbol point. Existing points remain movable.",
    "Text:": "Text:",
    "z. B. Eingang, Kamera 2": "e.g. entrance, camera 2",
    "Symbolfarbe": "Symbol color",
    "andere Farbe...": "custom color...",
    "Symbole": "Symbols",
    "Ausgewählter Punkt": "Selected point",
    "kein Punkt ausgewählt": "no point selected",
    "Textposition:": "Text position:",
    "Abstand:": "Gap:",
    "Schriftgröße:": "Font size:",
    "Box-Deckkraft:": "Box opacity:",
    "Textfarbe:": "Text color:",
    "Textfarbe: #000000": "Text color: #000000",
    "Fett": "Bold",
    "Kursiv": "Italic",
    "Unterstrichen": "Underline",
    "Stil:": "Style:",
    "Symbolgröße:": "Symbol size:",
    "Text übernehmen": "Apply text",
    "Punkt löschen": "Delete point",
    "Routen": "Routes",
    "Aktiv, sobald dieses Menü geöffnet ist: Klick in die Karte setzt einen Routenpunkt. Danach Ohne Berechnung speichern oder Route berechnen.": "Active while this section is open: clicking the map places a route point. Then save the click route or calculate a route.",
    "Name:": "Name:",
    "z. B. Route 1": "e.g. Route 1",
    "Farbe: #ff0505": "Color: #ff0505",
    "Farbe:": "Color:",
    "Linie:": "Line:",
    "Breite:": "Width:",
    "Klickroute speichern": "Save click route",
    "Punkt zurück": "Undo point",
    "Route berechnen": "Calculate route",
    "Routen löschen": "Delete routes",
    "ausgewählten Punkt als Zwischenstopp": "Use selected point as waypoint",
    "Bilddatei einfügen": "Insert image file",
    "Erlaubte Formate: JPG, PNG. Die Datei wird ins Projekt eingebettet und bleibt dadurch ohne festen Dateipfad nutzbar.": "Allowed formats: JPG, PNG. The file is embedded into the project, so it stays usable without a fixed file path.",
    "• Erlaubte Formate: JPG, PNG.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Allowed formats: JPG, PNG.\n• Right-click the map to clear selection.",
    "keine Bilddatei ausgewählt": "no image file selected",
    "Bilddatei hochladen…": "Upload image file…",
    "Bilddatei löschen": "Delete image file",
    "Textfeld / Legende": "Text box / legend",
    "Aktiv, sobald dieses Menü geöffnet ist: Symbol- und Routen-Klickmodus sind aus. Textfelder lassen sich auswählen und bearbeiten.": "Active while this section is open: symbol and route click modes are off. Text boxes can be selected and edited.",
    "Textstil Auswahl:": "Selected text style:",
    "Position:": "Position:",
    "Füllfarbe:": "Fill color:",
    "Füllfarbe: #ffffff": "Fill color: #ffffff",
    "Grundstil:": "Base style:",
    "alles Fett": "all bold",
    "alles Kursiv": "all italic",
    "alles Unterstrichen": "all underlined",
    "Neu/aktualisieren": "New/update",
    "Textfeld löschen": "Delete text box",
    "Querformat": "Landscape",
    "Hochformat": "Portrait",
    "Locker": "Loose",
    "Mittel": "Medium",
    "Eng": "Tight",
    "Rechts": "Right",
    "Links": "Left",
    "Oben": "Top",
    "Unten": "Bottom",
    "Rechts oben": "Top right",
    "Rechts unten": "Bottom right",
    "Links oben": "Top left",
    "Links unten": "Bottom left",
    "Bereit": "Ready",
    "Suche läuft...": "Searching...",
    "Kartenkacheln werden erneut geladen...": "Map tiles are being reloaded...",
    "Map wird neu geladen...": "Reloading map...",
    "Bitte zuerst einen Punkt auswählen.": "Please select a point first.",
    "Bitte mindestens zwei Routenpunkte setzen.": "Please place at least two route points.",
    "Bitte mindestens Start und Ziel setzen.": "Please place at least a start and destination.",
    "Route berechnet": "Route calculated",
    "Bilddateien": "image files",
    "Suchergebnisse": "search results",
    "Bilddatei konnte nicht geladen werden. Bitte PNG oder JPG verwenden.": "Image file could not be loaded. Please use PNG or JPG.",
    "Bilddatei hochladen": "Upload image file",
    "Zurücksetzen": "Reset",
    "Karten Ausschnitt / Orte": "Map view / places",
    "Größe / Gitter": "Size / grid",
    "Titel": "Title",
    "Zonen": "Zones",
    "Zone": "Zone",
    "Kartenebene:": "Map layer:",
    "Zoom:": "Zoom:",
    "Maßstab anzeigen": "Show scale",
    "Maßstab Position:": "Scale position:",
    "Maßstab Länge m:": "Scale length m:",
        "Hintergrundfarbe:": "Background color:",
    "Hintergrundfarbe: #ffffff": "Background color: #ffffff",
    "Farbe: #ff0505": "Color: #ff0505",
    "Füllfarbe: #ffffff": "Fill color: #ffffff",
    "Füllfarbe: #ff0505": "Fill color: #ff0505",
    "Konturfarbe: #ff0505": "Outline color: #ff0505",
    "Hintergrund-Deckkraft:": "Background opacity:",
    "Bestehende Punkte:": "Existing points:",
    "Symbol aktualisieren": "Update symbol",
    "Ohne Berechnung speichern": "Save without calculation",
    "Bestehende Routen:": "Existing routes:",
    "Ausgewählte Route löschen": "Delete selected route",
    "Bestehende Bilddateien:": "Existing image files:",
    "Textausrichtung:": "Text alignment:",
    "Feld aktualisieren": "Update field",
    "Deckkraft:": "Opacity:",
    "Bestehende Zonen:": "Existing zones:",
    "Neue Zone": "New zone",
    "Zone speichern": "Save zone",
    "Zone aktualisieren": "Update zone",
    "Zone löschen": "Delete zone",
    "Füllfarbe": "Fill color",
    "Konturfarbe": "Outline color",
    "Konturfarbe:": "Outline color:",
    "Konturbreite:": "Outline width:",
    "Beschriftung Position:": "Label position:",
    "Mitte": "Center",
    "Links": "Left",
    "Zentriert": "Centered",
    "Maßstab Deckkraft:": "Scale opacity:",
    "Texthintergrund:": "Text background:",
    "Text-Hintergrund Deckkraft:": "Text background opacity:",
    "• Ort suchen oder Karte mit Maus bewegen.\n• Mausrad zoomt die Karte.": "• Search a place or move the map with the mouse.\n• Mouse wheel zooms the map.",
    "• Klick in die Karte setzt einen Symbol-Punkt.\n• Bestehende Punkte können ausgewählt und bearbeitet werden.\n• Im Routenmodus sind Symbole nicht klickbar.": "• Click the map to place a symbol point.\n• Existing points can be selected and edited.\n• In route mode, symbols are not clickable.",
    "• Klick in die Karte setzt Routenpunkte.\n• Route berechnen erstellt Pfad.\n• Ohne Berechnung speichert die Klicklinie.": "• Click the map to place route points.\n• Calculate route creates a path.\n• Save without calculation stores the click line.",
    "• Klick in die Karte setzt Eckpunkte einer Zone.\n• Mindestens drei Punkte speichern eine Fläche.": "• Click the map to place zone corners.\n• At least three points save an area.",
    "• JPG oder PNG hochladen.\n• Bilddatei kann verschoben und skaliert werden.": "• Upload JPG or PNG.\n• Image files can be moved and scaled.",
    "• Text eingeben und formatieren.\n• Markierte Wörter können Fett/Kursiv/Unterstrichen werden.\n• Position, Farbe, Ausrichtung und Deckkraft sind einstellbar.": "• Enter and format text.\n• Selected words can be bold/italic/underlined.\n• Position, color, alignment and opacity can be adjusted.",
    "Symbolfarbe wählen": "Choose symbol color",
    "Textfarbe wählen": "Choose text color",
    "Füllfarbe wählen": "Choose fill color",
    "Konturfarbe wählen": "Choose outline color",
    "Hintergrundfarbe wählen": "Choose background color",
    "Bitte zuerst eine Zone auswählen.": "Please select a zone first.",
    "Bitte mindestens drei Zonenpunkte setzen.": "Please place at least three zone points.",
    "Suche fehlgeschlagen:": "Search failed:",
    "Route berechnen erstellt Pfad.": "Calculate route creates a path.",
    "• Klick in die Karte setzt einen Symbol-Punkt.\n• Bestehende Punkte können ausgewählt und bearbeitet werden.\n• Im Routenmodus sind Symbole nicht klickbar.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Click the map to place a symbol point.\n• Existing points can be selected and edited.\n• In route mode, symbols are not clickable.\n• Right-click the map to clear selection.",
    "• Klick in die Karte setzt Routenpunkte.\n• Route berechnen erstellt Pfad.\n• Ohne Berechnung speichert die Klicklinie.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Click the map to place route points.\n• Calculate route creates a path.\n• Save without calculation stores the click line.\n• Right-click the map to clear selection.",
    "• Klick in die Karte setzt Eckpunkte einer Zone.\n• Mindestens drei Punkte speichern eine Fläche.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Click the map to place zone corners.\n• At least three points save an area.\n• Right-click the map to clear selection.",
    "• Text eingeben und formatieren.\n• Markierte Wörter können Fett/Kursiv/Unterstrichen werden.\n• Position, Farbe, Ausrichtung und Deckkraft sind einstellbar.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Enter and format text.\n• Selected words can be bold/italic/underlined.\n• Position, color, alignment and opacity can be adjusted.\n• Right-click the map to clear selection.",
    "Routenfarbe wählen": "Choose route color",
    "Punkt": "Point",
    "Speichern": "Save",
    "Laden": "Load",
    "Export": "Export",
    "Aktionskarten-Projekt (*.json)": "Action map project (*.json)",
    "Aktionskarten-Projekt (*.json);;Alle Dateien (*)": "Action map project (*.json);;All files (*)",
    "Alle Dateien (*)": "All files (*)",
    "JPEG-Bild (*.jpg *.jpeg)": "JPEG image (*.jpg *.jpeg)",
    "PDF-Datei (*.pdf)": "PDF file (*.pdf)",
    "Bilddateien (*.png *.jpg *.jpeg)": "Image files (*.png *.jpg *.jpeg)",
    "Aktuelle Punkte und Textfelder wirklich löschen?": "Really delete the current points and text boxes?",
    "JPG konnte nicht gespeichert werden.": "JPG could not be saved.",
    "PDF konnte nicht gespeichert werden:": "PDF could not be saved:",
    "Projekt konnte nicht gespeichert werden:": "Project could not be saved:",
    "Projekt konnte nicht geladen werden:": "Project could not be loaded:",
    "Routenberechnung fehlgeschlagen:": "Route calculation failed:",

    "z. B. Kundgebung, Küfa etc.": "e.g. rally, kitchen, etc.",
    "Routen Legende hinzufügen": "Add routes legend",
    "• Ort suchen oder Karte mit Maus bewegen.\n• Mausrad zoomt die Karte.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Search a place or move the map with the mouse.\n• Mouse wheel zooms the map.\n• Right-click the map to clear selection.",
    "• JPG oder PNG hochladen.\n• Bilddatei kann verschoben und skaliert werden.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Upload JPG or PNG.\n• Image files can be moved and scaled.\n• Right-click the map to clear selection.",
    "Fußroute wird berechnet...": "Calculating walking route...",
    "Fußroute wird mit Alternativ-Endpunkt berechnet...": "Calculating walking route with fallback endpoint...",
    "Zoom": "Zoom",
    "Karte ziehen verschiebt den Ausschnitt; kurzer Klick setzt ein Element.": "Drag the map to move the view; a short click places an element.",
    "Map neu laden": "Reload map",
    "Anleitung": "Instructions",
    "Textfeld anzeigen": "Show text box",
    "Symbol einfügen": "Insert symbol",
    "Symbol im Text:": "Symbol in text:",
    "Farbe für Auswahl:": "Color for selection:",
    "Textfarbe Auswahl": "Selection text color",
    "Textfeld anzeigen": "Show text box",
    "Symbolfarbe:": "Symbol color:",
    "Symbol im Text:": "Symbol in text:",
    "Symbol einfügen": "Insert symbol",
    "• Text eingeben und frei formatieren.\n• Markierte Wörter können Fett/Kursiv/Unterstrichen und farbig werden.\n• Symbole können in den Text eingefügt werden.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Enter text and format it freely.\n• Selected words can become bold/italic/underlined and colored.\n• Symbols can be inserted into the text.\n• Right-click the map to clear selection.",
    "Kurzanleitung": "Quick guide",
    "Deckkraft:": "Opacity:",
    "Wegbeschreibung:": "Directions:",
    "Routen-Deckkraft:": "Route opacity:",
    "Wegbeschreibung kopierbar unten im Reiter.": "Directions can be copied at the bottom of the tab.",
    "Nach Route berechnen steht hier die kopierbare Wegbeschreibung mit Länge und Dauer.": "After calculating a route, the copyable directions with length and duration appear here.",
    "Route bearbeiten": "Edit route",
    "Ausgewählte Route bearbeiten": "Edit selected route",
    "Alle Routen löschen": "Delete all routes",
    "Berechnungsart:": "Route type:",
    "• Klick in die Karte setzt Routenpunkte.\n• Berechnungsart wählen: Fuß, Fahrrad oder PKW.\n• Route berechnen erstellt Pfad und Wegbeschreibung.\n• Route bearbeiten wandelt die Route zurück in Punkte.": "• Click the map to place route points.\n• Choose route type: walking, bike or car.\n• Calculate route creates a path and directions.\n• Edit route converts the route back into points.",
    "Fuß-Route": "Walking route",
    "Fahrrad-Route": "Bike route",
    "PKW-Route": "Car route",
    "Fußroute wird berechnet...": "Calculating walking route...",
    "Fahrradroute wird berechnet...": "Calculating bike route...",
    "PKW-Route wird berechnet...": "Calculating car route...",
    "Route wird mit Alternativ-Endpunkt berechnet...": "Calculating route with fallback endpoint...",
    "Route wird als bearbeitbare Punkte weitergeführt. Danach Punkt zurück, weitere Punkte setzen oder erneut berechnen/speichern.": "The route is continued as editable points. You can then undo points, add more points, or calculate/save it again.",
    "Bitte zuerst eine Route auswählen.": "Please select a route first.",
    "• Ort suchen oder Karte mit Maus bewegen.\n• Mausrad/Trackpad zoomt fein und stufenlos.\n• Rechtsklick in Karte wählt Auswahl ab.": "• Search a place or move the map with the mouse.\n• Mouse wheel/trackpad zooms smoothly and finely.\n• Right-click the map to clear selection.",
}

EN_TEXT.update({
    "Bildung": "Education",
    "Gesundheit": "Healthcare",
    "Kartennamen / Symbole": "Map names / symbols",
    "POI-Namen/Symbole filtern": "Filter POI names/symbols",
    "Namen anzeigen": "Show names",
    "Symbole anzeigen": "Show symbols",
    "Religiös": "Religious",
    "Einkaufen": "Shopping",
    "Gastronomie": "Food / drink",
    "Kultur / Freizeit": "Culture / leisure",
    "Öffentliche Einrichtungen": "Public services",
    "Verkehr / Parken": "Transport / parking",
    "Unterkunft": "Accommodation",
    "Sonstige POIs": "Other POIs",
    "Filter betrifft nur Namen und Kartensymbole, keine Gebäudeflächen.": "The filter affects only names and map symbols, not building areas.",
    "Vektorfilter aktiv": "Vector filter active",
    "Kartenart:": "Map type:",
    "Raster": "Raster",
    "Vektor": "Vector",
    "Vektor-Ansicht aktiv": "Vector view active",
    "Vektor-Ansicht nicht verfügbar": "Vector view unavailable",
    "Der POI-Filter ist nur in der Vektor-Ansicht bedienbar.": "The POI filter can only be used in the vector view.",
})

EN_TEXT.update({
    "ÖPNV": "Public transport",
    "POIs ab Zoom:": "POIs from zoom:",
    "(Vorgabe)": "(default)",
    "Diese Kartenebene enthält in der Vektor-Ansicht keine POIs.": "This map layer contains no POIs in the vector view.",
    "Die Vektor-Ansicht ist nicht verfügbar. Der Export wurde abgebrochen, damit keine andere Karte gespeichert wird.": "The vector view is unavailable. The export was cancelled so that no other map is saved.",
    "Die Vektorkarte konnte nicht erfasst werden. Der Export wurde abgebrochen, damit keine andere Karte gespeichert wird.": "The vector map could not be captured. The export was cancelled so that no other map is saved.",
    "Projekt gespeichert:": "Project saved:",
    "Projekt geladen:": "Project loaded:",
    "exportiert:": "exported:",
    "Ja": "Yes",
    "Nein": "No",
    "Kopieren": "Copy",
    "Wegbeschreibung kopiert.": "Directions copied.",
    "Keine Wegbeschreibung vorhanden.": "No directions available.",
    "Bestehende Textfelder:": "Existing text boxes:",
    "z. B. Textfeld 1": "e.g. Text box 1",
    "Neues Textfeld": "New text box",
    "Kein Textfeld gewählt: bitte ein Textfeld auswählen oder „Neues Textfeld“ drücken.": "No text box selected: please select a text box or press “New text box”.",
    "Route wird neu berechnet...": "Recalculating route...",
    "Route neu berechnet": "Route recalculated",
})


def tr_text(text: str, lang: str = "de") -> str:
    if lang == "en":
        return EN_TEXT.get(text, text)
    return text



_OriginalQSpinBox = QSpinBox

class QSpinBox(_OriginalQSpinBox):
    """QSpinBox with large, reliable up/down click zones, visible arrows and clamped typed values."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        try:
            self.setKeyboardTracking(False)
            self.editingFinished.connect(self._commit_clamped_text)
            self.lineEdit().textEdited.connect(self._clamp_over_max_while_typing)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def validate(self, text: str, pos: int):
        # Qts normaler QSpinBox-Validator blockiert Werte außerhalb der Range schon beim Tippen.
        # Für diese UI sollen Werte wie 9999 eingebbar sein und danach sofort auf Max/Min springen.
        if text.strip() in ("", "+", "-"):
            return (QValidator.State.Intermediate, text, pos)
        if re.fullmatch(r"[-+]?\d+", text.strip()):
            return (QValidator.State.Acceptable, text, pos)
        return (QValidator.State.Invalid, text, pos)

    def _clamp_over_max_while_typing(self, text: str) -> None:
        try:
            raw = text.strip()
            if not re.fullmatch(r"[-+]?\d+", raw):
                return
            value = int(raw)
            max_txt_len = len(str(abs(self.maximum())))
            # Erst den getippten Wert zulassen, dann sofort nach dem Tastendruck
            # sichtbar auf Min/Max korrigieren. So blockiert die Eingabe nicht.
            if value > self.maximum() and len(raw.lstrip("+-")) >= max_txt_len:
                QTimer.singleShot(0, self._commit_clamped_text)
            elif value < self.minimum() and raw.startswith("-"):
                QTimer.singleShot(0, self._commit_clamped_text)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def _commit_clamped_text(self) -> None:
        try:
            raw = self.lineEdit().text().strip()
            if not raw:
                return
            m = re.search(r"[-+]?\d+", raw)
            if not m:
                self.setValue(self.value())
                return
            value = int(m.group(0))
            if value < self.minimum():
                self.setValue(self.minimum())
            elif value > self.maximum():
                self.setValue(self.maximum())
            else:
                self.setValue(value)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def mousePressEvent(self, event) -> None:
        try:
            pos = event.position()
            btn_w = 42.0
            if pos.x() >= self.width() - btn_w:
                if pos.y() < self.height() / 2.0:
                    self.stepBy(1)
                else:
                    self.stepBy(-1)
                event.accept()
                return
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            arrow_color = QColor(theme.NEBENTEXT)
            if not self.isEnabled():
                arrow_color = QColor(theme.IDLE)
            p.setBrush(arrow_color)
            p.setPen(Qt.PenStyle.NoPen)
            btn_w = 42.0
            x0 = max(0.0, float(self.width()) - btn_w)
            mid_x = x0 + btn_w / 2.0
            top_mid_y = float(self.height()) * 0.27
            bottom_mid_y = float(self.height()) * 0.73
            size = 6.0
            p.drawPolygon(QPolygonF([
                QPointF(mid_x, top_mid_y - size * 0.70),
                QPointF(mid_x - size, top_mid_y + size * 0.55),
                QPointF(mid_x + size, top_mid_y + size * 0.55),
            ]))
            p.drawPolygon(QPolygonF([
                QPointF(mid_x, bottom_mid_y + size * 0.70),
                QPointF(mid_x - size, bottom_mid_y - size * 0.55),
                QPointF(mid_x + size, bottom_mid_y - size * 0.55),
            ]))
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

ICON_DATA = {
  "bahnhof": {
    "label": "Bahnhof",
    "data": "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"
  },
  "camp": {
    "label": "Camp",
    "data": "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"
  },
  "castor": {
    "label": "Castor",
    "data": "iVBORw0KGgoAAAANSUhEUgAAAJYAAACWCAYAAAA8AXHiAAA1M0lEQVR42u19eXhc13Xf7973Zh8sg40ASQAESZEmRZESJdVbFXmppSRWnMZuq7rKl+SzrVax3VROms/+HLX58kVN7TquFdWWlchObMWqqmizttCk9o0SF5AiBYIL9n0ZYAazz7z37j39470ZDIAZ4A04IAGIJxkTAt56z2/OOfesjIhwha5QuUkFAMbYB/X9NwLYAWAbgFYAmwA0AqgHEABQCcALwJVdKwAGgAyAJIAogDCAIIBxACMABgD0ALgAYPSDuKhEBEZEHxRgXQXgwwCuB3AdgD0Aalf4ntMAOgCcBNAO4AiArivAWtvUAuAzAD4J4NcANK+S5xoC8AaAVwG8CGBwPQIL68zG2gfgvwM4CoDWyOeo9cz7rgBr9Ummb1qqhtb4p916l5YrwLp89DkAT60DMBX7PGW94xVgXQLiAP6zZRDTB+TTYb0zvwKs8pMHwJ8BmPgAAWr+Z8JaA88VYJWHvglg6gMMqPmfKWtNrgBrmfRlAH1XgFT002et0RU/lk26CcBfArj5UtyswV2davHWJZu99alN3tr0Rk9NptEd0OpdlXrA6TcqHF7hVZxS5SoBgCENlhQaj+lJJazF1WAm6hhPh52jqZBrJDntHkoGPYPJKe9keuZSqazXAfw3AG9eAVZhcgL4LoC7V+oGAac/s6eqNbIv0BbdH9gWu75me7za6RMrca8ZLaG0h7r9J8I9FafCfZUdkYGqsBZ3reD63WepSO0KsOa6Dr4PYHu5L3xdYGvo4/W7Q5/asDd8fc32xOV8yfZQt++VidOBt4OdNSfDvTUrcItuAH8C4NkrwAJ+UG4pdUPN9ulbm/YHP9/8sak6V6WxGu2QqUxUfWrocN3BsRP1x0Pd5Y5Z3gfgGx9UYO0H8CCAG8txsSZPTfK2jTeO37Hl5ok2f2NmLTnn+uLjrkf6X9/w/OixxrFUyFumyx4DcBeAEx8kYH0ZwEMALvrG1wW2hr7YevPo7a03TWEd0GMDb9Y9OvD6xjKpSgJwJ4CffhCA9deWHXBR9LG6XcGvbLtl+NON+yJYh/Ty+Kmqn/Qc2nx46mx9GS73fQD/db0CywPgEQC/c7H201ev+uzgegVUIYA90PVCSxnssKcB3AEgtZ6A1QbgsYuxp1p9DfGvXfXZ/vWi8pajIn/U9cKWgcSk/yLtrtthOlfXPLD2A3gSwJblXuDObbf23rPn9kFcIdzb8VjLQz0Ht17EJfoBfGEljfpLAaybLBG8LDF+Q8326T/f88WevYG25BVIzdLpcJ/3Lzoe3XYR6nHaMkneXIvA+gSA5wAsS3R/fcdt3X+66/PDV2BUnL539qnNP7zw/HKdynEAvwXgtbUErJsA/PNyQLXV3xi7d+/vXvh4/e7YFegsTW8HOyvuOf2LHb3x8Yplgus3yy25VgpY+wEcWo76u7Vp/9iDN37tPP/glqMtZBIIYMQY8aJpKJIIdx370c6DYyealqkWbymnzbUSwGoD8MpyDPU/3P4bPd+6+t8OLXUccxGfoaRDdUnmSXs0rqtyPQMr5gq6JhIxtcFTrVfqNYsGmL9z5vHmH3cf2LZMg/5T5dotlhtYHpgpHKW6FOiv9v1e5x1bPhFc9CiFWIYZSsybcI/7xyvfGOis/MTOyvjugU+NQPB1Wc6dcMSc/3Pkxzs211UbV2euC25zNicaXFW6aniKZmQ80v9a/bdPPbwbpUc1jsFMVUqVA1hqGdfhkVJBVenwavftv/OMHWdnzJ10TflC/vaxYf+pqc66I72D/k4mjO/vaIu6erdF150KZJL9LPnzbb98/3zdxs0OdPMU+5dbWuJbYx+a2e5pTnnhLxhcv2PLJ4KN7sB7d5946OqonnSWcMsbLR5+vhzPXy6JVXKYpsFdnXrwxq92LJXKIjyaGuJJ94SRcL+UONx0YnSoYjwWd6Y1AZdL4LNbNwXvdv/hmfUGrCAmXZ9791sfDYUYNIPB7wV21AdSn2m8duIaz+6Zbf6NqQ1KvVbM9moPdfvuOvbAnmUkHF50+KdcqvDLAH5SyglNnprk33/4j97fXdWyqNhNOzKOSU/Mf56dC7zcf77mzOi0NykFF1IByQxUaKirFOIfdt7zrtfw6usFVCkklW8Ofmfvix0jVYZQADhBpIExgeYGt/4vNm2d+WTVjZO7HTujze4NRTM5OiODni8duf+aZWRMfAUXEbguB7D2Azheij5vcFenfv6Ru08vBirmlDwVSHqGUwn30ejZmkNjx5smZzSeMZzQBQeRAcCAKjNwqAZu2lEZ+5b/G+85hFOsB2A9rj7c9j8OvdaSiDuYhAsEDsbTENKA6iT4/IQb/VcHb9vwkYmt1TWZqzytSQ+8ohi4fv/d+/aWKLkIwA3L3SkS0UXXqj1YCqgqHV7twRu/2rGopOLEop6EuwdjVYfoUNuT3ceaRqczPKVL6JQG8RSI6yDSAO6Arit4p2/Gf5AObFoProUYizgeP9VRr6UZk1BA0EFIQkgCgaAbQDTC8cZIV+3Ppp+86kjiVO3p1NnKBIsXtJd3V7WkHrzxqx2VDm8pKcvM4u2y6WKA9YMSjXW6b/+dZxazqSSTbLoy5htg05X/PHq08cCRcX9ad3DJnJBcAlwATAdIA3GCJgiCvNA1hb0YObEp40ypaxlYBtP5P1Z9/5re4LRXEwzEdEhoAAQA3WQ3cUihQBeMd/ZHXU9NHtrSnuioaQ+fr0iKlFLoutfXbE/ct//OM5YkKsWY/8GlBtbnUGI68V/t+73OxXZ/BGIRd8rTZ0z5/3HsQOtbXQOVBgiCMUgYs0siZ79SBAkBB9KGC2f6085/8v9k51oG1jn/u7WPPhvyxGIKuKJYzlHr1ZmloYjAGQN3ApIBXd3AP5x/vbk91FN5NHKuIinSBXn66cZ9kb/a93udJT7S3Vhmmf9ygOW0dg4lOT8X81MRiE14Yr4BhCsOjh1vPDs449EAGBAwKA1JBJIcpDPzyysBIgamMAjSoUsOXXD29Bsz/oSScqxFUOlKWvnlmbOBtKYrghQYpJit3tjsF4oRwEiCpIDUCMQYpEPB1IyKnw8fbDs+faHySKizMiUyvJgr4g+3/0bPMnaJzksBrO+ihGqaW5v2jy3mUZdMshlP0jOOqO9nA8+3HRvpqxbCASEJTBEgSDCmAqQCcABQwKAAxEHEAKaBIJDRFMR53HN/6sHdght8LYGKQDjT8qvNx+InG6NpySUUSClN9tCshObEwMHAIOBwMCjMAaYogEKIRAgPDx7c+t5Mb8U7oTOVxSTXt67+t0O3Nu0fK+Hxtls8X1Fg3VSKCtzqb4w9eOPXzi9mqIerEr5eNVj5wuThpv5QxC04IU06DAnoGmDoBqShgUjC7NIoIcksBmZMACwDMAMEL6IxN070hbxnne8F1hKwMo6Y+r0n36s53yu4Lh2QSMPh4iBd5IBlvXHOIshoGWi6DiNlQOoCYEAiBfx04MC2E6GuyqPhzsqULGxzPXjj185v9TeWEuS/2+L9igHrL0s5+N69v3uhWECZOSWPVyU9E8qM//HgwdZjY73VGcmR0jmIJIgo2wMARAKABiIDkgSIDJA0IIRl0DIJkhJEXgRTmusnva+0ZJimrAVQSZLsmZF36gYTQa9kTkgIQCHo6QwYOLKtT8n8SkGCsmamtS7S/H8JGHAgnQQeGTq4tSPRVfVe4mxliiUWrANnDPfu/d0LK8n7UoD1ZZRQ9v71Hbd1L5b6kqlNeka849W/Cr298cLwjMcAQFwHIHP9JOb/O89ZYtqy0vyYu6YodA3ojgT9B7RDGyWTqz5NYlxMuF4MHW6K65qDSAdjRm6DMiur7LFSsfY2iRTw9PShtvf1zuqO9PlKDdoCPn+8fnfs6ztu6y7hUW9GCb0iSgHWPXYPvKFm+/RiSXpJh+YYzaTdrybe2fhW11hlRnfCIAamApJEQVDN/5fBNGYhYW6PrO+yICCWhvJq+PSGSc+QdzWDyuAaf2TmiS1npkaqdF0B42TCiBgAbkHKXvIGIyVn4evSgZExJ54Nv97aGRv29WaGCjpH/3TX54dvqNk+vRIYsAusb6KEVJg/3/PFojsP8hrqlCfuf2vqfM1r7017NemC4ICQHIYwt9hZNZhTh3ke3VmDg+UMX0BYxyoQQkUyxXEuPOV/PPFcq3SlVqVKJBDO8JOBE5ELtdEYg6ZLGFICxGF2/+aYbSxjg5HMAGcSkhgIbmSEC+93OPGr4NGmCzPjnnE96CqVVwVoC2y2ULIDLA+AP7V75zu33dq7WI76jJpy97l6qg+OHm2MpARPCw2CNAgpIAwFIGWB6psPMtOIVUxwEVlgZCDygKBCEmFqiuP4yHjVBdldUZpf8BIZ7EpCPTB+rL5rNOnQBWCQBEkOs628syRQZaEqhbUOLANJHIw58N5A0Ptm9Gj9ueigN6Iv9M7vDbQl79x2a28JN/pT2Gj+ZgdYfwyb2aCtvoZ40WoahViyIuUOUsb9an9XTSSlKwZ0EFIQZJgGu5SmC6EAmOaDTIJB0lwTiqRqAQwgydE1knIddb/TTHUz7tUELgnBjoYuVPzywvv1oQiDZBJmkoLDMtYN2ypwdhNgfgACmOmtJwhkDMneGj9f9+702aoebcCbVmMLwHXPntsHW30NcZu3qrUwcVHA4gD+yO7Lfe2qz/YX+5vGhTLtD/tfSr7d9P5Y2GeQ35T6nKwvp7n7IzIKqsC5NpY0j837v9mBESKnLXWD46kTnTXtdW82swp91YR7ZtSg61nxdFsoKhTGGUhhAJiVDJA2P6zULwIHgZnnEQCkwJgAkYLgjFAOJ040nneeqhlOhJyl8q4A/dFS2FkKWF8D0GDXYC9WTMq8UknXpDwnJyd8x4aGK9LC4LpQQKTmbCpLzJjWRx6IFoLKtE+IGQATyMY8zE14EkS6ZacAJCQmpzh7/tVR50wstSp2iJIkOxcZ8bzWOVopDAbizDK+s+pPA7icI2DtdF2knIuemSYCM0BSAuQE4y5cmIy5f3Wut6o3Pu6eofCC6MTtrTdNlWDIN1jYWDaw/pPdBfvqVZ8tWlAaRcYxUj0QOMXbG8ciMacmBISIgwwC6RwEyjk981VhIRU4a7xnbSsApJjANLeIlneemaFbA3greLa+W4xUSFVcdo/8iD7u+t7A3+9Ox5j53kKAwQkw1fyiKHKZm3ZpqlFScmvEIKGqThCpSGkSnZGhyhP6e7WjybCzVB6Wio3FnvxzAK62c4eP1e0KFgswG1zwsMw4nj8+6HurY9JjSAkh0yBKgygDkgJkmKCSeapwvsSa/ztkcUTSys/K/k2CoEGSgGQEjQGRKMd3xn68d6qlpxYMl01y6aTzlxJvbOgfyzjSBkCSAAEYmgYpkiBp+bAoHyz2jXfTHBC5CxAENH0GuogDkhAM6crJwQlfd3TMM5qZWgCuTzfui3ysblfQ5g2vxiIB6sWA9Qd2X+kr224ZLh6u0NVhNuHvT4z5DMMsVaKcypPWzygOoCJSa+7f59tkFnfItOF0CUyOM7x+sselk37ZgDUqx9yPj7/YlkjPhmjyRPCCH5fjxJh7cr4UN4X66Uh/9UvhY/VD6XF3mhbGExfjZSkYKQasFtjsCnNdYGuomLTSnbo67Y36ujIDlRPGuH++BMrt8KQsCppi/qxCXvkFPxNgOt8Z4ikFLyovbJ/kY5elT3qGpZS/c9x7w8AQBxgzWc0u/U41nQJ6EsMV57WeirAecxSSWtcFtoZsXu53UGQ8SzFgfdHug36x9eaiM/mS0JX3031VrwTbG0PhwqAq5FkvJrWKOUwXPUcwcCggQ8Wxdo6fGn+724B+SW0tgmRn2enqQ4cEh+GALhnAL8+cSCJgJB7yng0N+0czQVehcM9iPLWLlWIL/O/sXLHJU5MsthMUkCzKMs7eyahrZFQyBuQkUzGps5TUKiqZiuyezHx+AkiFIAMQDC8di3t6XOcrLyUzo1VDnkcHXtuY1hhSwtoFcmZvt1fmPvwEhpmogvPJoapzyV5/OLPQaXp7601TTZ4au41Y/p1dYO2DWSSxJN228cbxYo+f8aSdIzLs7YpO+IkcEHm2VL7qW9RAX+LnxcCVdWEIIaHLFAQkDCLEdeIPigevzTjjl8yv9UL9Q7ueO99VmxAwc9hJQhry8vhsmQrOOM4MB72nxkZ9I5mJgnZncd4uoP0oMBKvELB+2+4z3rHl5omCG1+H4CF/2HcWZ2r6MkMVgrjlISgupUoFmJ2/s9wLkmXGcmQyDK++Qjigv9R0KfiYkCnlxw/PuPUMmw0q55yYl4FIgBSCIKBHdAV60gO+BCVUu7wtQr9tB1i32XWIFutOrKuG2p+a9B0OndwQiemQlIYU9kBkB2CLSa/8DRHlnKcAGLNCJh4YguP/HH2zOUkrG6DWyWC/CD+zOZLWHCI//CRheT0uvY3FHBzgpmNiOBnyDokh/7A25hYk5jxMm78xU4LD9LalgNUCm5U3tzbtDxZWgsTiatI5mgi7B3oJCiMQtwLHJYCoVFAtOB+ELPssL6r1hA5w7kIsk3Y+HH5ii8FWzpA/lmmv+cXgS23ptAoingOSmWCsXCaXmgBJBkYOhELAqZnztRciI94UpRW7PC5AN87fHc5f1M/YfbzPN39sqpgnZYIi7vOJgQohGUQWUDTXvrIDoqVAVdCumvd7mQ1xSNNhCKRBEtAyDE8NvNN80tFeX3ZtA0KKJZSfjT+9dXoCEELklptIsWRVfi7opTHcAYAMgATPJbSdHAh5hvVJT8gZchPmJkYW43ER+sxiwPqkXd9VsYkPhi/lCKd1pSM0XKGRAhIcJOxJpVJBtbjkMhksSFr2nWKFgdIAT0NIIBTleHTyhVaNZcortRixl/2PbekcC3mZ4OC5jEQ1D1KXo/sSB8gJkFlSpwGIZICZ5qmGSTnllvMMvzpXpVGCT+uTiwHr1+xc4eP1u4vebAwRT7/jXGByymBMEoQQVtZC8Z1gqTtCO+ow69lnOW90FmCAFGYEQNcJxy/MuF+mF8tqyEcrRt3/cOzUhpmoZJKckLkKI2GGXRjBLEK/1KHL7PoZ2XxuAMD5gWF1ZGpGKbShWIzXi2En/82uAtBs5wqf2rA3XHA3qAoezCSdh7rOBYQgq4rXzLWy62JYbNe41HEF1WPuZ2HpAQXCUCHAICQQS0j+8OljTXEkyuJ+MJS08vPgs1uGp1IOTQc0IkgophqEsLztHCyXJXrp1GAue8JKLbLMUHRcmHLOxHQWUhZmmRbjdQFqtjC0AFgftnN2wOnPFCuTz0DnER5yjUdiTpCEgAAxOSsxbOwGi0ugpf8taIMR8hwOZL2yG4y5IMAhhIpJbcb3j4mfl2Xy2GDboca3+s/VxmJgZpqwZpaoQct7GA7gcmVM56+DuWueSQCDNccbumMjnvmAvr5meyLg9NudTfThQsC63s6Ze6pai5bJ6waxkVBC1TQwXc6mv0gh55Z0AbbV4MWAioiDwC1QZd/WsOrzHXA43BAQmAql2OHOibLEEB861FXVP55UFYWDc5ar+CAIy/DLetdKzxItq62Vx3oFHK+eGakYjyRUYsRK4fk8ur4QsK6zc+a+QFvR7nkhX8irCyCtMUhSIEU2D3v5gLKr/haek92FOczXZJbU4hIOVQeYAFEaXNGwZUNl6kfX391RDpZ980P/ofeT+5rjqkvA6ZBQGQcjh1m9zfK2/EgXBdaKjlNm+WzPpkMzhCIG15SMkqSkUgrP5+/rCgFrjy3/fWBb0VrBiUzM9QY7tGXWy46cm6GULIalQLY0qCgPXFlnabYOkSCMNCq9GXCWwY7G6uQz+/76SCUP6MVcB0RmImL+pxjzq7Wm9Her//z4F/bumvR5QV6HAyqrMAVXrmZN4LJlhWXz4mGV8FsqWUhdGUuPe1L6wqD0YjyfL9yyP2QN1o2wWTBxfc32gkn30qUpiZhETxdBkm45BBWLuSJnMNrxQZXvdway9YZWngoUACqT0I00btrvT/+w6n8dXbj2kglIaMgoKUopaY0g57U1c6gMXsUtPNwtFMbBMbdl4z2BP+5svOlvdj346pl6j0zzuC7nSY3LSSJPrhAkCJoGxOKSxSiu1mNud+ZiPC9AtRaWRrPA2mHnrAZ3darYDOVp57Q36hvxC0OannYBq5EHm81lt+nULB/QsiJzNh+cMwc8qoHNNf7kfFCR6V9icWXGOcaHvINTCXUYvZUjkxpPJM1iB0kAZxK1AYW2O7dGG6o8xlZHa6KW12gqUyjfm/4V+i9nozf8DR4+fLqBM9PzISk/wS/fBXAJ1CCY9dXKOmeZpZZNV0zQPVgxpI3NbHW1zMlsqHb6RIO7OmWzK+COfGDZ6g3e4q0rmkoxmUypb8wca9AlwBWaLZLIBsewdIrLYscsB2iz9zaNVQ4VJDTU+92pJ65ZKKkyLK1MKpOezsiwr933q+a3hif9Y6MAJEEzOADTuch5GjQi4at6G7s3V6Vvdd86cHVgc7JZ2ZisZBWGwmal1x/7/8vZ7oYf4K3Jjg2aAegGg9mpL2vA06XXhDlpxXKbGYOAM8m+wE2JxBgqCvPeJrC2AXgtC6xWW44Kb33RFo9pjTAy5JSQHILMHRDLlWgZi4JpJYBmfj+tLFJOEFIFVzhcjjQe+dhfnpjPz5RMK8P6pPs18VbTwbETG051JVQiZtlmZhAma3xIK+MlFQLeCEXcZxue2PkJsSP0afe/HNnnuypW7who+c1QHrj2G2d//9y3/Cf7gj4wBRqZXvhLn+CQNQ8YOBympLI2qUIAA0OAVgVIZjBOKs3n/fGQrVYPrfnGu63+nZu8temCj8slE1znUAwuSTGLBEia+pCE7SyGYkb8UmGdgkAjAmNmUgMJBoUDjMdx8+5NkUqaNdTNIE9aGdYm3QenD2947ER7w5kLCZWIzJpHlk3BUazgtpan1E2uTAWBA+fO1fxi5EDLmXifLyTDTom52QJ/tvUrnapKUFQBpkiALdwVrqwaLCS5aI4YYwCkM6nO8GmnXd4Xgkk+sBrtnLHRU1PQUUZMsowadyQQc5hVMtkMA2F95qrGpcBkF2iLqsRsvJAAMAbGdVTXCXz1Q785MFdRSjbOJzwvZd5s+mXf8aZgQjokPABjeRKFwEiCQZ9VXyzLCgc4d0LTONrHRqoejzy75bw4X5GScwsVWv0NmS1bGYETOMsz+y4byQUmnq4DQ/6O2jF90m2X9wWoMR9YtiL8je5Awc67hpSIZjI8mdG5WSqfV4plAzR2Y4F2pRfyVBYAk5HSwL+o3T69ZfqGcP7uL6bOOM/Fh3yHptqbhiIJR4Y4BLi5q5UMkNlUQSNvN5UVWGbMzzBU6IYLyTRD+9hI1eGpzsCkmHYJGDn4uLRK48vbf6NXEIHzhRvDSymtYDVSycV0Zg0HDEQmvTOJhUH5YrwvQPX5wLLVAa/eVVnY10NAOmlWgDCriJSyDTuyNYCEJQPQ5QBb/jOZOWAOME5wOCQ+XX/tFOf5m26JUTbkPe471HKuN6UIEAxKgVja3NGSx3QgUoH9G+XbLNICsYLgNMMJ7VRDn+z1G3KuOvyUuG3kumuZqZ4v+2gpmvU4kdkqWAUwPswpk2a2eV8o6pcPLFvFBQFn4fktRIAwAMOQOZuEwOck3ZXqWV8O2BZKNAcknGAckJzQylsSHEruYA0ZZXAqob7eMeHTdTKzSphlG1o+HiLD+l5wEJQ5VpF5Hx1mv4VMTr30jiWcQ9MJdRqhObaWwjiuxQ2jwgAYc+SkxaWVVvPd8EoOBgxAKoEFPrvFeF+AKvOBZatBWYWj8PQDECAlgaSElLq5lc62IyKAJLO6wCwNJruAKia15nrdzfuqDkLDBkYVskrLN9qTlFaGWX/lxJj1m1wPCRMwRBlLIgEEZY7/ibI9uoisHhLWhyQmg8Brzl+19Yl+n6DZ5DkFCtUZmxIOBwAmLyOYMGfzYe5yTDhIUViaFuX9QvLmA8tl6wzFKYsJVZKmCpQWYyUpeXW53GLy0nFBu4Ba2nVhgoNBh8dD2HcdwevPM5kJSGckhidmjWwmmdUdMCuJrKYjuf825gVyrbx1Ql4GOwPnDOf6k46piMZF/nMyQl2jYIoTORvn0kur+bn2lrRSTOgLYgXdIMV4X4Bc+SEdW7lIKlcLroLCgapqQk2AkBHIMwznxeys31EBpzMtMGRo1ozJ3x7TXBU893pzy8vNng6mJGnbKpl3kBEy+V8G0y7Utew2TQGHNA31rMSDYgKKzz5IVhqauetG7nqMzN9JKRGNEGna3HfknKGuxgdVZaiuopxkoMU9mTacnfbPKRTeIbO6AwoAr4tQUWGf94VgYhtQtqSZm+EjH5VMcQC6RlAQt3ZN5o6KSM7dhFhAoKV2RzQ3GES04I9zfDJzBAQDdCFRVUW4afLfXPBEC03KYmBk9Y4397hguedimN8PgXKjIvJ3VuaNJZym+wFpCE0uUClMKrQ1sz38+X9NmJoGIGj+d6U0MJV6Ipt1MzDrXQkCQgIOJyAyOpqc3JwUfZGk5lbTzJ9YlAxpMKfiWPA6KlNol6st8iF8o11m8rBDWCidaJ6EKrBQVOQXVGjXUHR9rewKDlRGq7QKUa0zUgps7DhU5rK84focA4PyGmrk3iXbJii/LQxlv0DCknqmLCv0YBsyW5Jf1/7X4RCmXFQsgXS+mr/4+E1hjOUc3ObrMCcAyaiyYqGhbkjDrufNyAdWxg6wkkLjTsWxwIjjpNCG1OYE1hgxAJxLEE+CBMtGzkELjqK8FBwDs4lys7n05kIIgNIAERxOYrxAkigHpwDVagHUarbs63LZ6XZJKc57m1fI5Bvvtur0Y3pSwTohBsDpYKir4SSzrScZzSZ4snzJp1jN3WZVILOqbsyuhHxWHTMJA4QPbXWKQKVCnLF1sV4l8D6ZDyxbGYJhLa6uG2AxBp/iEdud2yL+SppVEKTkWk3OglBaM2zy91RmcYaZpeCwHKmm+vM6gFuUX++7yrUlkZ/psJapBN5H84FlqxIjmIk6sI7IxVyiwe8zrt7YkLAcBRZA3DnLIOu6MEtvTXixnF0lLVWogDMXOFzgxLCh0qvXOCu1el6XUZiyLoBVAu/D+cCyVUo9ng471xOwFMbR5mxO3uL91NCGepU4J3BOpqFBDqsLMfJ2hsxSf8ilGXNOUJjZwF+BgNfNcEP99tDOyuakuk5AVSLvg/nAstWyZjQVcq0nYHFwquEB7Zra5uSnWz807XFLKNwAY1Yf1Ln+VMvxa3WuyXkdCKqiw6FqcLsNbKuvTt1Uc+10k7M+4+COdQOsEng/ng+sETtnjCSn3VhnpDKFNvHG1M2uj45d27ApoqrCCuXo81wmzJrzI7IxW4BUSFIhpYCqSGwM+DP/vulfDVzr3xmtUHzGelqnEng/kg+sATtnDCWDnvUGLAaGSviNvb7tsS9t+q3+T+/aFGlomJ2NiKzZni3bZzTPQSfgcRO21QdSv7fpN/o+WrV3pslVl1GZSutpnUrg/UC+H8vWoJ7B5JQX65A441TvCGhqJeCu+PXBLerZ6hMNpzf0jMSd4yEzzMOYkfsaSms+pcdpYEOFX/tIU9vMTQ3XhK5xXD3T5Fx/oCqR9z35wLI1FHEyPeOZ0RJKsUqdtQ0uhgCr0q+ha2aaajelrhfbY4POmHrkml+1nbqQdEQjZsa1ZgAOD9juHU5xC/16X42jSttZtSm50VmfqVD8hor1B6oZLaHYLKTIYSkLrFEA07BRW9ge6vYvNo1+bRvzCvmYT7hVV6qRN6R3NoWcOyiQubVN41rG1ICCAMaBmmqFrnK2JepZbUblKs0v/VpP1B7q9ts8dNrC0pwgdAdsTFA9Ee6pWK/AyrkhoJLCVWpAQ6YWdZoM0PzwHThnUBgnBQphndOJcE+FzUNzbQrygXXSDrBOhfsq8QEhDoU4U2idCiLbVALPT86uXZ7EswXJyEDVels4SZJNiilnh+yoTDsiDlpmPkGP6PaN0LBnfqPYtU4l8Ly9kMQ6YufMsBZ3tYe6fcV6ZK01IhDirpDzscgTbQ8fP9q4o8Ulvvrbt8x8JHbLAHW5Y4yZBa+MmcGc2dHCVldAMviEMuz52fCzLc90nGn49c9soa/U/ZvOtvDOKYXWvppsD3X7wlrcrnP0SCFgdQEYgo2ufq9MnA6sF2AJCH5G7696J9bTmEkznO2TytfvP1i7e8cLtdcqN47WaU2Jho0GCwTccJFHZFhaiSVSmA4yBGNp5TSdamjvm/Slk+aE12deHGYb9pyq+MrG1nAFW/tO0lcmTgdsHjpkYWgBsADgDQB3LHWFt4OdNYtNqV9LlKQUPzx6ruJk5ww0DUDGgMMBnDjNcUqc3OhwHAPrJqjO2doJKYBMGubxnIMzBTpJs+eWAbw5eLbqX9Ve57natSPO13h2w9vBzhqbh76R/x/zgfWqHWCdDPfWTGWiarHOyWuFDDLYkcj7Vc+Mv9qcToHAGGOMIaMBIMVUf0IBSwso3GxWLSW3Ko6YNbTTzMECY7khlj2p4arnEy+2bPY1dFeLQGatuiGmMlH1ZLjXLrBenbvxmUsv2r3pU0OH69a6tJox4uoTky83j41bPUxybS3NRiaSDAgpYEhCxjBL0IUgSJltImd1hJbSrFLSzQTTRAJ4ouO9+sMzHdUGXf6prsulEnn84mLAGgRwzM5VDo6dqF/LoEojrTwjn2ppD/ZXCyNnyef9kBvhutDcp2wuvERemXfuR0MC8TjhwMyLm0IyvGZz2Erg8TELO0WBBQDP27nS8VB3bV98fM2m0YzrQec/dR/eHAmXpqZmaxbzP3OJccAQwMmRkcp3EkdrNdLXnNTqi4+7joe6a20evgAzhV74Gbs3f6T/9Q1r0mBnCfVZ3yM7hwaJkeSQcJQAKht+MZiNRSamGH7afbB1yHneL+eNE1ntVCJvn7EDrFMATtiC6eixxrUGKgM6e9f5yobnj/VWGwaDWZbMlwRUSRXLxECkQAiOnsm46+nEc61JxNdUIUoJvD1hYWZJYAHAP9m54lgq5H1s4M01ZcTPyIjjye4jjf3DAgLM6qGgX7SUmqMKrRoqphLSGvDUye6a0UxwzZgNjw28WTeWCtlNkymIlWLAetTuQzw68PrGtbJgkgk26D1X9U7XhE9KQJIKQxjgBdoSlCyl5pwrAQgIIjAVmAgS+5/jP9kdEWujyqlEnj5aCrAGATxt56onw701L4+fWhPxwzCizj975//tSCQkF8QBroKpKqRx8VIqX145GOBQzBwbw1DAmBPHuoLed413ag0Yq9rWenn8VFUJvqun5+8GlwIWAPzM7sP8pOfQ5lVvsIu08t0L/7B9fDKtSpj9qYgykELLtlq5KCk11x1hgCSgwgGQB7rhQirN2Q+6n7xq2phZ1e6HEnlZFCOLAetZAGfsXP3w1Nn61S61hjNj7rPR3uqEzplODJIMs68VmX29ytlOKKtYRW5OoQIhPBgaMZSH5AO7Co0VWS3S6vDUWbu+qzMWRkoGFgD8rd2HeqDrhZbVCqqYjKv3R/5218B0xqFJKxmSCZDkVo1EecN5EoBhNfcFS8Hs6sIgJNir7036h43RVVmUUiIPF8XGUsD6EYBJO3c5HuquXY07RJ1p/C3fc5tPds14dE0BkALlem9ZnvOyAovldYTPOlANMAZkNIbxaFL9v8b/3Z6gxKqSWo8NvFlXgkN00sLGsoElAdxv9+F+1PXCllVnsMuQ84nTJxs0Q1cMaYBImwUTJ6tPQ3kLvFl+G6PcLCEOxjgyGbDnTwxVHvA9tkWDtmo88iXy7n4sMRPPzov9b5hJ8kvSQGLSf2/HY6tGJWqk8wOh1zd0DcWc0YTZH4ZxANkRbyzb3NVRZmBxq0dWlrLtkVwQgiGeFOy5d8d80yK0KloW3NvxWMtAYrKUgon/vdRBdoCVAvA9uw/5UM/BrafDfZe9/lCSZF16l//x88c3TCU0VZLZvoMznteSaL65XT5ozf5vdqeomyk3cEDXwDqnJnzHo2crL7f74XS4z/tQz8GtJZzyPQsTFw0sAPgugH67d/6Ljke3XW5gJWWKPzH8WtNoasarEbOMaQYpZ9tgm3ha3PO+TIdDLjcCc6SW2SLcMBRMp+Kuv+t/rq1f6aq4nHHEEnnVb2EB5QIWANxr98Djoe7a75196rL5tgQJdtI4ETge7qqJJh0QjENygEgxm6hBzM5EQbacvpywEtagF+QZ8SIPwCqEwTAYirqfHny3PkWpy2Jrfe/sU5tLMNhLwkApL/RTAK/bPfiHF57f/naws+JSLxaBEHKPeJ4Nv9LcH4q5DBKQubbaHLNttrOvz1bgGQrlcWUlo5YDciIl2Rvh9sbj7J26S60S3w52VvzwwvOlDFh/3cJA2YEFAP+tlIPvOf2LHfIS9zHXmcaPpM7VHusd9yVSBOJWz1BpuY6YbrXWntuf7xJYfRag9JwxbwhgYDzpeKbrdG1ExC5ZHFES4Z7Tv9ixkrwvFVhvArjP7sG98fGKu479aOclWzAINlj9fs2B1AtbBqc1hRjNJoLCMD9E1n9n/3D5htoQVESTCk6nO+sPG+/UGXRppNZdx360szc+Xoo2uc/i/YoBCwC+CaDb7sEHx040fefM482XYsHSzqjjldH2miPHEoqUYJJgzsqFtFSQWMBa4HLPsVEwMEzspcxrm0cqzlautCH/nTOPNx8cO9FUwindFs+x0sDSAPxJKSf8uPvAtkf6X6tfWWklWV94yvnO2XFvMiGtyagKCg0BWB2UbfNtgEng5SNTvle6uysyyKyYIf9I/2v1P+4+UOqO/U8snq84sAAz+HhfKSd8+9TDu1cyUK07U2pn9dGmI6MD1WkBMK5YWQurNUuFwJgEYwRDcIgMx9vD3VWjidCKZD+8PH6q6tunHt5d4mn3YZFA80oACwC+AZsVPdmv6N0nHrq6PdTtK7t7AYK9n+6svP/1VzbpAlBUZjazgsTqJSu9hggMThjChfaZc/Wn6FRtRpY31NMe6vbdfeKhq0v8lh2zeIxLDSwAuKsUHRPVk867jj2wpzMyWNbofsSIqc9caK8NThMEA3SDYHYXWo0qcCEZpMGAjkgS+OuOJ686lTpXIak8tlZnZNBz17EH9kT1pLMk1Ju8xeUC1gkAd5ZywmR6xvOlI/dfUy5wCRKsI32u4s3E0Y1pySCIm3FlotUwxtS2zJUwIIkwFSI8H355YzncD52RQc+Xjtx/TQnd+LJ0J2wW1KwUsADTafb9Uk4YS4W8v//ufXvLoRanaNr5QPjh3YNjDIT5FTerXWKx2X+sZAghgFfG3t/wPt6rvhj3Q3uo2/f77963t4SiiCx9HyU4QlcSWADwX2EzRz5fcv3Bu/ftuxiDXoPGD/BftnZcSKssl6WQHRK+2qVU1t0wb0oYB0YngEfjT+6YVseX1f785fFTVX/w7n37liGpnrZ4idUCLMBsJlKKMY+onnR+6cjfXLscVwSBMKx0+58beHejlmYwhCfneDB1YXb6DS/za9oFDbOx9MosuKzzDEOBSsA7x+KOF1OvNmkluh8e6X+t/ktH/ubaEm2qrLF+R7lWoJwrngJwO0rIgsiu5rdPPXx1qU7UNKWVn48+29J5BpCGApU5AQiAC3AHgXEOggtAdi4OW8BzZhsE86VMFqysAJjyhjYVva5qfazgNMuKLAUKXDCkilQGePjsu01B3X7O1nfOPN787VMPl7r7g8Wz22EjHeZyAAsA+gB8ATYTA/Ppx90Htv3Hoz/caTe2OJ4JOilcm95RW5Os8AEGJaFwHSzb4D/LfJYdBp4dWqkA5ISZNarmzfRS8j487998wOQ7W+fbb/m/M0NFzJq9Y4JMxdz45CzvGcu/G4ffDWysqEm2KC2RweT0ksCSRPiPR3+4cxnOT1i8+oLFu/LJbCKzDWKZ6SYA/wzAX+qJW/2NsXv3/u6Fj9fvji1qo2XCjsH0qOdcprvi/fBwxQW6EOjojbkMw2IpMRBjyHWEoTybJsdUgez0CQ7FgoksAByyLc8WbheUeerYCkYzBQoUSCJwSHArL76hwYHr/bsmd/naInsqt8abvfWZLZ7GdLF7vh3srLjn9C92lBj7y1IcwG+ixDjgkmZKticUW5lhjZ8A8NxywAUAX99xW/dSXQPTlOZhPeoYMcbc57SeivcGpzxdRldgODntnZkGOAc0OV9VUR4KKCe4WdGdJC/g4mFFbKnsMHU5d9eX+3l2KitnHC7FhbShweMktFZUpXb4WiLNtZXadf5dMzs8rck6Z7XmVdxFtyHfO/vU5hJTX+aD6rcAvFZuxq80sLKS62nYGExQiG6o2T7953u+2LM30LboBFiNpXkoE1dH0kFXd2bAN2gM+U9Hz9e8NxDyJtJm03/MgVVW1RnzgDZf/qjzJE52vk4+4BTM7aWVnziYVX/m7/JvoXIGJ+do2wZcV78lvCN+/cTOys3JJnetVu30G1VKRdHsw9PhPu9fdDy6rcQkvfnq73fKLakuJbAAYD+AJwFsWe4F7tx2a+89e24fXOo4nXQWp7g6oo+7u6Ij3sFYyDWWmnH1s57qC8Ggb3omW0FjWjMSApQ3vX5WSGVz4i0pkx3Zmy1ApXlSkGf/bqo6Jq3FBYPCzPMVRtBIwusGNjc6xV523XhdtSo3OhrSW2qrtW1qW7wBjWkHX3xkyr0dj7WUmKNeyFD/wsU6QFcDsACgDcBjAG5c7gVafQ3xr1312f7bW2+aWupYgwyWIY1H9aQyKaZcA8lxdyiRUYZr2xtePTNSMRMTSkbXuKEzSFKgQ5o9HKQ0i0xzact5gzAXGFBsrlWVZ+crAnBYE8O4AlRXAyLt1q+9Aeyj4c91ez0KNXvrMy3uxrRXcQk/9wkHU4mheCPcxwberPtR1wtbSqimKeZSuL3chvrlBBYAeAA8YongZdMNNdunv3rVZwftjl2RJJkEYUYJurrjI57xaEJNK0nHeDLoisaIBd2DFWfSfYGxcYAkIW0Ooc8psXxbizNpLdwsvrJWkw6ztEzhQHUVcPUuoG3qo8Me5jEa6lVUpjckfR6H3FbZkN7GticIBA5OS639y+Onqh7oeqHlItRevvPzjnK6FFYLsLL01ygxn6sQfaxuV/Ar224ZLmWuDxFBcsGSMqWkdJ3HZFwd1sfcwWRCNXTAcCXUAW9HbX8k6J0c5WT2bgeknmfnK3lmGQMcDqCmFmjd7uKtYve0b7IxqqqMKvzAJm+N1ojNSZeikkd1Spf0mC25bLiZXh4/VfWTnkObS+ilsBh9v1we9dUMLAD4MoCHUIZkqesCW0NfbL151I6KXFSyMYPN8CnnmDHpnkloXEszSGkCi/JVYL4GZABngOoAvH6g3ltlbKCmlEcsf3DAYwNv1j068PrGEloJLcpjmAHln15K5l5OYGWN+gcvxu7KpyZPTfK2jTeO37Hl5ok2f2MGa4j64uOuR/pf3/D86LHGZQSNF7On7lpJI321AitLPwBwdzkveEPN9ulbm/YHP9/8sanVOuRgKhNVnxo6XHdw7ER9Geyn+XQfLiJJb70ACwA+Z9kB28t94esCW0Mfr98d+tSGveHLPf+nPdTte2XidODtYGdNmVTdfOq27NdnL+d7riZgAWbw7rvlll75FHD6M3uqWiP7Am3R/YFtsetrtsdXagzxjJZQ2kPd/hPhnopT4b7KjshAVQlTtJYrpb6JZRQ+rHdgZekmAH8JG0M5y0EN7upUi7cu2eytT23y1qY3emoyje6AVu+q1ANOv1Hh8Aqv4pSq5bg0pMGSQuMxPamEtbgazEQd4+mwczQVco0kp91DyaBnMDnlXUYu1HLpdZjFpG+uFgYSEcraInEFdo59WJhOcOVjfvqsNVp1tNqBlaVvApi6AqTcZwrLKCC9AqzC5AHwZwAmPsCAmrDWwLPambWWgJUlDuA/w5yW/kEBVIf1zmtm0NNaBNZ8F8VT6xhQT1nvuOZorQMrSy2WzdG+DsDUbr1Ly1pmyHoBVj7tA/DfARxdQ2A6aj3zvvXChNXqxyqnJPsMgE8C+DUAzavkuYZgDuZ+Fea428H1tvDrHVjz6SoAHwZwPYDrAOzBMlOmS6Bpy/g+aam5IwC61vtCf9CAVYg2AtgBYBuAVgCbADQCqAcQAFAJwAvABTP3DzBzmDMAkgCiAMIAggDGAYwAGADQA+ACgNEP4qLmgHWFrlC56f8DIuKfm+a8YikAAAAASUVORK5CYII="
  },
  "clash": {
    "label": "Clash",
    "data": "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"
  },
  "cops": {
    "label": "Cops",
    "data": "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"
  },
  "faschos": {
    "label": "Faschos",
    "data": "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"
  },
  "infopoint": {
    "label": "Infopoint",
    "data": "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"
  },
  "konzert": {
    "label": "Konzert",
    "data": "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"
  },
  "kuefa": {
    "label": "Küfa",
    "data": "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"
  },
  "kundgebung": {
    "label": "Kundgebung",
    "data": "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"
  },
  "kundgebung_star": {
    "label": "Kundgebung Star",
    "data": "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"
  },
  "pfeil": {
    "label": "Pfeil",
    "data": "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"
  },
  "punkt": {
    "label": "Punkt",
    "data": "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"
  },
  "star": {
    "label": "Star",
    "data": "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"
  }
}

COLORS = [
    "#e14f9e", "#ff1414", "#f2b000", "#ffff00", "#00dd35", "#009844",
    "#00aadd", "#714cff", "#2046a3", "#913f0d", "#ffffff", "#222222",
]


MAPLIBRE_STYLES = {
    "Standard": "https://tiles.openfreemap.org/styles/liberty",
    "Fahrrad": "https://tiles.openfreemap.org/styles/bright",
    "Humanitär": "https://tiles.openfreemap.org/styles/positron",
}

GRID_PRESETS = {
    "Querformat": {
        "Locker": (11, 8),
        "Mittel": (14, 10),
        "Eng": (17, 12),
    },
    "Hochformat": {
        "Locker": (8, 11),
        "Mittel": (10, 14),
        "Eng": (12, 17),
    },
}

PAGE_EXPORTS = {
    # 300 dpi, DIN-Formate
    "A3": {
        "Querformat": (4961, 3508),
        "Hochformat": (3508, 4961),
        "pdf": QPageSize.PageSizeId.A3,
    },
    "A4": {
        "Querformat": (3508, 2480),
        "Hochformat": (2480, 3508),
        "pdf": QPageSize.PageSizeId.A4,
    },
    "A5": {
        "Querformat": (2480, 1748),
        "Hochformat": (1748, 2480),
        "pdf": QPageSize.PageSizeId.A5,
    },
}

PAGE_SIZE_ORDER = ["A3", "A4", "A5"]

MAP_LAYERS = {
    "Standard": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "subdomains": [""],
        "attribution": "© OpenStreetMap contributors",
        "needs_key": False,
    },
    "Fahrrad": {
        "url": "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        "subdomains": ["a", "b", "c"],
        "attribution": "© OpenStreetMap contributors, CyclOSM",
        "needs_key": False,
    },
    "Humanitär": {
        "url": "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        "subdomains": ["a", "b", "c"],
        "attribution": "© OpenStreetMap contributors, HOT",
        "needs_key": False,
    },
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def latlon_to_world(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    lat = clamp(lat, -85.05112878, 85.05112878)
    n = 256.0 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * n
    sin_lat = math.sin(math.radians(lat))
    y = (0.5 - math.log((1.0 + sin_lat) / (1.0 - sin_lat)) / (4.0 * math.pi)) * n
    return x, y


def world_to_latlon(x: float, y: float, zoom: int) -> Tuple[float, float]:
    n = 256.0 * (2 ** zoom)
    lon = x / n * 360.0 - 180.0
    yy = 0.5 - (y / n)
    lat = 90.0 - 360.0 * math.atan(math.exp(-yy * 2.0 * math.pi)) / math.pi
    return lat, lon


def safe_enum(value, fallback):
    return value if value is not None else fallback


@dataclass
class Marker:
    id: int
    lat: float
    lon: float
    symbol: str = "punkt"
    color: str = "#e14f9e"
    label: str = ""
    description: str = ""
    label_position: str = "Rechts"
    label_w: int = 150
    label_h: int = 54
    label_font: int = 12
    label_bold: bool = False
    label_italic: bool = False
    label_underline: bool = False
    label_bg_alpha: int = 255
    text_color: str = "#000000"
    label_gap: int = 4
    icon_size: int = 52


@dataclass
class NoteBox:
    id: int
    text: str = "Textfeld / Legende"
    text_html: str = ""
    position: str = "Rechts oben"
    bg_color: str = "#ffffff"
    bg_alpha: int = 255
    text_color: str = "#000000"
    align: str = "Links"
    w: int = 230
    h: int = 110
    font: int = 13
    bold: bool = False
    italic: bool = False
    underline: bool = False
    include_routes: bool = False
    visible: bool = True
    name: str = ""


@dataclass
class LogoItem:
    id: int
    data_base64: str = ""
    image_format: str = "PNG"
    name: str = "Bilddatei"
    x: float = 80.0
    y: float = 80.0
    w: float = 180.0
    h: float = 90.0


@dataclass
class Route:
    id: int
    name: str = "Route"
    points: List[Tuple[float, float]] = field(default_factory=list)
    control_points: List[Tuple[float, float]] = field(default_factory=list)
    color: str = "#ff0505"
    width: int = 6
    calculated: bool = False
    opacity: int = 80
    distance_m: float = 0.0
    duration_s: float = 0.0
    directions_text: str = ""
    profile: str = ""


@dataclass
class Zone:
    id: int
    name: str = "Zone"
    points: List[Tuple[float, float]] = field(default_factory=list)
    label: str = ""
    label_position: str = "Mitte"
    fill_color: str = "#ff0505"
    fill_alpha: int = 70
    border_color: str = "#ff0505"
    border_width: int = 4
    text_color: str = "#000000"
    label_font: int = 13
    label_bold: bool = False
    label_italic: bool = False
    label_underline: bool = False
    label_bg_color: str = "#ffffff"
    label_bg_alpha: int = 180



POI_CATEGORY_LABELS = {
    "education": "Bildung",
    "health": "Gesundheit",
    "religious": "Religiös",
    "shopping": "Einkaufen",
    "food": "Gastronomie",
    "culture": "Kultur / Freizeit",
    "public": "Öffentliche Einrichtungen",
    "transport": "Verkehr / Parken",
    "transit": "ÖPNV",
    "accommodation": "Unterkunft",
    "other": "Sonstige POIs",
}

# OpenMapTiles/OSM-POI class + subclass values used for the broad UI groups.
POI_CATEGORY_VALUES = {
    "education": ["school", "kindergarten", "college", "university"],
    "health": ["hospital", "clinic", "doctors", "doctor", "dentist", "pharmacy", "chemist"],
    "religious": ["place_of_worship", "church", "chapel", "cathedral", "mosque", "synagogue", "temple", "religious"],
    "shopping": ["shop", "supermarket", "grocery", "clothing_store", "bakery", "butcher", "bicycle", "hairdresser", "mall", "department_store", "convenience"],
    "food": ["restaurant", "cafe", "fast_food", "bar", "pub", "ice_cream", "beer", "food_court"],
    "culture": ["museum", "theatre", "cinema", "library", "art_gallery", "arts_centre", "gallery", "attraction", "castle", "monument", "memorial", "stadium", "sports_centre", "swimming_pool", "golf", "playground", "garden", "zoo", "theme_park", "water_park", "pitch"],
    "public": ["town_hall", "police", "fire_station", "post", "post_office", "information", "community_centre", "courthouse", "toilets", "drinking_water", "recycling"],
    "transport": ["fuel", "parking", "bicycle_parking", "car", "taxi", "charging_station"],
    # Haltestellen und Bahnhöfe. Die Kartenstile führen sie in den Klassen bus, rail, railway.
    "transit": ["bus", "bus_stop", "bus_station", "rail", "railway", "station", "halt", "tram_stop", "subway", "aerialway", "ferry_terminal"],
    "accommodation": ["hotel", "motel", "hostel", "guest_house", "camp_site", "caravan_site", "chalet"],
}

# Regler „POIs ab Zoom“: Versatz des Mindest-Zooms der POI-Ebenen in Zoomstufen.
# Negativ = früher einblenden. Die Kartenstile setzen die erste Rangstufe auf Zoom 15.
POI_ZOOM_OFFSET_MIN = -4.0
POI_ZOOM_OFFSET_MAX = 2.0

# Vorbelegung für ein neues Projekt und nach „Zurücksetzen“. Gespeicherte Projekte
# behalten ihre eigenen Werte.
# Jede Kartenart merkt sich ihre eigene Kartenebene.
DEFAULT_VECTOR_LAYER = "Fahrrad"
DEFAULT_RASTER_LAYER = "Standard"
POI_DEFAULT_CATEGORIES = ("education", "health", "food", "public", "transit", "accommodation")
POI_DEFAULT_ZOOM_OFFSET = -4.0

# Was Rückgängig/Wiederholen umfasst (Projektstand-Schlüssel).
HISTORY_CONTENT_KEYS = ("markers", "notes", "logos", "routes", "zones")
HISTORY_TITLE_KEYS = ("map_title", "title_bg_color", "title_bg_alpha", "title_text_color")
POI_STYLE_FIRST_ZOOM = 15.0

# Lokale MapLibre-Dateien (MapLibre GL JS 6.18.0, nur gelesen).
MAPLIBRE_DIR_NAME = "maplibre"
MAPLIBRE_FILES = {
    "maplibre-gl.mjs": b"text/javascript",
    "maplibre-gl-worker.mjs": b"text/javascript",
    "maplibre-gl.css": b"text/css",
}

def _maplibre_dir() -> Path:
    return _resource_dir() / MAPLIBRE_DIR_NAME

def maplibre_files_missing() -> List[str]:
    return [name for name in MAPLIBRE_FILES if not (_maplibre_dir() / name).is_file()]


if HAS_WEBENGINE:
    class MapLibrePage(QWebEnginePage):
        """Kartenseite; ihre Konsolenmeldungen landen im Debug-Log (nur wenn eingeschaltet)."""

        def javaScriptConsoleMessage(self, level, message, line, source) -> None:
            if not DEBUG_LOG_ENABLED:
                return
            seen = self.__dict__.setdefault("_seen_messages", set())
            if message in seen:
                return
            seen.add(message)
            log_debug(f"Karte: {message} (Zeile {line})")

    class MapLibreSchemeHandler(QWebEngineUrlSchemeHandler):
        """Liefert die Kartenseite und die lokalen MapLibre-Dateien aus."""

        def __init__(self, html_provider, parent: Optional[QObject] = None) -> None:
            super().__init__(parent)
            self._html_provider = html_provider

        def requestStarted(self, job) -> None:
            try:
                name = job.requestUrl().path().lstrip("/")
                if name == "karte.html":
                    data, mime = self._html_provider().encode("utf-8"), b"text/html"
                elif name in MAPLIBRE_FILES and (_maplibre_dir() / name).is_file():
                    data, mime = (_maplibre_dir() / name).read_bytes(), MAPLIBRE_FILES[name]
                else:
                    job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
                    return
                buf = QBuffer(job)
                buf.setData(QByteArray(data))
                buf.open(QIODevice.OpenModeFlag.ReadOnly)
                job.reply(mime, buf)
            except Exception as exc:
                log_debug("MapLibre-Datei konnte nicht ausgeliefert werden", exc)
                try:
                    job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
                except Exception:
                    pass


class TileManager(QObject):
    tileLoaded = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        cache = QNetworkDiskCache(self)
        cache_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        if not cache_dir:
            cache_dir = str(Path.home() / ".aktionskarten_tile_cache")
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cache.setCacheDirectory(str(Path(cache_dir) / "osm_tiles"))
        cache.setMaximumCacheSize(250 * 1024 * 1024)
        self.network.setCache(cache)
        self.layer = "Standard"
        self.cache: Dict[Tuple[str, int, int, int], QPixmap] = {}
        self.pending: set[Tuple[str, int, int, int]] = set()
        self.failed: set[Tuple[str, int, int, int]] = set()
        # Reste eines Laufs, der nicht normal beendet wurde, liegen nicht länger herum.
        self.clear_disk_cache()

    def set_layer(self, layer: str) -> None:
        if layer not in MAP_LAYERS:
            layer = "Standard"
        self.layer = layer
        self.pending.clear()
        self.failed.clear()
        self.tileLoaded.emit()

    def attribution(self) -> str:
        return MAP_LAYERS.get(self.layer, MAP_LAYERS["Standard"]).get("attribution", "© OpenStreetMap contributors")

    def pixmap(self, z: int, x: int, y: int) -> Optional[QPixmap]:
        max_tile = 2 ** z
        if y < 0 or y >= max_tile:
            return None
        x = x % max_tile
        key = (self.layer, z, x, y)
        if key in self.cache:
            return self.cache[key]
        if key not in self.pending:
            self._request_tile(key)
        return None

    def retry_failed(self) -> None:
        failed = list(self.failed)
        self.failed.clear()
        for key in failed[:80]:
            if key not in self.cache and key not in self.pending:
                self._request_tile(key)

    def clear_disk_cache(self) -> None:
        try:
            cache = self.network.cache()
            cache_dir = Path(cache.cacheDirectory()) if cache else None
            if cache:
                cache.clear()
            self.cache.clear()
            self.pending.clear()
            self.failed.clear()
            if cache_dir and cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            log_debug("Kachel-Cache konnte nicht vollständig gelöscht werden", exc)

    def _request_tile(self, key: Tuple[str, int, int, int]) -> None:
        layer, z, x, y = key
        self.pending.add(key)
        info = MAP_LAYERS.get(layer, MAP_LAYERS["Standard"])
        subs = info.get("subdomains") or [""]
        sub = subs[abs(int(x) + int(y)) % len(subs)]
        url = info["url"].format(z=z, x=x, y=y, s=sub)
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", NETWORK_USER_AGENT.encode("ascii"))
        request.setRawHeader(b"Accept", b"image/png,image/*;q=0.8,*/*;q=0.5")
        try:
            request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.PreferCache)
            request.setAttribute(QNetworkRequest.Attribute.CacheSaveControlAttribute, True)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        reply = self.network.get(request)
        reply.finished.connect(lambda r=reply, k=key: self._finished(r, k))

    @Slot()
    def _finished(self, reply: QNetworkReply, key: Tuple[str, int, int, int]) -> None:
        self.pending.discard(key)
        data = bytes(reply.readAll())
        ok = reply.error() == QNetworkReply.NetworkError.NoError and bool(data)
        if ok:
            pix = QPixmap()
            if pix.loadFromData(data) and not pix.isNull():
                self.cache[key] = pix
                self.failed.discard(key)
            else:
                self.failed.add(key)
        else:
            self.failed.add(key)
        reply.deleteLater()
        self.tileLoaded.emit()

    def _looks_like_black_error_tile(self, pix: QPixmap) -> bool:
        """Dunkle Kacheln sind erlaubt; nur tatsächlich leere Bilder gelten als Fehler."""
        return pix.isNull()


class IconFactory:
    def __init__(self) -> None:
        self.base_images: Dict[str, QImage] = {}
        self.cache: Dict[Tuple[str, str], QPixmap] = {}
        for key, item in ICON_DATA.items():
            data = base64.b64decode(item["data"])
            img = QImage.fromData(data).convertToFormat(QImage.Format.Format_ARGB32)
            self.base_images[key] = img

    def pixmap(self, key: str, color_hex: str) -> QPixmap:
        if key not in self.base_images:
            key = next(iter(self.base_images.keys()))
        cache_key = (key, color_hex.lower())
        if cache_key in self.cache:
            return self.cache[cache_key]
        base = self.base_images[key]
        out = QImage(base.size(), QImage.Format.Format_ARGB32)
        out.fill(QColor(0, 0, 0, 0))
        target = QColor(color_hex)
        if not target.isValid():
            target = QColor("#e14f9e")
        for y in range(base.height()):
            for x in range(base.width()):
                c = base.pixelColor(x, y)
                a = c.alpha()
                if a <= 0:
                    continue
                # Die Vorlagen bestehen aus schwarzer Grafik + Farbfläche. Alles Helle/Farbige wird zur Zielfarbe.
                if c.red() < 55 and c.green() < 55 and c.blue() < 55:
                    out.setPixelColor(x, y, QColor(8, 8, 8, a))
                else:
                    out.setPixelColor(x, y, QColor(target.red(), target.green(), target.blue(), a))
        pix = QPixmap.fromImage(out)
        self.cache[cache_key] = pix
        return pix


class MapCanvas(QWidget):
    markerSelected = Signal(object)
    noteSelected = Signal(object)
    logoSelected = Signal(object)
    routeSelected = Signal(object)
    zoneSelected = Signal(object)
    statusChanged = Signal(str)

    def __init__(self, icon_factory: IconFactory, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.icon_factory = icon_factory
        self.tiles = TileManager(self)
        self.tiles.tileLoaded.connect(self.update)
        self.vector_preview = False
        # Kartenart: False = Raster-Kacheln, True = Vektor-Ansicht (MapLibre).
        # Vorbelegung Vektor; ohne Vektor-Ansicht stellt das Hauptfenster auf Raster.
        self.vector_mode = True
        # POI-Ebenen des geladenen Vektor-Stils: -1 unbekannt, 0 keine.
        self.vector_poi_layers = -1
        self.vector_map_sync_callback = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        self.paper_size = "A4"
        self.orientation = "Querformat"
        self.grid_density = "Locker"
        self.show_grid = True
        self.show_grid_lines = True
        self.border = 30.0
        self.map_layers = {"raster": DEFAULT_RASTER_LAYER, "vector": DEFAULT_VECTOR_LAYER}
        self.tiles.set_layer(self.map_layer)
        self.show_scale = False
        self.scale_position = "Rechts unten"
        self.scale_length_m = 1000
        self.scale_alpha = 255
        self.current_route_profile = "Fuß-Route"
        self.map_title = ""
        self.title_bg_color = "#ffffff"
        self.title_bg_alpha = 0
        self.title_text_color = "#000000"

        self.center_lat = 51.1657
        self.center_lon = 10.4515
        self.zoom = 6.0

        self.markers: List[Marker] = []
        self.notes: List[NoteBox] = []
        self.logos: List[LogoItem] = []
        self.routes: List[Route] = []
        self.zones: List[Zone] = []
        self.poi_filter_enabled = True
        self.poi_show_names = True
        self.poi_show_icons = True
        self.poi_categories_enabled = set(POI_DEFAULT_CATEGORIES)
        self.poi_zoom_offset = POI_DEFAULT_ZOOM_OFFSET
        self.selected_marker_id: Optional[int] = None
        self.selected_note_id: Optional[int] = None
        self.selected_logo_id: Optional[int] = None
        self.selected_route_id: Optional[int] = None
        self.selected_zone_id: Optional[int] = None
        self.selected_marker_ids: set[int] = set()
        self.selected_note_ids: set[int] = set()
        self.selected_logo_ids: set[int] = set()
        self.selected_route_ids: set[int] = set()
        self.selected_zone_ids: set[int] = set()
        self.undo_stack: List[dict] = []
        self.redo_stack: List[dict] = []
        self._restoring_history = False
        self.next_marker_id = 1
        self.next_note_id = 1
        self.next_logo_id = 1
        self.next_route_id = 1
        self.next_zone_id = 1
        self.next_zone_id = 1

        self.set_mode = False
        self.route_mode = False
        self.zone_mode = False
        self.logo_mode = False
        self.active_route_points: List[Tuple[float, float]] = []
        self.active_zone_points: List[Tuple[float, float]] = []
        self.current_route_color = "#ff0505"
        self.current_route_width = 6
        self.current_route_opacity = 80
        self.current_route_profile = "Fuß-Route"
        self.current_zone_fill_color = "#ff0505"
        self.current_zone_fill_alpha = 70
        self.current_zone_border_color = "#ff0505"
        self.current_zone_border_width = 4
        self.current_symbol = "punkt" if "punkt" in ICON_DATA else next(iter(ICON_DATA.keys()))
        self.current_color = "#e14f9e"
        self.default_label = ""

        self._mouse_down = False
        self._drag_kind: Optional[str] = None  # "pan", "marker", "logo", "pending_*"
        self._pending_action: Optional[str] = None
        self._pending_page_pos = QPointF()
        self._pending_widget_pos = QPointF()
        self._last_page_pos = QPointF()
        self._last_widget_pos = QPointF()

    # ---------- Layout ----------
    def page_size(self) -> Tuple[float, float]:
        # Interne Seitenkoordinaten bleiben proportional zum DIN-Format.
        # A4 Querformat entspricht der bisherigen Arbeitsgröße.
        base_w, base_h = (1600.0, 1131.0) if self.orientation == "Querformat" else (1131.0, 1600.0)
        factors = {"A3": math.sqrt(2.0), "A4": 1.0, "A5": 1.0 / math.sqrt(2.0)}
        f = factors.get(self.paper_size, 1.0)
        return base_w * f, base_h * f

    def map_rect(self) -> QRectF:
        w, h = self.page_size()
        return QRectF(self.border, self.border, w - 2 * self.border, h - 2 * self.border)

    def page_transform(self) -> Tuple[float, float, float]:
        pw, ph = self.page_size()
        margin = 16.0
        sx = max(0.1, (self.width() - 2 * margin) / pw)
        sy = max(0.1, (self.height() - 2 * margin) / ph)
        scale = min(sx, sy)
        ox = (self.width() - pw * scale) / 2.0
        oy = (self.height() - ph * scale) / 2.0
        return scale, ox, oy

    def widget_to_page(self, pos: QPointF) -> QPointF:
        scale, ox, oy = self.page_transform()
        return QPointF((pos.x() - ox) / scale, (pos.y() - oy) / scale)

    def page_to_widget(self, pos: QPointF) -> QPointF:
        scale, ox, oy = self.page_transform()
        return QPointF(pos.x() * scale + ox, pos.y() * scale + oy)

    # ---------- Map projection ----------
    def center_world(self) -> Tuple[float, float]:
        return latlon_to_world(self.center_lat, self.center_lon, self.zoom)

    def latlon_to_page(self, lat: float, lon: float) -> QPointF:
        mx, my = self.center_world()
        wx, wy = latlon_to_world(lat, lon, self.zoom)
        r = self.map_rect()
        return QPointF(r.center().x() + (wx - mx), r.center().y() + (wy - my))

    def page_to_latlon(self, p: QPointF) -> Tuple[float, float]:
        mx, my = self.center_world()
        r = self.map_rect()
        wx = mx + (p.x() - r.center().x())
        wy = my + (p.y() - r.center().y())
        return world_to_latlon(wx, wy, self.zoom)

    # ---------- History ----------
    def _state_copy(self) -> dict:
        return json.loads(json.dumps(self.project_state(), ensure_ascii=False))

    def _history_state(self) -> dict:
        # Rückgängig/Wiederholen betrifft nur Inhalte: Punkte, Texte, Bilder, Routen, Zonen
        # und den Titel. Kartenausschnitt und Einstellungen gehören nicht dazu.
        full = self._state_copy()
        state = {key: full.get(key, []) for key in HISTORY_CONTENT_KEYS}
        state["title"] = {key: full.get("ui", {}).get(key) for key in HISTORY_TITLE_KEYS}
        return state

    def _restore_history_state(self, state: dict) -> None:
        full = self._state_copy()
        for key in HISTORY_CONTENT_KEYS:
            full[key] = state.get(key, [])
        full.setdefault("ui", {}).update(state.get("title", {}))
        self._restoring_history = True
        try:
            self.load_project_state(full)
        finally:
            self._restoring_history = False

    def _history_step(self, source: List[dict], target: List[dict]) -> None:
        try:
            current = self._history_state()
        except Exception:
            return
        # Gemerkte Stände, die dem jetzigen gleichen, wären ein Schritt ohne Wirkung.
        while source and source[-1] == current:
            source.pop()
        if not source:
            return
        state = source.pop()
        target.append(current)
        self._restore_history_state(state)

    def remember(self) -> None:
        if getattr(self, "_restoring_history", False):
            return
        try:
            state = self._history_state()
        except Exception:
            return
        if self.undo_stack and self.undo_stack[-1] == state:
            return
        self.undo_stack.append(state)
        if len(self.undo_stack) > 80:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self) -> None:
        self._history_step(self.undo_stack, self.redo_stack)

    def redo(self) -> None:
        self._history_step(self.redo_stack, self.undo_stack)

    def clear_multi_selection(self) -> None:
        self.selected_marker_ids.clear()
        self.selected_note_ids.clear()
        self.selected_logo_ids.clear()
        self.selected_route_ids.clear()
        self.selected_zone_ids.clear()

    def deselect_all(self) -> None:
        self.clear_multi_selection()
        self.selected_marker_id = None
        self.selected_note_id = None
        self.selected_logo_id = None
        self.selected_route_id = None
        self.selected_zone_id = None
        self.markerSelected.emit(None)
        self.noteSelected.emit(None)
        self.logoSelected.emit(None)
        self.routeSelected.emit(None)
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()

    # ---------- Public state ----------
    def set_paper_size(self, value: str) -> None:
        self.paper_size = value if value in PAGE_EXPORTS else "A4"
        self.update()

    def set_orientation(self, value: str) -> None:
        self.orientation = value
        if self.grid_density not in GRID_PRESETS[self.orientation]:
            self.grid_density = "Locker"
        self.update()

    def set_density(self, value: str) -> None:
        self.grid_density = value
        self.update()

    @property
    def map_layer(self) -> str:
        # Kartenebene der gerade gewählten Kartenart.
        return self.map_layers["vector" if self.vector_mode else "raster"]

    @map_layer.setter
    def map_layer(self, value: str) -> None:
        self.map_layers["vector" if self.vector_mode else "raster"] = value

    def set_map_layer(self, value: str) -> None:
        self.map_layer = value if value in MAP_LAYERS else "Standard"
        self.tiles.set_layer(self.map_layer)
        self._sync_vector_map()
        self.update()

    def set_current_symbol(self, key: str) -> None:
        if key in ICON_DATA:
            self.current_symbol = key

    def set_current_color(self, color_hex: str) -> None:
        self.current_color = color_hex
        self.update()

    def selected_marker(self) -> Optional[Marker]:
        for m in self.markers:
            if m.id == self.selected_marker_id:
                return m
        return None

    def selected_note(self) -> Optional[NoteBox]:
        for n in self.notes:
            if n.id == self.selected_note_id:
                return n
        return None

    def selected_logo(self) -> Optional[LogoItem]:
        for logo in self.logos:
            if logo.id == self.selected_logo_id:
                return logo
        return None

    def selected_route(self) -> Optional[Route]:
        for route in self.routes:
            if route.id == self.selected_route_id:
                return route
        return None

    def selected_zone(self) -> Optional[Zone]:
        for zone in self.zones:
            if zone.id == self.selected_zone_id:
                return zone
        return None

    def add_marker_from_controls(self, lat: float, lon: float, label: str = "") -> Marker:
        self.remember()
        marker = Marker(
            id=self.next_marker_id,
            lat=lat,
            lon=lon,
            symbol=self.current_symbol,
            color=self.current_color,
            label="",
            description=label,
        )
        self.next_marker_id += 1
        self.markers.append(marker)
        self.selected_marker_id = marker.id
        self.selected_note_id = None
        self.selected_logo_id = None
        self.markerSelected.emit(marker)
        self.noteSelected.emit(None)
        self.logoSelected.emit(None)
        self.routeSelected.emit(None)
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()
        return marker

    def update_selected_marker(self, **kwargs) -> None:
        ids = set(self.selected_marker_ids)
        if not ids and self.selected_marker_id is not None:
            ids.add(self.selected_marker_id)
        targets = [m for m in self.markers if m.id in ids]
        if not targets:
            return
        self.remember()
        for m in targets:
            for k, v in kwargs.items():
                if hasattr(m, k):
                    setattr(m, k, v)
        self.update_status()
        self.update()

    def delete_selected_marker(self) -> None:
        if self.selected_marker_id is None and not self.selected_marker_ids:
            return
        self.remember()
        if self.selected_marker_ids:
            ids = set(self.selected_marker_ids)
            self.markers = [m for m in self.markers if m.id not in ids]
            self.selected_marker_ids.clear()
            self.selected_marker_id = None
            self.markerSelected.emit(None)
            self.update_status()
            self.update()
            return
        self.markers = [m for m in self.markers if m.id != self.selected_marker_id]
        self.selected_marker_id = None
        self.markerSelected.emit(None)
        self.update_status()
        self.update()

    def add_logo_from_path(self, file_path: str) -> Optional[LogoItem]:
        self.remember()
        path = Path(file_path)
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        img = QImage.fromData(raw)
        if img.isNull() or img.width() <= 0 or img.height() <= 0:
            return None
        fmt = path.suffix.lower().lstrip(".").upper() or "PNG"
        r = self.map_rect()
        default_w = min(220.0, max(80.0, r.width() * 0.16))
        default_h = default_w * img.height() / img.width()
        logo = LogoItem(
            id=self.next_logo_id,
            data_base64=base64.b64encode(raw).decode("ascii"),
            image_format=fmt,
            name=path.name,
            x=r.left() + 18.0,
            y=r.top() + 18.0,
            w=default_w,
            h=default_h,
        )
        self.next_logo_id += 1
        self.logos.append(logo)
        self.selected_logo_id = logo.id
        self.selected_marker_id = None
        self.selected_note_id = None
        self.logoSelected.emit(logo)
        self.markerSelected.emit(None)
        self.noteSelected.emit(None)
        self.update_status()
        self.update()
        return logo

    def update_selected_logo(self, **kwargs) -> None:
        ids = set(self.selected_logo_ids)
        if not ids and self.selected_logo_id is not None:
            ids.add(self.selected_logo_id)
        targets = [logo for logo in self.logos if logo.id in ids]
        if not targets:
            return
        self.remember()
        for logo in targets:
            for k, v in kwargs.items():
                if hasattr(logo, k):
                    setattr(logo, k, v)
        self.update_status()
        self.update()

    def delete_selected_logo(self) -> None:
        if self.selected_logo_id is None and not self.selected_logo_ids:
            return
        self.remember()
        if self.selected_logo_ids:
            ids = set(self.selected_logo_ids)
            self.logos = [logo for logo in self.logos if logo.id not in ids]
            self.selected_logo_ids.clear()
            self.selected_logo_id = None
            self.logoSelected.emit(None)
            self.update_status()
            self.update()
            return
        self.logos = [logo for logo in self.logos if logo.id != self.selected_logo_id]
        self.selected_logo_id = None
        self.logoSelected.emit(None)
        self.routeSelected.emit(None)
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()

    def add_or_update_note(self, note: NoteBox, update_existing: bool = False) -> None:
        ids = set(self.selected_note_ids)
        if not ids and self.selected_note_id is not None:
            ids.add(self.selected_note_id)
        if update_existing and ids:
            targets = [n for n in self.notes if n.id in ids]
            if targets:
                self.remember()
                for current in targets:
                    current.text = note.text
                    current.text_html = note.text_html
                    current.position = note.position
                    current.bg_color = note.bg_color
                    current.bg_alpha = note.bg_alpha
                    current.text_color = note.text_color
                    current.align = note.align
                    current.w = note.w
                    current.h = note.h
                    current.font = note.font
                    current.bold = note.bold
                    current.italic = note.italic
                    current.underline = note.underline
                    current.include_routes = note.include_routes if hasattr(note, "include_routes") else current.include_routes
                    current.visible = note.visible if hasattr(note, "visible") else current.visible
                    current.name = getattr(note, "name", "") or f"Textfeld {current.id}"
                self.update_status()
                self.update()
                return
        self.remember()
        note.id = self.next_note_id
        if not note.name:
            note.name = f"Textfeld {note.id}"
        self.next_note_id += 1
        self.notes.append(note)
        self.selected_note_id = note.id
        self.selected_marker_id = None
        self.selected_logo_id = None
        self.noteSelected.emit(note)
        self.markerSelected.emit(None)
        self.logoSelected.emit(None)
        self.routeSelected.emit(None)
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()

    def select_note_by_id(self, note_id: Optional[int]) -> None:
        self.clear_multi_selection()
        self.selected_note_id = note_id
        self.selected_marker_id = None
        self.selected_logo_id = None
        self.noteSelected.emit(self.selected_note())
        self.markerSelected.emit(None)
        self.logoSelected.emit(None)
        self.update()

    def delete_selected_note(self) -> None:
        if self.selected_note_id is None and not self.selected_note_ids:
            return
        self.remember()
        if self.selected_note_ids:
            ids = set(self.selected_note_ids)
            self.notes = [n for n in self.notes if n.id not in ids]
            self.selected_note_ids.clear()
            self.selected_note_id = None
            self.noteSelected.emit(None)
            self.update_status()
            self.update()
            return
        self.notes = [n for n in self.notes if n.id != self.selected_note_id]
        self.selected_note_id = None
        self.noteSelected.emit(None)
        self.update_status()
        self.update()

    def add_route(self, points: List[Tuple[float, float]], name: str = "Route",
                  color: Optional[str] = None, width: Optional[int] = None, calculated: bool = False,
                  opacity: Optional[int] = None, distance_m: float = 0.0,
                  duration_s: float = 0.0, directions_text: str = "",
                  control_points: Optional[List[Tuple[float, float]]] = None) -> Optional[Route]:
        self.remember()
        clean_points: List[Tuple[float, float]] = []
        for lat, lon in points:
            try:
                clean_points.append((float(lat), float(lon)))
            except (TypeError, ValueError):
                pass
        if len(clean_points) < 2:
            return None
        clean_control_points: List[Tuple[float, float]] = []
        for lat, lon in (control_points or points):
            try:
                clean_control_points.append((float(lat), float(lon)))
            except (TypeError, ValueError):
                pass
        if len(clean_control_points) < 2:
            clean_control_points = list(clean_points)
        route = Route(
            id=self.next_route_id,
            name=name.strip() or f"Route {self.next_route_id}",
            points=clean_points,
            control_points=clean_control_points,
            color=color or self.current_route_color,
            width=int(width if width is not None else self.current_route_width),
            calculated=calculated,
            opacity=int(clamp(opacity if opacity is not None else self.current_route_opacity, 0, 100)),
            distance_m=float(distance_m or 0.0),
            duration_s=float(duration_s or 0.0),
            directions_text=str(directions_text or ""),
        )
        self.next_route_id += 1
        self.routes.append(route)
        self.selected_route_id = route.id
        self.routeSelected.emit(route)
        self.active_route_points.clear()
        self.update_status()
        self.update()
        return route

    def remove_last_route_point(self) -> None:
        if self.active_route_points:
            self.active_route_points.pop()
            self.update_status()
            self.update()

    def delete_selected_route(self) -> None:
        if self.selected_route_id is None and not self.selected_route_ids:
            return
        self.remember()
        if self.selected_route_ids:
            ids = set(self.selected_route_ids)
            self.routes = [r for r in self.routes if r.id not in ids]
            self.selected_route_ids.clear()
            self.selected_route_id = None
            self.routeSelected.emit(None)
            self.update_status()
            self.update()
            return
        self.routes = [r for r in self.routes if r.id != self.selected_route_id]
        self.selected_route_id = None
        self.routeSelected.emit(None)
        self.update_status()
        self.update()

    def clear_routes(self) -> None:
        self.remember()
        self.routes.clear()
        self.active_route_points.clear()
        self.selected_route_id = None
        self.next_route_id = 1
        self.routeSelected.emit(None)
        self.update_status()
        self.update()

    def select_route_by_id(self, route_id: Optional[int]) -> None:
        self.selected_route_id = route_id
        self.routeSelected.emit(self.selected_route())
        self.update()

    def update_selected_route(self, **kwargs) -> None:
        ids = set(self.selected_route_ids)
        if not ids and self.selected_route_id is not None:
            ids.add(self.selected_route_id)
        targets = [r for r in self.routes if r.id in ids]
        if not targets:
            return
        self.remember()
        for r in targets:
            for k, v in kwargs.items():
                if hasattr(r, k):
                    setattr(r, k, v)
        self.update_status()
        self.update()

    def add_zone(self, points: List[Tuple[float, float]], name: str = "Zone", label: str = "",
                 fill_color: Optional[str] = None, fill_alpha: Optional[int] = None,
                 border_color: Optional[str] = None, border_width: Optional[int] = None,
                 label_position: str = "Mitte", label_bg_color: str = "#ffffff", label_bg_alpha: int = 180, text_color: str = "#000000") -> Optional[Zone]:
        self.remember()
        clean_points: List[Tuple[float, float]] = []
        for lat, lon in points:
            try:
                clean_points.append((float(lat), float(lon)))
            except (TypeError, ValueError):
                pass
        if len(clean_points) < 3:
            return None
        zone = Zone(
            id=self.next_zone_id,
            name=name.strip() or f"Zone {self.next_zone_id}",
            points=clean_points,
            label=label,
            label_position=label_position,
            fill_color=fill_color or self.current_zone_fill_color,
            fill_alpha=int(fill_alpha if fill_alpha is not None else self.current_zone_fill_alpha),
            border_color=border_color or self.current_zone_border_color,
            border_width=int(border_width if border_width is not None else self.current_zone_border_width),
            text_color=text_color or "#000000",
            label_bg_color=label_bg_color or "#ffffff",
            label_bg_alpha=int(label_bg_alpha),
        )
        self.next_zone_id += 1
        self.zones.append(zone)
        self.selected_zone_id = zone.id
        self.active_zone_points.clear()
        self.zoneSelected.emit(zone)
        self.update_status()
        self.update()
        return zone

    def update_selected_zone(self, **kwargs) -> None:
        ids = set(self.selected_zone_ids)
        if not ids and self.selected_zone_id is not None:
            ids.add(self.selected_zone_id)
        targets = [z for z in self.zones if z.id in ids]
        if not targets:
            return
        self.remember()
        for z in targets:
            for k, v in kwargs.items():
                if hasattr(z, k):
                    setattr(z, k, v)
        self.update_status()
        self.update()

    def select_zone_by_id(self, zone_id: Optional[int]) -> None:
        self.selected_zone_id = zone_id
        self.zoneSelected.emit(self.selected_zone())
        self.update()

    def remove_last_zone_point(self) -> None:
        if self.active_zone_points:
            self.active_zone_points.pop()
            self.update_status()
            self.update()

    def delete_selected_zone(self) -> None:
        if self.selected_zone_id is None and not self.selected_zone_ids:
            return
        self.remember()
        if self.selected_zone_ids:
            ids = set(self.selected_zone_ids)
            self.zones = [z for z in self.zones if z.id not in ids]
            self.selected_zone_ids.clear()
            self.selected_zone_id = None
            self.zoneSelected.emit(None)
            self.update_status()
            self.update()
            return
        self.zones = [z for z in self.zones if z.id != self.selected_zone_id]
        self.selected_zone_id = None
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()

    def center_on(self, lat: float, lon: float, zoom: Optional[float] = None) -> None:
        self.center_lat = float(lat)
        self.center_lon = float(lon)
        if zoom is not None:
            self.zoom = float(clamp(float(zoom), 2.0, 19.0))
        self._sync_vector_map()
        self.update_status()
        self.update()

    def reset_project(self) -> None:
        self.remember()
        self.markers.clear()
        self.notes.clear()
        self.logos.clear()
        self.routes.clear()
        self.zones.clear()
        self.active_route_points.clear()
        self.active_zone_points.clear()
        self.selected_marker_id = None
        self.selected_note_id = None
        self.selected_logo_id = None
        self.selected_route_id = None
        self.selected_zone_id = None
        self.next_marker_id = 1
        self.next_note_id = 1
        self.next_logo_id = 1
        self.next_route_id = 1
        self.next_zone_id = 1
        self.next_zone_id = 1
        self.center_lat = 51.1657
        self.center_lon = 10.4515
        self.zoom = 6.0
        self.paper_size = "A4"
        self.orientation = "Querformat"
        self.grid_density = "Locker"
        self.show_grid = True
        self.show_grid_lines = True
        self.border = 30.0
        self.vector_mode = bool(self.vector_preview)
        self.map_layers = {"raster": DEFAULT_RASTER_LAYER, "vector": DEFAULT_VECTOR_LAYER}
        self.tiles.set_layer(self.map_layer)
        self.poi_filter_enabled = True
        self.poi_show_names = True
        self.poi_show_icons = True
        self.poi_categories_enabled = set(POI_DEFAULT_CATEGORIES)
        self.poi_zoom_offset = POI_DEFAULT_ZOOM_OFFSET
        self.show_scale = False
        self.scale_position = "Rechts unten"
        self.scale_length_m = 1000
        self.scale_alpha = 255
        self.current_route_profile = "Fuß-Route"
        self.map_title = ""
        self.title_bg_color = "#ffffff"
        self.title_bg_alpha = 0
        self.title_text_color = "#000000"
        self.markerSelected.emit(None)
        self.noteSelected.emit(None)
        self.logoSelected.emit(None)
        self.routeSelected.emit(None)
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()

    def project_state(self) -> dict:
        return {
            "version": APP_VERSION,
            "map": {"center_lat": self.center_lat, "center_lon": self.center_lon, "zoom": self.zoom},
            "ui": {
                "paper_size": self.paper_size,
                "orientation": self.orientation,
                "grid_density": self.grid_density,
                "show_grid": self.show_grid,
                "show_grid_lines": self.show_grid_lines,
                "border": self.border,
                "map_layer": self.map_layer,
                "map_layer_raster": self.map_layers["raster"],
                "map_layer_vector": self.map_layers["vector"],
                "vector_mode": bool(self.vector_mode),
                "poi_filter_enabled": bool(self.poi_filter_enabled),
                "poi_show_names": bool(self.poi_show_names),
                "poi_show_icons": bool(self.poi_show_icons),
                "poi_categories_enabled": sorted(self.poi_categories_enabled),
                "poi_categories_version": 2,
                "poi_zoom_offset": float(self.poi_zoom_offset),
                "show_scale": self.show_scale,
                "scale_position": self.scale_position,
                "scale_length_m": self.scale_length_m,
                "scale_alpha": self.scale_alpha,
                "map_title": self.map_title,
                "title_bg_color": self.title_bg_color,
                "title_bg_alpha": self.title_bg_alpha,
                "title_text_color": self.title_text_color,
                "current_symbol": self.current_symbol,
                "current_color": self.current_color,
                "current_route_color": self.current_route_color,
                "current_route_width": self.current_route_width,
                "current_route_opacity": self.current_route_opacity,
                "current_route_profile": self.current_route_profile,
            },
            "markers": [asdict(m) for m in self.markers],
            "notes": [asdict(n) for n in self.notes],
            "logos": [asdict(logo) for logo in self.logos],
            "routes": [asdict(r) for r in self.routes],
            "zones": [asdict(z) for z in self.zones],
        }

    def load_project_state(self, data: dict) -> None:
        self.markers.clear()
        self.notes.clear()
        self.logos.clear()
        self.routes.clear()
        self.zones.clear()
        self.active_route_points.clear()
        self.active_zone_points.clear()
        mp = data.get("map", {})
        self.center_lat = float(mp.get("center_lat", mp.get("lat", 51.1657)))
        self.center_lon = float(mp.get("center_lon", mp.get("lon", 10.4515)))
        self.zoom = float(clamp(float(mp.get("zoom", 6.0)), 2.0, 19.0))
        ui = data.get("ui", {})
        self.paper_size = str(ui.get("paper_size", ui.get("page_size", self.paper_size)))
        if self.paper_size not in PAGE_EXPORTS:
            self.paper_size = "A4"
        self.orientation = ui.get("orientation", self.orientation)
        if self.orientation not in GRID_PRESETS:
            self.orientation = "Querformat"
        self.grid_density = ui.get("grid_density", ui.get("density", "Locker"))
        if self.grid_density not in GRID_PRESETS[self.orientation]:
            self.grid_density = "Locker"
        self.show_grid = bool(ui.get("show_grid", ui.get("grid", True)))
        self.show_grid_lines = bool(ui.get("show_grid_lines", ui.get("gridLines", True)))
        self.border = float(ui.get("border", self.border))
        self.border = clamp(self.border, 10.0, 100.0)
        saved_layer = str(ui.get("map_layer", "Standard"))
        if saved_layer not in MAP_LAYERS:
            saved_layer = "Standard"
        self.poi_filter_enabled = bool(ui.get("poi_filter_enabled", False))
        # Projekte bis 2.8 kennen keine Kartenart: dort lief die Vektorkarte genau dann,
        # wenn der POI-Filter aktiv war.
        self.vector_mode = bool(ui.get("vector_mode", self.poi_filter_enabled))
        # Kartenebene je Kartenart. Projekte ohne diese Felder kennen nur eine Ebene:
        # sie gilt für die gespeicherte Kartenart, die andere bekommt ihre Vorbelegung.
        self.map_layers = {"raster": DEFAULT_RASTER_LAYER, "vector": DEFAULT_VECTOR_LAYER}
        self.map_layer = saved_layer
        for mode_key in ("raster", "vector"):
            mode_layer = str(ui.get("map_layer_" + mode_key, "") or "")
            if mode_layer in MAP_LAYERS:
                self.map_layers[mode_key] = mode_layer
        self.tiles.set_layer(self.map_layer)
        self.poi_show_names = bool(ui.get("poi_show_names", True))
        self.poi_show_icons = bool(ui.get("poi_show_icons", True))
        saved_poi_categories = ui.get("poi_categories_enabled", list(POI_CATEGORY_LABELS.keys()))
        if isinstance(saved_poi_categories, (list, tuple, set)):
            self.poi_categories_enabled = {str(key) for key in saved_poi_categories if str(key) in POI_CATEGORY_LABELS}
            # Projekte vor dem Typ ÖPNV: Haltestellen liefen dort unter „Sonstige POIs“.
            if int(ui.get("poi_categories_version", 1) or 1) < 2 and "other" in self.poi_categories_enabled:
                self.poi_categories_enabled.add("transit")
        else:
            self.poi_categories_enabled = set(POI_CATEGORY_LABELS.keys())
        try:
            self.poi_zoom_offset = clamp(float(ui.get("poi_zoom_offset", 0.0)), POI_ZOOM_OFFSET_MIN, POI_ZOOM_OFFSET_MAX)
        except Exception:
            self.poi_zoom_offset = 0.0
        self.show_scale = bool(ui.get("show_scale", False))
        self.scale_position = str(ui.get("scale_position", "Rechts unten"))
        self.scale_length_m = int(ui.get("scale_length_m", 1000))
        self.scale_alpha = int(ui.get("scale_alpha", 255))
        self.map_title = str(ui.get("map_title", ui.get("title", self.map_title)))
        self.title_bg_color = str(ui.get("title_bg_color", "#ffffff"))
        self.title_bg_alpha = int(ui.get("title_bg_alpha", 0))
        self.title_text_color = str(ui.get("title_text_color", "#000000"))
        self.current_symbol = ui.get("current_symbol", ui.get("currentSymbol", self.current_symbol))
        self.current_color = ui.get("current_color", ui.get("currentColor", self.current_color))
        self.current_route_color = ui.get("current_route_color", "#ff0505")
        self.current_route_width = int(ui.get("current_route_width", 6))
        self.current_route_opacity = int(ui.get("current_route_opacity", 80))
        self.current_route_profile = str(ui.get("current_route_profile", "Fuß-Route"))
        if self.current_route_profile not in ("Fuß-Route", "Fahrrad-Route", "PKW-Route"):
            self.current_route_profile = "Fuß-Route"

        max_m = 0
        for raw in data.get("markers", []):
            old_label = raw.get("label", "")
            desc = raw.get("description", "") or old_label
            m = Marker(
                id=int(raw.get("id", raw.get("marker_id", 0)) or 0),
                lat=float(raw.get("lat", 0.0)),
                lon=float(raw.get("lon", raw.get("lng", 0.0))),
                symbol=raw.get("symbol", "punkt"),
                color=raw.get("color", "#e14f9e"),
                label="",
                description=desc,
                label_position=raw.get("label_position", raw.get("labelPosition", "Rechts")),
                label_w=int(raw.get("label_w", raw.get("labelW", 150))),
                label_h=int(raw.get("label_h", raw.get("labelH", 54))),
                label_font=int(raw.get("label_font", raw.get("labelFont", 12))),
                label_bold=bool(raw.get("label_bold", raw.get("labelBold", False))),
                label_italic=bool(raw.get("label_italic", raw.get("labelItalic", False))),
                label_underline=bool(raw.get("label_underline", raw.get("labelUnderline", False))),
                label_bg_alpha=int(raw.get("label_bg_alpha", raw.get("labelBgAlpha", 255))),
                text_color=raw.get("text_color", raw.get("textColor", "#000000")),
                label_gap=int(raw.get("label_gap", raw.get("labelGap", 4))),
                icon_size=int(raw.get("icon_size", raw.get("iconSize", 52))),
            )
            if m.id <= 0:
                m.id = max_m + 1
            max_m = max(max_m, m.id)
            self.markers.append(m)
        self.next_marker_id = max_m + 1

        max_n = 0
        for raw in data.get("notes", []):
            n = NoteBox(
                id=int(raw.get("id", 0) or 0),
                text=raw.get("text", ""),
                text_html=raw.get("text_html", raw.get("textHtml", "")),
                position=raw.get("position", "Rechts oben"),
                bg_color=raw.get("bg_color", raw.get("bgColor", "#ffffff")),
                bg_alpha=int(raw.get("bg_alpha", raw.get("bgAlpha", 255))),
                text_color=raw.get("text_color", raw.get("textColor", "#000000")),
                align=raw.get("align", "Links"),
                w=int(raw.get("w", 230)),
                h=int(raw.get("h", 110)),
                font=int(raw.get("font", 13)),
                bold=bool(raw.get("bold", False)),
                italic=bool(raw.get("italic", False)),
                underline=bool(raw.get("underline", False)),
                include_routes=bool(raw.get("include_routes", raw.get("includeRoutes", False))),
                visible=bool(raw.get("visible", True)),
                name=str(raw.get("name", "") or ""),
            )
            if n.id <= 0:
                n.id = max_n + 1
            max_n = max(max_n, n.id)
            self.notes.append(n)
        self.next_note_id = max_n + 1

        max_logo = 0
        for raw in data.get("logos", []):
            logo = LogoItem(
                id=int(raw.get("id", 0) or 0),
                data_base64=str(raw.get("data_base64", raw.get("dataBase64", ""))),
                image_format=str(raw.get("image_format", raw.get("imageFormat", "PNG"))),
                name=str(raw.get("name", f"Bilddatei {raw.get('id', '')}")),
                x=float(raw.get("x", 80.0)),
                y=float(raw.get("y", 80.0)),
                w=float(raw.get("w", 180.0)),
                h=float(raw.get("h", 90.0)),
            )
            if not logo.data_base64:
                continue
            if logo.id <= 0:
                logo.id = max_logo + 1
            max_logo = max(max_logo, logo.id)
            self.logos.append(logo)
        self.next_logo_id = max_logo + 1

        max_r = 0
        for raw in data.get("routes", []):
            pts: List[Tuple[float, float]] = []
            for pt in raw.get("points", []):
                try:
                    lat, lon = pt
                    pts.append((float(lat), float(lon)))
                except Exception as exc:
                    log_debug("Stiller Fehler", exc)
            if len(pts) < 2:
                continue
            control_pts: List[Tuple[float, float]] = []
            for pt in raw.get("control_points", raw.get("controlPoints", [])):
                try:
                    lat, lon = pt
                    control_pts.append((float(lat), float(lon)))
                except Exception as exc:
                    log_debug("Stiller Fehler", exc)
            if len(control_pts) < 2:
                control_pts = list(pts)
            route = Route(
                id=int(raw.get("id", 0) or 0),
                name=raw.get("name", "Route"),
                points=pts,
                control_points=control_pts,
                color=raw.get("color", "#ff0505"),
                width=int(raw.get("width", 6)),
                calculated=bool(raw.get("calculated", False)),
                opacity=int(raw.get("opacity", 80)),
                distance_m=float(raw.get("distance_m", raw.get("distanceM", 0.0)) or 0.0),
                duration_s=float(raw.get("duration_s", raw.get("durationS", 0.0)) or 0.0),
                directions_text=str(raw.get("directions_text", raw.get("directionsText", "")) or ""),
                profile=str(raw.get("profile", "") or ""),
            )
            if route.id <= 0:
                route.id = max_r + 1
            max_r = max(max_r, route.id)
            self.routes.append(route)
        self.next_route_id = max_r + 1

        max_z = 0
        for raw in data.get("zones", []):
            pts: List[Tuple[float, float]] = []
            for pt in raw.get("points", []):
                try:
                    lat, lon = pt
                    pts.append((float(lat), float(lon)))
                except Exception as exc:
                    log_debug("Stiller Fehler", exc)
            if len(pts) < 3:
                continue
            zone = Zone(
                id=int(raw.get("id", 0) or 0),
                name=raw.get("name", "Zone"),
                points=pts,
                label=raw.get("label", ""),
                label_position=raw.get("label_position", raw.get("labelPosition", "Mitte")),
                fill_color=raw.get("fill_color", raw.get("fillColor", "#ff0505")),
                fill_alpha=int(raw.get("fill_alpha", raw.get("fillAlpha", 70))),
                border_color=raw.get("border_color", raw.get("borderColor", "#ff0505")),
                border_width=int(raw.get("border_width", raw.get("borderWidth", 4))),
                text_color=raw.get("text_color", raw.get("textColor", "#000000")),
                label_font=int(raw.get("label_font", raw.get("labelFont", 13))),
                label_bold=bool(raw.get("label_bold", raw.get("labelBold", False))),
                label_italic=bool(raw.get("label_italic", raw.get("labelItalic", False))),
                label_underline=bool(raw.get("label_underline", raw.get("labelUnderline", False))),
                label_bg_color=raw.get("label_bg_color", raw.get("labelBgColor", "#ffffff")),
                label_bg_alpha=int(raw.get("label_bg_alpha", raw.get("labelBgAlpha", 180))),
            )
            if zone.id <= 0:
                zone.id = max_z + 1
            max_z = max(max_z, zone.id)
            self.zones.append(zone)
        self.next_zone_id = max_z + 1

        self.selected_marker_id = None
        self.selected_note_id = None
        self.selected_logo_id = None
        self.selected_route_id = None
        self.selected_zone_id = None
        self.markerSelected.emit(None)
        self.noteSelected.emit(None)
        self.logoSelected.emit(None)
        self.routeSelected.emit(None)
        self.zoneSelected.emit(None)
        self.update_status()
        self.update()

    def update_status(self) -> None:
        self.statusChanged.emit(
            f"Zoom {float(self.zoom):.2f} | Punkte: {len(self.markers)} | "
            f"Routen: {len(self.routes)} | Zonen: {len(self.zones)} | "
            f"Textfelder: {len(self.notes)} | Bilddateien: {len(self.logos)}"
        )
        self._sync_vector_map()

    def _sync_vector_map(self) -> None:
        cb = getattr(self, "vector_map_sync_callback", None)
        if callable(cb):
            try:
                cb()
            except Exception as exc:
                log_debug("Stiller Fehler", exc)

    # ---------- Mouse interaction ----------
    def _toggle_multi(self, kind: str, item_id: int) -> None:
        attr = f"selected_{kind}_ids"
        ids = getattr(self, attr, None)
        if ids is None:
            return
        if item_id in ids:
            ids.remove(item_id)
        else:
            ids.add(item_id)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.setFocus()
            self._mouse_down = False
            self._drag_kind = None
            self.deselect_all()
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        page_pos = self.widget_to_page(QPointF(event.position()))
        self._mouse_down = True
        self._last_page_pos = page_pos
        self._last_widget_pos = QPointF(event.position())

        ctrl_down = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl_down:
            if self.set_mode:
                clicked_marker = self._hit_marker(page_pos)
                if clicked_marker:
                    self.selected_marker_id = clicked_marker.id
                    self._toggle_multi("marker", clicked_marker.id)
                    return
            elif getattr(self, "logo_mode", False):
                clicked_logo = self._hit_logo(page_pos)
                if clicked_logo:
                    self.selected_logo_id = clicked_logo.id
                    self._toggle_multi("logo", clicked_logo.id)
                    return
            elif self.route_mode:
                clicked_route = self._hit_route(page_pos)
                if clicked_route:
                    self.selected_route_id = clicked_route.id
                    self._toggle_multi("route", clicked_route.id)
                    return
            elif self.zone_mode:
                clicked_zone = self._hit_zone(page_pos)
                if clicked_zone:
                    self.selected_zone_id = clicked_zone.id
                    self._toggle_multi("zone", clicked_zone.id)
                    return
            else:
                clicked_route = self._hit_route(page_pos)
                if clicked_route:
                    self.selected_route_id = clicked_route.id
                    self._toggle_multi("route", clicked_route.id)
                    return
                clicked_marker = self._hit_marker(page_pos)
                if clicked_marker:
                    self.selected_marker_id = clicked_marker.id
                    self._toggle_multi("marker", clicked_marker.id)
                    return
                clicked_note = self._hit_note(page_pos)
                if clicked_note:
                    self.selected_note_id = clicked_note.id
                    self._toggle_multi("note", clicked_note.id)
                    return
                clicked_logo = self._hit_logo(page_pos)
                if clicked_logo:
                    self.selected_logo_id = clicked_logo.id
                    self._toggle_multi("logo", clicked_logo.id)
                    return
                clicked_zone = self._hit_zone(page_pos)
                if clicked_zone:
                    self.selected_zone_id = clicked_zone.id
                    self._toggle_multi("zone", clicked_zone.id)
                    return

        r = self.map_rect()
        if r.contains(page_pos) and self.route_mode:
            self._pending_action = "route"
            self._pending_page_pos = QPointF(page_pos)
            self._pending_widget_pos = QPointF(event.position())
            self._drag_kind = "pending_route"
            return
        if r.contains(page_pos) and self.zone_mode:
            self._pending_action = "zone"
            self._pending_page_pos = QPointF(page_pos)
            self._pending_widget_pos = QPointF(event.position())
            self._drag_kind = "pending_zone"
            return

        if self.set_mode:
            clicked_marker = self._hit_marker(page_pos)
            if clicked_marker:
                self.clear_multi_selection()
                self.selected_marker_id = clicked_marker.id
                self.selected_note_id = None
                self.selected_logo_id = None
                self.markerSelected.emit(clicked_marker)
                self.noteSelected.emit(None)
                self.logoSelected.emit(None)
                self._drag_kind = "marker"
                self.update()
                return
            if r.contains(page_pos):
                self._pending_action = "marker"
                self._pending_page_pos = QPointF(page_pos)
                self._pending_widget_pos = QPointF(event.position())
                self._drag_kind = "pending_marker"
                return

        if getattr(self, "logo_mode", False):
            clicked_logo = self._hit_logo(page_pos)
            if clicked_logo:
                self.clear_multi_selection()
                self.selected_logo_id = clicked_logo.id
                self.selected_marker_id = None
                self.selected_note_id = None
                self.logoSelected.emit(clicked_logo)
                self.markerSelected.emit(None)
                self.noteSelected.emit(None)
                self._drag_kind = "logo"
                self.update()
                return
            if r.contains(page_pos):
                self.selected_marker_id = None
                self.selected_note_id = None
                self.selected_logo_id = None
                self.markerSelected.emit(None)
                self.noteSelected.emit(None)
                self.logoSelected.emit(None)
                self._drag_kind = "pan"
                self.update()
                return

        clicked_route = self._hit_route(page_pos)
        if clicked_route:
            self.clear_multi_selection()
            self.selected_route_id = clicked_route.id
            self.routeSelected.emit(clicked_route)
            self._drag_kind = None
            self.update()
            return

        clicked_zone = self._hit_zone(page_pos)
        if clicked_zone:
            self.clear_multi_selection()
            self.selected_zone_id = clicked_zone.id
            self.zoneSelected.emit(clicked_zone)
            self._drag_kind = None
            self.update()
            return

        clicked_note = self._hit_note(page_pos)
        if clicked_note:
            self.clear_multi_selection()
            self.selected_note_id = clicked_note.id
            self.selected_marker_id = None
            self.selected_logo_id = None
            self.noteSelected.emit(clicked_note)
            self.markerSelected.emit(None)
            self.logoSelected.emit(None)
            self._drag_kind = None
            self.update()
            return

        clicked_logo = self._hit_logo(page_pos)
        if clicked_logo:
            self.clear_multi_selection()
            self.selected_logo_id = clicked_logo.id
            self.selected_marker_id = None
            self.selected_note_id = None
            self.logoSelected.emit(clicked_logo)
            self.markerSelected.emit(None)
            self.noteSelected.emit(None)
            self._drag_kind = "logo"
            self.update()
            return

        clicked_marker = self._hit_marker(page_pos)
        if clicked_marker:
            self.clear_multi_selection()
            self.selected_marker_id = clicked_marker.id
            self.selected_note_id = None
            self.selected_logo_id = None
            self.markerSelected.emit(clicked_marker)
            self.noteSelected.emit(None)
            self.logoSelected.emit(None)
            self._drag_kind = "marker"
            self.update()
            return

        if r.contains(page_pos):
            if self.set_mode:
                self._pending_action = "marker"
                self._pending_page_pos = QPointF(page_pos)
                self._pending_widget_pos = QPointF(event.position())
                self._drag_kind = "pending_marker"
            else:
                self.selected_marker_id = None
                self.selected_note_id = None
                self.selected_logo_id = None
                self.markerSelected.emit(None)
                self.noteSelected.emit(None)
                self.logoSelected.emit(None)
                self._drag_kind = "pan"
                self.update()
        else:
            self._drag_kind = None

    def mouseMoveEvent(self, event) -> None:
        page_pos = self.widget_to_page(QPointF(event.position()))
        if not self._mouse_down:
            lat, lon = self.page_to_latlon(page_pos) if self.map_rect().contains(page_pos) else (None, None)
            if lat is not None:
                self.statusChanged.emit(
                    f"Zoom {float(self.zoom):.2f} | Lat {lat:.5f} Lon {lon:.5f} | Punkte: {len(self.markers)} | Routenpunkte: {len(self.active_route_points)} | Zonenpunkte: {len(self.active_zone_points)}"
                )
            return

        delta = page_pos - self._last_page_pos
        if isinstance(self._drag_kind, str) and self._drag_kind.startswith("pending_"):
            start = self._pending_widget_pos
            now = QPointF(event.position())
            if math.hypot(now.x() - start.x(), now.y() - start.y()) < 6.0:
                return
            self._drag_kind = "pan"
            self._pending_action = None
        if self._drag_kind == "pan":
            cx, cy = self.center_world()
            cx -= delta.x()
            cy -= delta.y()
            self.center_lat, self.center_lon = world_to_latlon(cx, cy, self.zoom)
            self._sync_vector_map()
            self.update()
        elif self._drag_kind == "marker":
            m = self.selected_marker()
            if m and self.map_rect().contains(page_pos):
                m.lat, m.lon = self.page_to_latlon(page_pos)
                self.markerSelected.emit(m)
                self.update()
        elif self._drag_kind == "logo":
            logo = self.selected_logo()
            if logo:
                logo.x += delta.x()
                logo.y += delta.y()
                pw, ph = self.page_size()
                logo.x = clamp(logo.x, 0.0, max(0.0, pw - logo.w))
                logo.y = clamp(logo.y, 0.0, max(0.0, ph - logo.h))
                self.logoSelected.emit(logo)
                self.update()
        self._last_page_pos = page_pos
        self._last_widget_pos = QPointF(event.position())

    def _execute_pending_map_click(self) -> None:
        action = self._pending_action
        page_pos = QPointF(self._pending_page_pos)
        self._pending_action = None
        if not self.map_rect().contains(page_pos):
            return
        if action == "route":
            lat, lon = self.page_to_latlon(page_pos)
            self.active_route_points.append((lat, lon))
            self.selected_marker_id = None
            self.selected_note_id = None
            self.selected_logo_id = None
            self.markerSelected.emit(None)
            self.noteSelected.emit(None)
            self.logoSelected.emit(None)
        elif action == "zone":
            lat, lon = self.page_to_latlon(page_pos)
            self.active_zone_points.append((lat, lon))
            self.selected_marker_id = None
            self.selected_note_id = None
            self.selected_logo_id = None
            self.markerSelected.emit(None)
            self.noteSelected.emit(None)
            self.logoSelected.emit(None)
        elif action == "marker":
            lat, lon = self.page_to_latlon(page_pos)
            self.add_marker_from_controls(lat, lon, self.default_label)
        self.update_status()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if isinstance(self._drag_kind, str) and self._drag_kind.startswith("pending_"):
            self._execute_pending_map_click()
        self._mouse_down = False
        self._drag_kind = None

    def wheelEvent(self, event) -> None:
        page_pos = self.widget_to_page(QPointF(event.position()))
        if not self.map_rect().contains(page_pos):
            return

        # Geografischen Punkt unter dem Cursor VOR der Zoomänderung merken.
        before_lat, before_lon = self.page_to_latlon(page_pos)
        old_zoom = float(self.zoom)

        pixel_y = event.pixelDelta().y()
        angle_y = event.angleDelta().y()

        if pixel_y:
            # Hochauflösende Trackpads liefern Pixel-Deltas und zoomen damit praktisch kontinuierlich.
            delta_zoom = float(pixel_y) * 0.0035
        elif angle_y:
            # Klassisches Mausrad: feine Schritte statt ganzer OSM-Zoomstufen.
            delta_zoom = (float(angle_y) / 120.0) * 0.05
        else:
            return

        new_zoom = float(clamp(old_zoom + delta_zoom, 2.0, 19.0))
        if abs(new_zoom - old_zoom) < 0.000001:
            event.accept()
            return

        self.zoom = new_zoom

        # Zoom auf Mausposition: der geografische Punkt unter dem Cursor bleibt stabil.
        wx, wy = latlon_to_world(before_lat, before_lon, self.zoom)
        r = self.map_rect()
        center_wx = wx - (page_pos.x() - r.center().x())
        center_wy = wy - (page_pos.y() - r.center().y())
        self.center_lat, self.center_lon = world_to_latlon(center_wx, center_wy, self.zoom)

        self._sync_vector_map()
        self.update_status()
        self.update()
        event.accept()

    def keyPressEvent(self, event) -> None:
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl and event.key() == Qt.Key.Key_Z:
            self.undo()
            return
        if ctrl and event.key() == Qt.Key.Key_Y:
            self.redo()
            return
        if ctrl and event.key() == Qt.Key.Key_A:
            self.clear_multi_selection()
            if self.set_mode:
                self.selected_marker_ids = {m.id for m in self.markers}
            elif self.route_mode:
                self.selected_route_ids = {r.id for r in self.routes}
            elif self.zone_mode:
                self.selected_zone_ids = {z.id for z in self.zones}
            else:
                self.selected_note_ids = {n.id for n in self.notes}
            self.update()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected_marker_ids or self.selected_marker_id is not None:
                self.delete_selected_marker()
            elif self.selected_note_ids or self.selected_note_id is not None:
                self.delete_selected_note()
            elif self.selected_logo_ids or self.selected_logo_id is not None:
                self.delete_selected_logo()
            elif self.selected_zone_ids or self.selected_zone_id is not None:
                self.delete_selected_zone()
            elif self.selected_route_ids or self.selected_route_id is not None:
                self.delete_selected_route()
        elif event.key() == Qt.Key.Key_Plus:
            self.zoom = float(clamp(float(self.zoom) + 0.05, 2.0, 19.0))
            self.update_status()
            self.update()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom = float(clamp(float(self.zoom) - 0.05, 2.0, 19.0))
            self.update_status()
            self.update()

    def _hit_marker(self, page_pos: QPointF) -> Optional[Marker]:
        for m in reversed(self.markers):
            icon_rect, label_rect = self._marker_rects(m)
            text = m.description.strip() or m.label.strip()
            if icon_rect.adjusted(-6, -6, 6, 6).contains(page_pos) or (text and label_rect.contains(page_pos)):
                return m
        return None

    def _hit_note(self, page_pos: QPointF) -> Optional[NoteBox]:
        for n in reversed(self.notes):
            if not getattr(n, "visible", True):
                continue
            if self._note_rect(n).contains(page_pos):
                return n
        return None

    def _zone_path(self, zone: Zone) -> QPainterPath:
        path = QPainterPath()
        pts = [self.latlon_to_page(lat, lon) for lat, lon in zone.points]
        if pts:
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            path.closeSubpath()
        return path

    def _hit_zone(self, page_pos: QPointF) -> Optional[Zone]:
        for z in reversed(self.zones):
            if self._zone_path(z).contains(page_pos):
                return z
        return None

    def _distance_to_segment(self, p: QPointF, a: QPointF, b: QPointF) -> float:
        ax, ay, bx, by = a.x(), a.y(), b.x(), b.y()
        px, py = p.x(), p.y()
        dx, dy = bx - ax, by - ay
        denom = dx * dx + dy * dy
        if denom <= 0.000001:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
        cx, cy = ax + t * dx, ay + t * dy
        return math.hypot(px - cx, py - cy)

    def _hit_route(self, page_pos: QPointF) -> Optional[Route]:
        for route in reversed(self.routes):
            pts = [self.latlon_to_page(lat, lon) for lat, lon in route.points]
            hit_width = max(10.0, float(route.width) + 8.0)
            for a, b in zip(pts, pts[1:]):
                if self._distance_to_segment(page_pos, a, b) <= hit_width:
                    return route
        return None

    def _logo_rect(self, logo: LogoItem) -> QRectF:
        return QRectF(float(logo.x), float(logo.y), max(8.0, float(logo.w)), max(8.0, float(logo.h)))

    def _hit_logo(self, page_pos: QPointF) -> Optional[LogoItem]:
        for logo in reversed(self.logos):
            if self._logo_rect(logo).contains(page_pos):
                return logo
        return None

    def _logo_pixmap(self, logo: LogoItem) -> QPixmap:
        pix = QPixmap()
        try:
            pix.loadFromData(base64.b64decode(logo.data_base64))
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        return pix

    # ---------- Drawing ----------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        use_vector = bool(getattr(self, "vector_preview", False) and getattr(self, "vector_mode", False))
        if not use_vector:
            painter.fillRect(self.rect(), QColor(theme.GRUND))
        scale, ox, oy = self.page_transform()
        preview_scale = scale * max(1.0, float(self.devicePixelRatioF()))
        painter.translate(ox, oy)
        painter.scale(scale, scale)
        self.draw_page(painter, render_scale=preview_scale, skip_tiles=use_vector)
        painter.end()

    def render_to_image(self, width: int, height: int, base_map_image: Optional[QImage] = None) -> QImage:
        img = QImage(width, height, QImage.Format.Format_RGB32)
        img.fill(QColor("#ffffff"))
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        pw, ph = self.page_size()
        export_scale_x = width / pw
        export_scale_y = height / ph
        painter.scale(export_scale_x, export_scale_y)
        if base_map_image is not None and not base_map_image.isNull():
            mr = self.map_rect()
            painter.fillRect(QRectF(0, 0, pw, ph), QColor("#000000"))
            painter.drawImage(
                mr,
                base_map_image,
                QRectF(0, 0, base_map_image.width(), base_map_image.height()),
            )
            self.draw_page(painter, export=True, render_scale=1.0, skip_tiles=True)
        else:
            self.draw_page(painter, export=True, render_scale=1.0)
        painter.end()
        return img

    def draw_page(self, p: QPainter, export: bool = False, render_scale: float = 1.0, skip_tiles: bool = False) -> None:
        pw, ph = self.page_size()
        if skip_tiles:
            r = self.map_rect()
            p.fillRect(QRectF(0, 0, pw, r.top()), QColor("#000000"))
            p.fillRect(QRectF(0, r.bottom(), pw, max(0.0, ph - r.bottom())), QColor("#000000"))
            p.fillRect(QRectF(0, r.top(), r.left(), r.height()), QColor("#000000"))
            p.fillRect(QRectF(r.right(), r.top(), max(0.0, pw - r.right()), r.height()), QColor("#000000"))
        else:
            p.fillRect(QRectF(0, 0, pw, ph), QColor("#000000"))
            self._draw_tiles(p, detail_scale=render_scale)
        self._draw_zones(p)
        self._draw_map_title(p)
        if self.show_grid_lines:
            self._draw_grid_lines(p)
        self._draw_routes(p)
        self._draw_markers(p)
        self._draw_logos(p)
        self._draw_notes(p)
        self._draw_scale_bar(p)
        if self.show_grid:
            self._draw_grid_frame(p)
        if not export:
            self._draw_selection(p)

    def _draw_tiles(self, p: QPainter, detail_scale: float = 1.0) -> None:
        r = self.map_rect()
        p.save()
        p.setClipRect(r)
        p.fillRect(r, QColor("#e7e4d6"))

        # Vorschau-Workaround: Unter Linux/Wayland wirken stark skalierte 256er-Kacheln
        # schnell weich. Deshalb wird bei großer Anzeige-Skalierung automatisch eine
        # zusätzliche Detailstufe geladen und auf dieselben Seitenkoordinaten gemappt.
        # Der Export bleibt weiterhin im gewählten DIN-Zielraster.
        boost = 1 if float(detail_scale) >= 1.25 and float(self.zoom) < 19.0 else 0
        base_tile_zoom = int(math.floor(float(self.zoom)))
        tile_zoom = min(19, base_tile_zoom + boost)
        factor = 2 ** (float(tile_zoom) - float(self.zoom))

        cx, cy = latlon_to_world(self.center_lat, self.center_lon, tile_zoom)
        top_left_x = cx - (r.width() * factor) / 2.0
        top_left_y = cy - (r.height() * factor) / 2.0
        min_tx = math.floor(top_left_x / 256.0)
        max_tx = math.floor((top_left_x + r.width() * factor) / 256.0)
        min_ty = math.floor(top_left_y / 256.0)
        max_ty = math.floor((top_left_y + r.height() * factor) / 256.0)
        tile_size = 256.0 / factor

        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                x = r.left() + (tx * 256.0 - top_left_x) / factor
                y = r.top() + (ty * 256.0 - top_left_y) / factor
                target = QRectF(x, y, tile_size, tile_size)
                pix = self.tiles.pixmap(tile_zoom, tx, ty)
                if pix and not pix.isNull():
                    p.drawPixmap(target, pix, QRectF(0, 0, pix.width(), pix.height()))
                else:
                    p.fillRect(target, QColor("#e9e6d8"))
                    pen = QPen(QColor(170, 168, 150, 80), 1)
                    p.setPen(pen)
                    p.drawRect(target)
        # OSM Attribution sichtbar im Export
        p.setPen(QColor(60, 60, 60, 190))
        font = QFont("Arial", 8)
        p.setFont(font)
        p.drawText(r.adjusted(6, 0, -6, -4), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                   self.tiles.attribution())
        p.restore()

    def _draw_map_title(self, p: QPainter) -> None:
        title = self.map_title.strip()
        if not title:
            return
        r = self.map_rect()
        p.save()
        p.setClipRect(r)
        font = QFont("Arial", 22, QFont.Weight.Bold)
        font.setItalic(True)
        doc = QTextDocument()
        doc.setDefaultFont(font)
        doc.setPlainText(title)
        w = min(r.width() - 28.0, max(40.0, float(doc.idealWidth()) + 20.0))
        doc.setTextWidth(w - 16.0)
        h = max(34.0, float(doc.size().height()) + 10.0)
        rect = QRectF(r.left() + 14, r.top() + 10, w, h)
        bg = QColor(self.title_bg_color)
        if not bg.isValid():
            bg = QColor("#ffffff")
        bg.setAlpha(int(clamp(self.title_bg_alpha, 0, 255)))
        if bg.alpha() > 0:
            p.fillRect(rect, bg)
        tc = QColor(getattr(self, "title_text_color", "#000000"))
        if not tc.isValid():
            tc = QColor("#000000")
        p.setPen(tc)
        p.setFont(font)
        p.drawText(rect.adjusted(8, 5, -8, -5),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, title)
        p.restore()

    def grid_counts(self) -> Tuple[int, int]:
        return GRID_PRESETS[self.orientation].get(self.grid_density, GRID_PRESETS[self.orientation]["Locker"])

    def _draw_grid_lines(self, p: QPainter) -> None:
        r = self.map_rect()
        cols, rows = self.grid_counts()
        p.save()
        p.setClipRect(r)
        p.setPen(QPen(QColor(55, 55, 55, 85), 1.0))
        for i in range(1, cols):
            x = r.left() + r.width() * i / cols
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        for j in range(1, rows):
            y = r.top() + r.height() * j / rows
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        p.restore()

    def _draw_grid_frame(self, p: QPainter) -> None:
        pw, ph = self.page_size()
        b = self.border
        r = self.map_rect()
        cols, rows = self.grid_counts()
        red = QColor("#ff0505")
        dark_red = QColor("#b00000")
        p.save()
        p.fillRect(QRectF(0, 0, pw, b), red)
        p.fillRect(QRectF(0, ph - b, pw, b), red)
        p.fillRect(QRectF(0, b, b, ph - 2 * b), red)
        p.fillRect(QRectF(pw - b, b, b, ph - 2 * b), red)
        p.setPen(QPen(dark_red, 1))
        # top/bottom separators
        for i in range(cols + 1):
            x = r.left() + r.width() * i / cols
            p.drawLine(QPointF(x, 0), QPointF(x, b))
            p.drawLine(QPointF(x, ph - b), QPointF(x, ph))
        for j in range(rows + 1):
            y = r.top() + r.height() * j / rows
            p.drawLine(QPointF(0, y), QPointF(b, y))
            p.drawLine(QPointF(pw - b, y), QPointF(pw, y))
        p.setPen(QColor("#050505"))
        p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        letters = [chr(ord('A') + i) for i in range(cols)]
        for i, letter in enumerate(letters):
            cell = QRectF(r.left() + r.width() * i / cols, 0, r.width() / cols, b)
            p.drawText(cell, Qt.AlignmentFlag.AlignCenter, letter)
            cell2 = QRectF(r.left() + r.width() * i / cols, ph - b, r.width() / cols, b)
            p.drawText(cell2, Qt.AlignmentFlag.AlignCenter, letter)
        p.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        for j in range(rows):
            num = str(j + 1)
            cell_l = QRectF(0, r.top() + r.height() * j / rows, b, r.height() / rows)
            cell_r = QRectF(pw - b, r.top() + r.height() * j / rows, b, r.height() / rows)
            p.save()
            p.translate(cell_l.center())
            p.rotate(-90)
            p.drawText(QRectF(-cell_l.height()/2, -cell_l.width()/2, cell_l.height(), cell_l.width()),
                       Qt.AlignmentFlag.AlignCenter, num)
            p.restore()
            p.save()
            p.translate(cell_r.center())
            p.rotate(90)
            p.drawText(QRectF(-cell_r.height()/2, -cell_r.width()/2, cell_r.height(), cell_r.width()),
                       Qt.AlignmentFlag.AlignCenter, num)
            p.restore()
        p.restore()

    def _draw_zones(self, p: QPainter) -> None:
        r = self.map_rect()
        p.save()
        p.setClipRect(r)
        def draw_zone_points(points, color_hex, width, fill_alpha=0):
            if not points:
                return
            page_points = [self.latlon_to_page(lat, lon) for lat, lon in points]
            pen_color = QColor(color_hex)
            if not pen_color.isValid():
                pen_color = QColor("#ff0505")
            p.setPen(QPen(pen_color, max(1, int(width)), Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for a, b in zip(page_points, page_points[1:]):
                p.drawLine(a, b)
            p.setBrush(pen_color)
            for point in page_points:
                p.drawEllipse(point, 4.0, 4.0)
        for z in self.zones:
            path = self._zone_path(z)
            fill = QColor(z.fill_color)
            if not fill.isValid():
                fill = QColor("#ff0505")
            fill.setAlpha(int(clamp(z.fill_alpha, 0, 255)))
            border = QColor(z.border_color)
            if not border.isValid():
                border = QColor("#ff0505")
            p.fillPath(path, fill)
            p.setPen(QPen(border, max(1, int(z.border_width)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(path)
            if z.label.strip() and z.points:
                page_points = [self.latlon_to_page(lat, lon) for lat, lon in z.points]
                if z.label_position == "Mitte":
                    x = sum(pt.x() for pt in page_points) / len(page_points)
                    y = sum(pt.y() for pt in page_points) / len(page_points)
                    center = QPointF(x, y)
                else:
                    br = QPolygonF(page_points).boundingRect()
                    if z.label_position == "Oben":
                        center = QPointF(br.center().x(), br.top())
                    elif z.label_position == "Unten":
                        center = QPointF(br.center().x(), br.bottom())
                    elif z.label_position == "Links":
                        center = QPointF(br.left(), br.center().y())
                    else:
                        center = QPointF(br.right(), br.center().y())
                font = QFont("Arial", z.label_font)
                font.setBold(z.label_bold)
                font.setItalic(z.label_italic)
                font.setUnderline(z.label_underline)
                color = QColor(z.text_color)
                if not color.isValid():
                    color = QColor("#000000")
                doc = QTextDocument()
                doc.setDefaultFont(font)
                safe_label = html.escape(z.label).replace("\n", "<br>")
                doc.setHtml(f'<span style="color:{color.name()};">{safe_label}</span>')
                w = min(360.0, max(50.0, float(doc.idealWidth()) + 18.0))
                doc.setTextWidth(w - 16.0)
                h = max(24.0, float(doc.size().height()) + 10.0)
                rect = QRectF(center.x() - w/2.0, center.y() - h/2.0, w, h)
                bg = QColor(getattr(z, "label_bg_color", "#ffffff"))
                if not bg.isValid():
                    bg = QColor("#ffffff")
                bg.setAlpha(int(clamp(z.label_bg_alpha, 0, 255)))
                if bg.alpha() > 0:
                    p.fillRect(rect, bg)
                p.save()
                p.setClipRect(rect.adjusted(8, 5, -8, -5))
                p.translate(rect.left() + 8, rect.top() + 5)
                doc.drawContents(p, QRectF(0, 0, rect.width()-16, rect.height()-10))
                p.restore()
        if self.active_zone_points:
            draw_zone_points(self.active_zone_points, self.current_zone_border_color, self.current_zone_border_width)
        p.restore()

    def _draw_scale_bar(self, p: QPainter) -> None:
        if not self.show_scale:
            return
        r = self.map_rect()
        meters = max(1.0, float(self.scale_length_m))
        meters_per_px = 156543.03392 * math.cos(math.radians(self.center_lat)) / (2 ** self.zoom)
        if meters_per_px <= 0:
            return
        length_px = meters / meters_per_px
        if length_px > r.width() * 0.8:
            length_px = r.width() * 0.8
        margin = 18.0
        pos = self.scale_position
        if "Rechts" in pos:
            x1 = r.right() - margin - length_px
        else:
            x1 = r.left() + margin
        if "oben" in pos.lower() or "Oben" in pos:
            y = r.top() + margin + 20
        else:
            y = r.bottom() - margin - 20
        x2 = x1 + length_px
        label = f"{int(meters)} m" if meters < 1000 else f"{meters/1000:g} km"
        p.save()
        p.setOpacity(clamp(float(getattr(self, "scale_alpha", 255)), 0, 255) / 255.0)
        p.setPen(QPen(QColor("#000000"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        p.drawLine(QPointF(x1, y), QPointF(x2, y))
        p.drawLine(QPointF(x1, y-8), QPointF(x1, y+8))
        p.drawLine(QPointF(x2, y-8), QPointF(x2, y+8))
        p.setPen(QPen(QColor("#ffffff"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        p.drawLine(QPointF(x1, y), QPointF(x2, y))
        p.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        p.setPen(QColor("#000000"))
        p.fillRect(QRectF(x1, y+9, max(72.0, length_px), 22), QColor(255, 255, 255, 190))
        p.drawText(QRectF(x1, y+9, max(72.0, length_px), 22), Qt.AlignmentFlag.AlignCenter, label)
        p.restore()

    def _draw_routes(self, p: QPainter) -> None:
        r = self.map_rect()
        p.save()
        p.setClipRect(r)

        def draw_poly(points: List[Tuple[float, float]], color_hex: str, width: int, dashed: bool = False, show_points: bool = False, opacity: int = 100) -> None:
            if not points:
                return
            p.save()
            p.setOpacity(clamp(float(opacity), 0.0, 100.0) / 100.0)
            color = QColor(color_hex)
            if not color.isValid():
                color = QColor("#ff0505")
            style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
            p.setPen(QPen(color, max(1, int(width)), style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            page_points = [self.latlon_to_page(lat, lon) for lat, lon in points]
            if len(page_points) >= 2:
                path = QPainterPath(page_points[0])
                for pt in page_points[1:]:
                    path.lineTo(pt)
                # Als ein zusammenhängender Pfad zeichnen. So entstehen bei reduzierter
                # Deckkraft keine dunkleren Überlappungs-Punkte an Segmentgrenzen.
                p.drawPath(path)
            if show_points:
                p.setPen(QPen(QColor("#000000"), 1.2))
                p.setBrush(color)
                for point in page_points:
                    p.drawEllipse(point, 4.0, 4.0)
            p.restore()

        for route in self.routes:
            draw_poly(route.points, route.color, route.width, False, False, getattr(route, "opacity", 80))
        if self.active_route_points:
            draw_poly(self.active_route_points, self.current_route_color, self.current_route_width, True, True, getattr(self, "current_route_opacity", 80))
        p.restore()

    def _marker_label_size(self, marker: Marker, text: str) -> Tuple[float, float]:
        if not text.strip():
            return 0.0, 0.0
        font = QFont("Arial", marker.label_font)
        font.setBold(marker.label_bold)
        font.setItalic(marker.label_italic)
        font.setUnderline(marker.label_underline)
        doc = QTextDocument()
        doc.setDefaultFont(font)
        doc.setPlainText(text)
        natural_w = max(36.0, min(320.0, float(doc.idealWidth())))
        doc.setTextWidth(natural_w)
        size = doc.size()
        return max(44.0, size.width() + 14.0), max(22.0, size.height() + 10.0)

    def _marker_rects(self, marker: Marker) -> Tuple[QRectF, QRectF]:
        center = self.latlon_to_page(marker.lat, marker.lon)
        s = marker.icon_size
        icon_rect = QRectF(center.x() - s / 2, center.y() - s / 2, s, s)
        text = marker.description.strip() or marker.label.strip()
        w, h = self._marker_label_size(marker, text)
        gap = marker.label_gap
        pos = marker.label_position
        if pos == "Oben":
            label_rect = QRectF(center.x() - w / 2, icon_rect.top() - gap - h, w, h)
        elif pos == "Unten":
            label_rect = QRectF(center.x() - w / 2, icon_rect.bottom() + gap, w, h)
        elif pos == "Links":
            label_rect = QRectF(icon_rect.left() - gap - w, center.y() - h / 2, w, h)
        else:
            label_rect = QRectF(icon_rect.right() + gap, center.y() - h / 2, w, h)
        return icon_rect, label_rect

    def _draw_logos(self, p: QPainter) -> None:
        p.save()
        p.setClipRect(QRectF(0, 0, *self.page_size()).adjusted(-500, -500, 500, 500))
        for logo in self.logos:
            rect = self._logo_rect(logo)
            pix = self._logo_pixmap(logo)
            if pix and not pix.isNull():
                p.drawPixmap(rect, pix, QRectF(0, 0, pix.width(), pix.height()))
        p.restore()

    def _draw_markers(self, p: QPainter) -> None:
        r = self.map_rect()
        p.save()
        p.setClipRect(r.adjusted(-300, -300, 300, 300))
        if self.route_mode:
            p.setOpacity(0.30)
        for marker in self.markers:
            icon_rect, label_rect = self._marker_rects(marker)
            pix = self.icon_factory.pixmap(marker.symbol, marker.color)
            p.drawPixmap(icon_rect, pix, QRectF(0, 0, pix.width(), pix.height()))
            text = marker.description.strip() or marker.label.strip()
            if text:
                bg = QColor("#ffffff")
                bg.setAlpha(int(clamp(marker.label_bg_alpha, 0, 255)))
                if bg.alpha() > 0:
                    p.fillRect(label_rect, bg)
                color = QColor(marker.text_color)
                if not color.isValid():
                    color = QColor("#000000")
                p.setPen(color)
                font = QFont("Arial", marker.label_font)
                font.setBold(marker.label_bold)
                font.setItalic(marker.label_italic)
                font.setUnderline(marker.label_underline)
                p.setFont(font)
                p.drawText(label_rect.adjusted(7, 5, -7, -5),
                           Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                           text)
        p.restore()

    def _note_document(self, n: NoteBox, text_width: Optional[float] = None) -> QTextDocument:
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        base_font = QFont("Arial", n.font)
        base_font.setBold(n.bold)
        base_font.setItalic(n.italic)
        base_font.setUnderline(n.underline)
        doc.setDefaultFont(base_font)
        text_color = QColor(getattr(n, "text_color", "#000000"))
        if not text_color.isValid():
            text_color = QColor("#000000")
        align = getattr(n, "align", "Links")
        align_css = "center" if align == "Zentriert" else ("right" if align == "Rechts" else "left")
        doc.setDefaultStyleSheet(
            f"body, p {{ color: {text_color.name()}; font-family: Arial; font-size: {int(n.font)}pt; text-align: {align_css}; }} "
            "span { vertical-align: baseline; } img { vertical-align: middle; }"
        )
        if n.text_html:
            clean_html = n.text_html
            # Font-Größe der Legende einheitlich halten, Inline-Farben aber erhalten.
            clean_html = re.sub(
                r"font-size\s*:\s*[^;\"]+;?",
                f"font-size:{int(n.font)}pt;",
                clean_html,
                flags=re.IGNORECASE,
            )
            # Eingebettete Symbolbilder für Legenden/Textfelder als Dokument-Ressourcen nachladen.
            for src in re.findall(r'src=["\'](aktionsicon:[^"\']+)["\']', clean_html):
                try:
                    parts = src.split(":", 2)
                    key = parts[1]
                    raw_color = parts[2] if len(parts) > 2 else "000000"
                    raw_color = raw_color.replace("%23", "#")
                    color = raw_color if raw_color.startswith("#") else "#" + raw_color
                    pix = self.icon_factory.pixmap(key, color)
                    image = pix.toImage()
                    doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(src), image)
                    doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(src.replace("%23", "#")), image)
                    doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(src.replace("#", "")), image)
                except Exception as exc:
                    log_debug("Stiller Fehler", exc)
            if getattr(n, "include_routes", False) and self.routes:
                route_html = "".join(
                    f'<div><span style="color:{html.escape(r.color)}; font-weight:bold; font-size:{int(n.font)}pt;">{html.escape(r.name or ("Route " + str(r.id)))}</span></div>'
                    for r in self.routes
                )
                insert = f'<div style="margin-top:6px;">{route_html}</div>'
                if re.search(r"</body>", clean_html, flags=re.IGNORECASE):
                    clean_html = re.sub(r"</body>", insert + "</body>", clean_html, flags=re.IGNORECASE)
                else:
                    clean_html += insert
            doc.setHtml(clean_html)
        else:
            base_text = n.text
            if getattr(n, "include_routes", False) and self.routes:
                route_lines = "\n".join(r.name or ("Route " + str(r.id)) for r in self.routes)
                base_text = (base_text + "\n" + route_lines).strip()
            doc.setPlainText(base_text)
        if text_width is not None:
            doc.setTextWidth(max(20.0, float(text_width)))
        try:
            doc.adjustSize()
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        return doc

    def _note_auto_size(self, n: NoteBox) -> Tuple[float, float]:
        r = self.map_rect()
        pad_x = 16.0
        pad_y = 12.0
        doc = self._note_document(n)
        min_w = 90.0
        # Textfelder sollen sich so weit wie nötig verbreitern und erst dann umbrechen,
        # wenn die verfügbare Kartenbreite wirklich ausgereizt ist.
        max_w = max(min_w, float(r.width()) - 20.0)
        natural_w = float(doc.idealWidth()) + pad_x
        w = clamp(natural_w, min_w, max_w)
        doc = self._note_document(n, w - pad_x)
        h = float(doc.size().height()) + pad_y
        h = clamp(h, 28.0, max(40.0, r.height() - 20.0))
        return w, h

    def _note_rect(self, n: NoteBox) -> QRectF:
        r = self.map_rect()
        margin = 10.0
        w, h = self._note_auto_size(n)
        if n.position == "Zentriert":
            return QRectF(r.center().x() - w / 2.0, r.center().y() - h / 2.0, w, h)
        if n.position == "Links oben":
            return QRectF(r.left() + margin, r.top() + margin, w, h)
        if n.position == "Links unten":
            return QRectF(r.left() + margin, r.bottom() - margin - h, w, h)
        if n.position == "Rechts unten":
            return QRectF(r.right() - margin - w, r.bottom() - margin - h, w, h)
        return QRectF(r.right() - margin - w, r.top() + margin, w, h)

    def _draw_notes(self, p: QPainter) -> None:
        p.save()
        for n in self.notes:
            if not getattr(n, "visible", True):
                continue
            rect = self._note_rect(n)
            bg = QColor(n.bg_color)
            if not bg.isValid():
                bg = QColor("#ffffff")
            bg.setAlpha(int(clamp(getattr(n, "bg_alpha", 255), 0, 255)))
            if bg.alpha() > 0:
                p.fillRect(rect, bg)

            inner = rect.adjusted(8, 6, -8, -6)
            p.save()
            p.setClipRect(inner)
            p.translate(inner.topLeft())
            doc = self._note_document(n, inner.width())
            doc.drawContents(p, QRectF(0, 0, inner.width(), inner.height()))
            p.restore()
        p.restore()

    def _draw_selection(self, p: QPainter) -> None:
        p.save()
        p.setPen(QPen(QColor("#00ffff"), 2.0, Qt.PenStyle.DashLine))
        ids_to_draw = set(self.selected_marker_ids)
        if self.selected_marker_id is not None:
            ids_to_draw.add(self.selected_marker_id)
        for m in self.markers:
            if m.id in ids_to_draw:
                icon_rect, label_rect = self._marker_rects(m)
                p.drawRect(icon_rect.adjusted(-4, -4, 4, 4))
        note_ids = set(self.selected_note_ids)
        if self.selected_note_id is not None:
            note_ids.add(self.selected_note_id)
        for n in self.notes:
            if n.id in note_ids:
                p.drawRect(self._note_rect(n).adjusted(-3, -3, 3, 3))
        logo_ids = set(self.selected_logo_ids)
        if self.selected_logo_id is not None:
            logo_ids.add(self.selected_logo_id)
        for logo in self.logos:
            if logo.id in logo_ids:
                p.drawRect(self._logo_rect(logo).adjusted(-3, -3, 3, 3))
        zone_ids = set(self.selected_zone_ids)
        if self.selected_zone_id is not None:
            zone_ids.add(self.selected_zone_id)
        for z in self.zones:
            if z.id in zone_ids:
                p.drawPath(self._zone_path(z))
        # Routen-Auswahl wird als cyanfarbene Linie darübergelegt.
        route_ids = set(self.selected_route_ids)
        if self.selected_route_id is not None:
            route_ids.add(self.selected_route_id)
        for route in self.routes:
            if route.id in route_ids:
                pts = [self.latlon_to_page(lat, lon) for lat, lon in route.points]
                for a, b in zip(pts, pts[1:]):
                    p.drawLine(a, b)
        p.restore()



class MapLibreContainer(QWidget):
    def __init__(self, canvas: MapCanvas, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.web = None
        self.profile = None
        self.scheme_handler = None
        self._loaded = False
        self._load_started = False
        self._sync_scheduled = False
        self.missing_files = maplibre_files_missing()
        self.canvas.vector_preview = bool(HAS_WEBENGINE and QWebEngineView is not None and not self.missing_files)
        self.canvas.vector_map_sync_callback = self.schedule_sync

        layout = QStackedLayout(self)
        layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        layout.setContentsMargins(0, 0, 0, 0)
        if self.canvas.vector_preview:
            try:
                # Eigenes Profil ohne Namen: nichts wird auf die Festplatte geschrieben
                # (kein Karten-Cache, keine Cookies über das Programmende hinaus).
                self.profile = QWebEngineProfile(self)
                self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
                self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
                self.scheme_handler = MapLibreSchemeHandler(self._html, self)
                self.profile.installUrlSchemeHandler(MAPLIBRE_SCHEME, self.scheme_handler)
                self.web = QWebEngineView(self)
                self.web.setPage(MapLibrePage(self.profile, self.web))
                # Auch die noch leere Seite ist dunkel, nicht weiß.
                self.web.page().setBackgroundColor(QColor(theme.GRUND))
                layout.addWidget(self.web)
                self.web.loadFinished.connect(self._map_loaded)
                # Die Kartenseite wird erst geladen, wenn die Vektor-Ansicht gewählt wird.
                # In der Raster-Ansicht geht deshalb nichts an den Vektor-Kartendienst.
            except Exception as exc:
                log_debug("MapLibre-Vorschau konnte nicht gestartet werden", exc)
                self.web = None
                self.canvas.vector_preview = False
        layout.addWidget(self.canvas)
        self.canvas.raise_()
        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.timeout.connect(self._update_web_geometry)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.canvas.setGeometry(self.rect())
        self._geometry_timer.start(0)
        self.schedule_sync()

    def _map_loaded(self, ok: bool) -> None:
        self._loaded = bool(ok)
        self._update_web_geometry()
        self.schedule_sync()

    def _update_web_geometry(self) -> None:
        if not self.web:
            return
        scale, ox, oy = self.canvas.page_transform()
        mr = self.canvas.map_rect()
        x = int(round(ox + mr.left() * scale))
        y = int(round(oy + mr.top() * scale))
        w = max(1, int(round(mr.width() * scale)))
        h = max(1, int(round(mr.height() * scale)))
        self.web.setGeometry(x, y, w, h)
        self.web.lower()

    def maplibre_zoom(self) -> float:
        scale, _ox, _oy = self.canvas.page_transform()
        return max(0.0, float(self.canvas.zoom) - 1.0 + math.log2(max(1e-6, float(scale))))

    def _filter_config(self) -> dict:
        return {
            "enabled": bool(getattr(self.canvas, "poi_filter_enabled", False) and getattr(self.canvas, "vector_mode", False)),
            "show_names": bool(getattr(self.canvas, "poi_show_names", True)),
            "show_icons": bool(getattr(self.canvas, "poi_show_icons", True)),
            "categories": sorted(getattr(self.canvas, "poi_categories_enabled", set(POI_CATEGORY_LABELS.keys()))),
            "zoom_offset": float(getattr(self.canvas, "poi_zoom_offset", 0.0)),
        }

    def schedule_sync(self) -> None:
        if self._sync_scheduled:
            return
        self._sync_scheduled = True
        QTimer.singleShot(0, self._sync_now)

    def _sync_now(self) -> None:
        self._sync_scheduled = False
        if not self.web:
            return
        if not bool(getattr(self.canvas, "vector_mode", False)):
            return
        if not self._load_started:
            self._load_started = True
            try:
                self.web.load(QUrl(MAPLIBRE_PAGE_URL))
            except Exception as exc:
                log_debug("Vektorkarte konnte nicht geladen werden", exc)
            return
        self._update_web_geometry()
        lon = float(self.canvas.center_lon)
        lat = float(self.canvas.center_lat)
        zoom = self.maplibre_zoom()
        style = MAPLIBRE_STYLES.get(self.canvas.map_layer, MAPLIBRE_STYLES["Standard"])
        config = self._filter_config()
        js = (
            "(function() { if (window.aktionsMapSet) {"
            f"window.aktionsMapSet({lon:.10f}, {lat:.10f}, {zoom:.4f}, {json.dumps(style)}, {json.dumps(config)});"
            " return 'ok:' + (window.aktionsPoiLayerCount ? window.aktionsPoiLayerCount() : -1); } return 'wait'; })()"
        )
        try:
            self.web.page().runJavaScript(js, self._sync_result)
        except Exception as exc:
            log_debug("Vektorkarte konnte nicht synchronisiert werden", exc)

    def _note_poi_layer_count(self, value: str) -> None:
        # -1 = Stil lädt noch, 0 = Kartenebene ohne POIs, sonst Anzahl der POI-Ebenen.
        try:
            count = int(value.split(":", 1)[1]) if ":" in value else -1
        except Exception:
            count = -1
        if count < 0:
            waits = int(getattr(self, "_style_waits", 0))
            if waits < 60 and bool(getattr(self.canvas, "vector_mode", False)):
                self._style_waits = waits + 1
                QTimer.singleShot(400, self.schedule_sync)
        else:
            self._style_waits = 0
        if count != int(getattr(self.canvas, "vector_poi_layers", -1)):
            self.canvas.vector_poi_layers = count
            callback = getattr(self, "poi_layers_changed", None)
            if callable(callback):
                try:
                    callback()
                except Exception as exc:
                    log_debug("Stiller Fehler", exc)

    def reload_vector_map(self) -> None:
        if not self.web:
            return
        try:
            self.web.page().runJavaScript("window.aktionsReload && window.aktionsReload();")
        except Exception as exc:
            log_debug("Vektorkarte konnte nicht neu geladen werden", exc)
        self.schedule_sync()

    def _sync_result(self, value) -> None:
        if isinstance(value, str) and value.startswith("ok"):
            self._sync_retries = 0
            self._note_poi_layer_count(value)
            if not getattr(self, "_first_sync_done", False):
                self._first_sync_done = True
                QTimer.singleShot(300, self.schedule_sync)
                QTimer.singleShot(1200, self.schedule_sync)
            return
        retries = int(getattr(self, "_sync_retries", 0))
        if retries < 80 and bool(getattr(self.canvas, "vector_mode", False)):
            self._sync_retries = retries + 1
            QTimer.singleShot(150, self.schedule_sync)

    def capture_map_image(self, target_width: int, target_height: int) -> Optional[QImage]:
        if not self.web or not self.canvas.vector_preview:
            return None
        target_width = max(32, int(target_width))
        target_height = max(32, int(target_height))
        css_w = max(1, int(self.web.width()))
        # Der geografische Ausschnitt bleibt gleich; nur der WebGL-Pixelratio wird für
        # den Export hochgesetzt. So bleibt die Vektorkarte bei A3/A4 scharf.
        desired_ratio = max(1.0, min(6.0, float(target_width) / float(css_w)))
        result = {"value": None}
        loop = QEventLoop()
        timed_out = {"value": False}

        def finish(value):
            if value:
                result["value"] = value
                loop.quit()
            else:
                QTimer.singleShot(80, poll)

        def poll():
            if timed_out["value"] or not self.web:
                return
            try:
                self.web.page().runJavaScript("window.aktionsCaptureResult || ''", finish)
            except Exception:
                loop.quit()

        try:
            self.web.page().runJavaScript(f"window.aktionsPrepareCapture && window.aktionsPrepareCapture({desired_ratio:.5f});")
            timeout = QTimer()
            timeout.setSingleShot(True)
            def timeout_now():
                timed_out["value"] = True
                loop.quit()
            timeout.timeout.connect(timeout_now)
            timeout.start(6500)
            QTimer.singleShot(120, poll)
            loop.exec()
            timeout.stop()
        except Exception as exc:
            log_debug("Vektorkarte konnte nicht für Export erfasst werden", exc)
            result["value"] = None
        finally:
            try:
                if self.web:
                    self.web.page().runJavaScript("window.aktionsRestoreCapture && window.aktionsRestoreCapture();")
            except Exception:
                pass

        data_url = result.get("value")
        if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
            return None
        try:
            raw = base64.b64decode(data_url.split(",", 1)[1])
            img = QImage.fromData(raw, "PNG")
            if img.isNull():
                return None
            return img
        except Exception as exc:
            log_debug("Vektor-Exportbild konnte nicht dekodiert werden", exc)
            return None

    def _html(self) -> str:
        styles = json.dumps(MAPLIBRE_STYLES, ensure_ascii=False)
        groups = json.dumps(POI_CATEGORY_VALUES, ensure_ascii=False)
        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="maplibre-gl.css">
<style>
html, body, #map {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:{theme.GRUND}; }}
.maplibregl-ctrl-attrib {{ font: 10px/13px Arial, sans-serif; }}
</style>
</head>
<body>
<div id="map"></div>
<script type="module">
let maplibregl = null;
try {{
  maplibregl = await import("./maplibre-gl.mjs");
  maplibregl.setWorkerUrl(new URL("./maplibre-gl-worker.mjs", window.location.href).href);
}} catch(e) {{ console.warn("MapLibre", e); }}
const styles = {styles};
const poiGroups = {groups};
let currentStyle = styles["Standard"];
let map = null;
let originalPoiLayers = {{}};
let currentConfig = {{enabled:false, show_names:true, show_icons:true, categories:[], zoom_offset:0}};
let oldCaptureRatio = null;
let currentStyleKey = "";
let lastLoggedConfig = "";
let lastLoggedSize = "";
let nudgePending = false;
let styleReady = false;
window.aktionsCaptureResult = "";

function sizeInfo() {{
  const m = document.getElementById("map");
  const c = map ? map.getCanvas() : null;
  return "Fenster " + window.innerWidth + "x" + window.innerHeight + " Karte " + m.clientWidth + "x" + m.clientHeight
    + (c ? " Canvas " + c.clientWidth + "x" + c.clientHeight : "");
}}
function logSize(tag) {{
  const info = sizeInfo();
  if (tag === "resize" && info === lastLoggedSize) return;
  lastLoggedSize = info;
  console.log(tag + ": " + info + (map ? " Zoom " + map.getZoom().toFixed(2) : ""));
}}
function fitMap() {{
  if (!map) return;
  try {{ map.resize(); map.triggerRepaint(); }} catch(e) {{ console.warn("resize", String(e)); }}
  logSize("resize");
}}
// Nach dem Laden eines Stils einmal kurz den Zoom bewegen: damit werden alle Kacheln der
// Ansicht angefordert (am PC blieben sonst Flächen leer, bis der Zoom geändert wurde).
function nudge() {{
  if (!map) return;
  try {{
    const z = map.getZoom();
    map.jumpTo({{zoom: z + 0.05}});
    requestAnimationFrame(() => {{ try {{ map.jumpTo({{zoom: z}}); map.resize(); }} catch(e) {{}} logSize("nachgeladen"); }});
  }} catch(e) {{ console.warn("nachladen", String(e)); }}
}}

function valuesForCategories(keys) {{
  let out = [];
  for (const key of keys || []) {{
    if (poiGroups[key]) out = out.concat(poiGroups[key]);
  }}
  return [...new Set(out)];
}}
function allKnownValues() {{
  let out = [];
  for (const key of Object.keys(poiGroups)) out = out.concat(poiGroups[key]);
  return [...new Set(out)];
}}
function anyIn(values) {{
  if (!values.length) return ["==", "class", "__aktionskarten_never__"];
  return ["any", ["in", "class", ...values], ["in", "subclass", ...values]];
}}
function noneIn(values) {{
  if (!values.length) return ["all"];
  return ["all", ["!in", "class", ...values], ["!in", "subclass", ...values]];
}}
// Die POI-Ebenen der Kartenstile filtern in Ausdrucks-Schreibweise. Alte und neue
// Schreibweise dürfen in einem Filter nicht gemischt werden, sonst greift er falsch.
function isExpressionFilter(filter) {{
  if (filter === true || filter === false) return true;
  if (!Array.isArray(filter) || filter.length === 0) return false;
  switch (filter[0]) {{
    case "has": return filter.length >= 2 && filter[1] !== "$id" && filter[1] !== "$type";
    case "in": return filter.length >= 3 && (typeof filter[1] !== "string" || Array.isArray(filter[2]));
    case "!in": case "!has": case "none": return false;
    case "==": case "!=": case ">": case ">=": case "<": case "<=":
      return filter.length !== 3 || Array.isArray(filter[1]) || Array.isArray(filter[2]);
    case "any": case "all":
      for (const f of filter.slice(1)) {{ if (!isExpressionFilter(f) && typeof f !== "boolean") return false; }}
      return true;
    default: return true;
  }}
}}
function matchProp(prop, values) {{
  return ["match", ["get", prop], values, true, false];
}}
function anyInExpr(values) {{
  if (!values.length) return false;
  return ["any", matchProp("class", values), matchProp("subclass", values)];
}}
function noneInExpr(values) {{
  if (!values.length) return true;
  return ["all", ["!", matchProp("class", values)], ["!", matchProp("subclass", values)]];
}}
function categoryFilterFor(original, allowedKnown, known, allowOther) {{
  if (original && !isExpressionFilter(original)) {{
    const extra = allowOther ? ["any", anyIn(allowedKnown), noneIn(known)] : anyIn(allowedKnown);
    return ["all", original, extra];
  }}
  const extra = allowOther ? ["any", anyInExpr(allowedKnown), noneInExpr(known)] : anyInExpr(allowedKnown);
  return original ? ["all", original, extra] : ["all", extra];
}}
function snapshotPoiLayers() {{
  originalPoiLayers = {{}};
  if (!map || !map.getStyle()) return;
  for (const layer of (map.getStyle().layers || [])) {{
    if (layer.type !== "symbol" || layer["source-layer"] !== "poi") continue;
    const layout = layer.layout || {{}};
    originalPoiLayers[layer.id] = {{
      source: layer.source,
      filter: layer.filter || null,
      visibility: layout.visibility || "visible",
      textField: layout["text-field"],
      iconImage: layout["icon-image"],
      minzoom: layer.minzoom,
      maxzoom: layer.maxzoom
    }};
  }}
}}
// Verschiebt den Mindest-Zoom einer POI-Ebene. Ebenen ohne Mindest-Zoom bleiben, wie sie sind.
function setZoomRange(id, state, offset) {{
  if (state.minzoom === undefined) return;
  const min = Math.max(0, Math.min(24, state.minzoom + offset));
  const max = state.maxzoom === undefined ? 24 : state.maxzoom;
  if (state.appliedMin === min) return;
  map.setLayerZoomRange(id, min, max);
  state.appliedMin = min;
}}
function applyPoiFilter() {{
  if (!map || !map.getStyle()) return;
  const enabled = !!currentConfig.enabled;
  const selectedCategories = new Set(currentConfig.categories || []);
  const allowOther = selectedCategories.has("other");
  const allowedKnown = valuesForCategories([...selectedCategories].filter(x => x !== "other"));
  const known = allKnownValues();
  const zoomOffset = Number(currentConfig.zoom_offset) || 0;

  for (const [id, state] of Object.entries(originalPoiLayers)) {{
    if (!map.getLayer(id)) continue;
    try {{
      if (!enabled) {{
        map.setFilter(id, state.filter || null);
        map.setLayoutProperty(id, "visibility", state.visibility || "visible");
        if (state.textField !== undefined) map.setLayoutProperty(id, "text-field", state.textField);
        if (state.iconImage !== undefined) map.setLayoutProperty(id, "icon-image", state.iconImage);
        setZoomRange(id, state, 0);
        continue;
      }}
      map.setLayoutProperty(id, "visibility", state.visibility || "visible");
      setZoomRange(id, state, zoomOffset);
      map.setFilter(id, categoryFilterFor(state.filter, allowedKnown, known, allowOther));
      if (state.textField !== undefined)
        map.setLayoutProperty(id, "text-field", currentConfig.show_names ? state.textField : "");
      if (state.iconImage !== undefined)
        map.setLayoutProperty(id, "icon-image", currentConfig.show_icons ? state.iconImage : "");
    }} catch(e) {{ console.warn("POI-Filter", id, String(e)); }}
  }}
  const key = JSON.stringify(currentConfig);
  if (key !== lastLoggedConfig) {{
    lastLoggedConfig = key;
    console.log("POI-Filter " + key + " Ebenen=" + Object.keys(originalPoiLayers).join(","));
  }}
}}
function createMap(lon, lat, zoom) {{
  map = new maplibregl.Map({{
    container: "map",
    style: currentStyle,
    center: [lon, lat],
    zoom: zoom,
    interactive: false,
    attributionControl: false,
    canvasContextAttributes: {{preserveDrawingBuffer: true}},
  }});
  map.addControl(new maplibregl.AttributionControl({{compact: true}}));
  map.on("style.load", () => {{ snapshotPoiLayers(); styleReady = true; applyPoiFilter(); nudgePending = true; logSize("Stil geladen"); }});
  map.on("idle", () => {{
    if (currentConfig.enabled) applyPoiFilter();
    if (nudgePending) {{ nudgePending = false; nudge(); }}
  }});
  map.on("error", (e) => {{ console.warn("Kartenfehler: " + (e && e.error ? e.error.message : String(e))); }});
  window.addEventListener("resize", fitMap);
  try {{ new ResizeObserver(fitMap).observe(document.getElementById("map")); }} catch(e) {{}}
  logSize("Karte angelegt");
}}
window.aktionsMapSet = function(lon, lat, zoom, styleUrl, config) {{
  currentConfig = config || currentConfig;
  const styleKey = styleUrl ? JSON.stringify(styleUrl) : currentStyleKey;
  if (!map) {{
    if (!maplibregl) return;
    if (styleUrl) {{ currentStyle = styleUrl; currentStyleKey = styleKey; }}
    try {{ createMap(lon, lat, zoom); }} catch(e) {{ map = null; showLoadError(e); }}
    return;
  }}
  if (styleUrl && styleKey !== currentStyleKey) {{
    currentStyle = styleUrl;
    currentStyleKey = styleKey;
    styleReady = false;
    map.setStyle(styleUrl);
  }}
  map.jumpTo({{center: [lon, lat], zoom: zoom}});
  map.resize();
  if (Object.keys(originalPoiLayers).length) applyPoiFilter();
}};
// Anzahl der POI-Ebenen des geladenen Stils; -1, solange der Stil noch lädt.
window.aktionsPoiLayerCount = function() {{
  return styleReady ? Object.keys(originalPoiLayers).length : -1;
}};
// „Map neu laden“ in der Vektor-Ansicht: Stil und Kacheln neu anfordern.
window.aktionsReload = function() {{
  if (!map) return;
  styleReady = false;
  try {{ map.setStyle(currentStyle, {{diff: false}}); }} catch(e) {{ console.warn("neu laden", String(e)); }}
}};
window.aktionsProject = function(lon, lat) {{
  if (!map) return "";
  const p = map.project([lon, lat]);
  return JSON.stringify([p.x, p.y]);
}};
window.aktionsPoiInfo = function() {{
  const out = {{}};
  if (!map) return JSON.stringify(out);
  for (const [id, state] of Object.entries(originalPoiLayers)) {{
    if (!map.getLayer(id)) continue;
    let names = null;
    try {{
      names = map.querySourceFeatures(state.source, {{sourceLayer: "poi", filter: map.getFilter(id)}})
        .map(f => String(f.properties.name || f.properties.class));
      names = [...new Set(names)].sort();
    }} catch(e) {{ names = "Fehler: " + String(e); }}
    out[id] = {{visibility: map.getLayoutProperty(id, "visibility") || "visible", names: names, minzoom: map.getLayer(id).minzoom}};
  }}
  return JSON.stringify(out);
}};
window.aktionsPrepareCapture = function(pixelRatio) {{
  if (!map) return;
  window.aktionsCaptureResult = "";
  try {{
    oldCaptureRatio = map.getPixelRatio();
    map.setPixelRatio(pixelRatio);
    map.resize();
    let done = false;
    const finish = () => {{
      if (done) return;
      done = true;
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        try {{ window.aktionsCaptureResult = map.getCanvas().toDataURL("image/png"); }}
        catch(e) {{ window.aktionsCaptureResult = "ERROR:" + String(e); }}
      }}));
    }};
    if (map.areTilesLoaded && map.areTilesLoaded()) finish();
    else map.once("idle", finish);
    setTimeout(finish, 1800);
  }} catch(e) {{ window.aktionsCaptureResult = "ERROR:" + String(e); }}
}};
window.aktionsRestoreCapture = function() {{
  try {{
    if (map && oldCaptureRatio !== null) {{
      map.setPixelRatio(oldCaptureRatio);
      map.resize();
    }}
  }} catch(e) {{}}
  oldCaptureRatio = null;
}};
function showLoadError(e) {{
  console.warn("MapLibre konnte nicht geladen werden: " + String(e));
  document.body.innerHTML = '<div style="font:14px Arial;padding:12px;color:#222;background:#eee;">MapLibre konnte nicht geladen werden.</div>';
}}
if (!maplibregl) showLoadError("Bibliothek fehlt");
</script>
</body>
</html>"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.icons = IconFactory()
        self.setWindowIcon(QIcon(self.icons.pixmap("kundgebung", "#e14f9e")))
        self.net = QNetworkAccessManager(self)
        self.search_results: List[dict] = []
        self._loading_selection = False
        self._note_live_update_pending = False
        self._note_saved_selection = (0, 0)
        self._note_live_timer = QTimer(self)
        self._note_live_timer.setSingleShot(True)
        self._note_live_timer.timeout.connect(self._perform_live_update_note)
        self.canvas = MapCanvas(self.icons)
        self.map_container = MapLibreContainer(self.canvas)
        self.map_container.poi_layers_changed = self._poi_layers_changed
        self.setCentralWidget(self.map_container)
        self._build_toolbar()
        self._build_controls()
        self._build_status_zoom()
        self._refresh_poi_filter_ui()
        self.statusBar().showMessage(tr_text("Bereit", self._current_lang() if hasattr(self, "language_combo") else "de"))
        self.canvas.markerSelected.connect(self._marker_selected)
        self.canvas.noteSelected.connect(self._note_selected)
        self.canvas.logoSelected.connect(self._logo_selected)
        self.canvas.routeSelected.connect(self._route_selected)
        self.canvas.zoneSelected.connect(self._zone_selected)
        self.canvas.statusChanged.connect(self._canvas_status_changed)
        self._install_shortcuts()
        self.canvas.update_status()
        self._apply_initial_size()

    def _apply_initial_size(self) -> None:
        # Startgröße aus den sizeHints, mindestens die bisherige Arbeitsfläche, aber nie
        # größer als der nutzbare Bildschirm. Größe und Position werden nicht gemerkt.
        try:
            hint = self.sizeHint()
            width = max(hint.width(), 1900)
            height = max(hint.height(), 1050)
            screen = self.screen() or QGuiApplication.primaryScreen()
            if screen is not None:
                avail = screen.availableGeometry()
                width = min(width, max(640, avail.width() - 16))
                height = min(height, max(480, avail.height() - 48))
                self.resize(width, height)
                self.move(
                    avail.left() + max(0, (avail.width() - width) // 2),
                    avail.top() + max(0, (avail.height() - height - 32) // 2),
                )
            else:
                self.resize(width, height)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
            self.resize(1900, 1050)


    def _build_status_zoom(self) -> None:
        self.status_zoom_label = QLabel(f"Zoom {float(self.canvas.zoom):.2f}")
        self.status_zoom_label.setProperty("i18n_source", "Zoom")
        self.status_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.status_zoom_slider.setRange(40, 380)
        self.status_zoom_slider.setSingleStep(1)
        self.status_zoom_slider.setPageStep(5)
        self.status_zoom_slider.setValue(int(round(float(self.canvas.zoom) * 20.0)))
        self.status_zoom_slider.setFixedWidth(220)
        self.status_zoom_slider.valueChanged.connect(self._status_zoom_changed)
        self.statusBar().addPermanentWidget(self.status_zoom_label)
        self.statusBar().addPermanentWidget(self.status_zoom_slider)

    def _status_zoom_changed(self, value: int) -> None:
        zoom = float(value) / 20.0
        self.canvas.center_on(self.canvas.center_lat, self.canvas.center_lon, zoom)
        if hasattr(self, "search_zoom_slider"):
            self.search_zoom_slider.blockSignals(True)
            self.search_zoom_slider.setValue(int(round(zoom * 20.0)))
            self.search_zoom_slider.blockSignals(False)

    def _canvas_status_changed(self, message: str) -> None:
        try:
            self.statusBar().showMessage(message)
            self._update_poi_zoom_label()
            slider_value = int(round(float(self.canvas.zoom) * 20.0))
            if hasattr(self, "status_zoom_slider") and self.status_zoom_slider.value() != slider_value:
                self.status_zoom_slider.blockSignals(True)
                self.status_zoom_slider.setValue(slider_value)
                self.status_zoom_slider.blockSignals(False)
            if hasattr(self, "search_zoom_slider") and self.search_zoom_slider.value() != slider_value:
                self.search_zoom_slider.blockSignals(True)
                self.search_zoom_slider.setValue(slider_value)
                self.search_zoom_slider.blockSignals(False)
            if hasattr(self, "status_zoom_label"):
                self.status_zoom_label.setText(f"{tr_text('Zoom', self._current_lang())} {float(self.canvas.zoom):.2f}")
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def _install_shortcuts(self) -> None:
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_undo.activated.connect(self._undo)
        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.shortcut_redo.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_redo.activated.connect(self._redo)
        self.shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut_select_all.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_select_all.activated.connect(self._select_all_current_category)

    def _select_all_current_category(self) -> None:
        self.canvas.clear_multi_selection()
        idx = self.tools_box.currentIndex() if hasattr(self, "tools_box") else -1
        if idx == 3:  # Symbol-Punkte
            self.canvas.selected_marker_ids = {m.id for m in self.canvas.markers}
        elif idx == 4:  # Route
            self.canvas.selected_route_ids = {r.id for r in self.canvas.routes}
        elif idx == 5:  # Zonen
            self.canvas.selected_zone_ids = {z.id for z in self.canvas.zones}
        elif idx == 6:  # Bilddatei
            self.canvas.selected_logo_ids = {logo.id for logo in self.canvas.logos}
        elif idx == 7:  # Legende / Textfeld
            self.canvas.selected_note_ids = {n.id for n in self.canvas.notes}
        self.canvas.update()

    def _build_toolbar(self) -> None:
        tb = QToolBar("Datei", self)
        tb.setMovable(False)
        self.addToolBar(tb)
        self._i18n_actions = []
        actions = [
            ("Projekt speichern", self.save_project),
            ("Projekt laden", self.load_project),
            ("JPG exportieren", self.export_jpg),
            ("PDF exportieren", self.export_pdf),
            ("Map neu laden", self.retry_tiles),
            ("Zurücksetzen", self.reset_project),
        ]
        for label, fn in actions:
            act = QAction(label, self)
            act.setProperty("i18n_source", label)
            act.triggered.connect(fn)
            tb.addAction(act)
            self._i18n_actions.append(act)
        self.language_label = QLabel("Sprache:")
        self.language_label.setProperty("i18n_source", "Sprache:")
        tb.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.addItem("DE", "de")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        tb.addWidget(self.language_combo)
        self.debug_checkbox = QCheckBox("Debugging aktivieren")
        self.debug_checkbox.setProperty("i18n_source", "Debugging aktivieren")
        self.debug_checkbox.setChecked(False)
        self.debug_checkbox.toggled.connect(self._debug_toggled)
        self.debug_action = tb.addWidget(self.debug_checkbox)
        self.debug_action.setVisible(not FROZEN)

    def _debug_toggled(self, checked: bool) -> None:
        global DEBUG_LOG_ENABLED
        DEBUG_LOG_ENABLED = bool(checked)
        if DEBUG_LOG_ENABLED:
            try:
                with _debug_log_path().open("a", encoding="utf-8") as fh:
                    fh.write(f"Debugging aktiviert für {APP_NAME} {APP_VERSION}\n\n")
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            self.statusBar().showMessage(f"Debug-Log: {_debug_log_path()}")

    def _build_controls(self) -> None:
        dock = QDockWidget("", self)
        dock.setObjectName("toolsDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget())
        dock.setMinimumWidth(500)
        dock.setMaximumWidth(760)
        root = QWidget()
        root.setObjectName("toolsRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.map_title_edit = None

        self.tools_box = QToolBox()
        self.tools_box.setObjectName("toolsBox")
        self.tools_box.setMinimumWidth(440)
        self.tools_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tools_box, 1)

        # Karten Ausschnitt / Orte
        search_page = QWidget()
        search_layout = QVBoxLayout(search_page)
        search_layout.setContentsMargins(8, 0, 8, 8)
        group = QGroupBox("")
        group.setObjectName("ohneTitel")
        form = QFormLayout(group)
        self.search_hint = QLabel("• Ort suchen oder Karte mit Maus bewegen.\n• Mausrad/Trackpad zoomt fein und stufenlos.\n• Rechtsklick in Karte wählt Auswahl ab.")
        self.search_hint.setProperty("hint", True)
        self.search_hint.setWordWrap(True)
        form.addRow(self.search_hint)
        self.place_search = QLineEdit()
        self.place_search.setPlaceholderText("Ort, Adresse oder Platz suchen")
        self.place_search.returnPressed.connect(self.search_place)
        form.addRow("Suche:", self.place_search)
        search_row = QHBoxLayout()
        search_btn = QPushButton("Suchen")
        search_btn.clicked.connect(self.search_place)
        search_row.addWidget(search_btn)
        form.addRow(search_row)
        self.search_result_combo = QComboBox()
        self.search_result_combo.currentIndexChanged.connect(self._search_result_changed)
        # Wählt der Nutzer ein Ergebnis im Klappmenü, springt die Karte direkt dorthin.
        self.search_result_combo.activated.connect(lambda _index=0: self.center_selected_search_result())
        form.addRow("Ergebnis:", self.search_result_combo)
        result_row = QHBoxLayout()
        center_btn = QPushButton("Zentrieren")
        center_btn.clicked.connect(self.center_selected_search_result)
        result_row.addWidget(center_btn)
        add_search_marker = QPushButton("Ergebnis als Punkt setzen")
        add_search_marker.clicked.connect(self.add_search_result_as_marker)
        result_row.addWidget(add_search_marker)
        form.addRow(result_row)
        self.search_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.search_zoom_slider.setRange(40, 380)
        self.search_zoom_slider.setSingleStep(1)
        self.search_zoom_slider.setPageStep(5)
        self.search_zoom_slider.setValue(int(round(float(self.canvas.zoom) * 20.0)))
        self.search_zoom_slider.valueChanged.connect(self._search_zoom_changed)
        form.addRow("Zoom:", self.search_zoom_slider)
        self.map_layer_combo = QComboBox()
        self.map_layer_combo.addItems(list(MAP_LAYERS.keys()))
        self.map_layer_combo.setCurrentText(self.canvas.map_layer)
        self.map_layer_combo.currentTextChanged.connect(self._map_layer_changed)
        form.addRow("Kartenebene:", self.map_layer_combo)
        mode_row = QHBoxLayout()
        self.map_mode_raster_btn = QPushButton("Raster")
        self.map_mode_raster_btn.setCheckable(True)
        self.map_mode_raster_btn.setChecked(True)
        self.map_mode_raster_btn.clicked.connect(lambda _=False: self._map_mode_chosen(False))
        mode_row.addWidget(self.map_mode_raster_btn)
        self.map_mode_vector_btn = QPushButton("Vektor")
        self.map_mode_vector_btn.setCheckable(True)
        self.map_mode_vector_btn.clicked.connect(lambda _=False: self._map_mode_chosen(True))
        mode_row.addWidget(self.map_mode_vector_btn)
        form.addRow("Kartenart:", mode_row)
        search_layout.addWidget(group)

        poi_group = QGroupBox("Kartennamen / Symbole")
        poi_layout = QVBoxLayout(poi_group)
        self.poi_filter_checkbox = QCheckBox("POI-Namen/Symbole filtern")
        self.poi_filter_checkbox.setChecked(False)
        self.poi_filter_checkbox.toggled.connect(self._poi_filter_toggled)
        poi_layout.addWidget(self.poi_filter_checkbox)

        self.poi_options_widget = QWidget()
        poi_options_layout = QVBoxLayout(self.poi_options_widget)
        poi_options_layout.setContentsMargins(14, 0, 0, 0)
        poi_options_layout.setSpacing(2)

        self.poi_names_checkbox = QCheckBox("Namen anzeigen")
        self.poi_names_checkbox.setChecked(True)
        self.poi_names_checkbox.toggled.connect(self._poi_names_toggled)
        poi_options_layout.addWidget(self.poi_names_checkbox)
        self.poi_icons_checkbox = QCheckBox("Symbole anzeigen")
        self.poi_icons_checkbox.setChecked(True)
        self.poi_icons_checkbox.toggled.connect(self._poi_icons_toggled)
        poi_options_layout.addWidget(self.poi_icons_checkbox)

        category_label = QLabel("Typen:")
        poi_options_layout.addWidget(category_label)
        self.poi_category_checkboxes = {}
        for category, label in POI_CATEGORY_LABELS.items():
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda checked, key=category: self._poi_category_toggled(key, checked))
            self.poi_category_checkboxes[category] = checkbox
            poi_options_layout.addWidget(checkbox)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("POIs ab Zoom:"))
        self.poi_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.poi_zoom_slider.setRange(int(POI_ZOOM_OFFSET_MIN * 2), int(POI_ZOOM_OFFSET_MAX * 2))
        self.poi_zoom_slider.setSingleStep(1)
        self.poi_zoom_slider.setPageStep(2)
        self.poi_zoom_slider.setValue(0)
        self.poi_zoom_slider.valueChanged.connect(self._poi_zoom_offset_changed)
        zoom_row.addWidget(self.poi_zoom_slider, 1)
        # Der Text wird erst nach dem Aufbau gesetzt, damit die Übersetzung ihn nicht festhält.
        self.poi_zoom_value_label = QLabel("")
        self.poi_zoom_value_label.setMinimumWidth(96)
        zoom_row.addWidget(self.poi_zoom_value_label)
        poi_options_layout.addLayout(zoom_row)

        poi_hint = QLabel("Filter betrifft nur Namen und Kartensymbole, keine Gebäudeflächen.")
        poi_hint.setWordWrap(True)
        poi_options_layout.addWidget(poi_hint)
        self.poi_options_widget.setVisible(False)
        poi_layout.addWidget(self.poi_options_widget)

        self.poi_status_label = QLabel("Der POI-Filter ist nur in der Vektor-Ansicht bedienbar.")
        self.poi_status_label.setWordWrap(True)
        poi_layout.addWidget(self.poi_status_label)
        search_layout.addWidget(poi_group)

        search_layout.addStretch(1)
        self.tools_box.addItem(search_page, "Karten Ausschnitt / Orte")

        # Titel
        title_page = QWidget()
        title_layout = QVBoxLayout(title_page)
        title_layout.setContentsMargins(8, 0, 8, 8)
        title_group = QGroupBox("")
        title_group.setObjectName("ohneTitel")
        title_form = QFormLayout(title_group)
        self.map_title_edit = QLineEdit("")
        self.map_title_edit.textChanged.connect(self._map_title_changed)
        title_form.addRow("Titel der Aktionskarte", self.map_title_edit)
        self.title_text_color = "#000000"
        self.title_text_color_btn = QPushButton("Textfarbe: #000000")
        self.title_text_color_btn.clicked.connect(self._choose_title_text_color)
        title_form.addRow("Textfarbe:", self.title_text_color_btn)
        self.title_bg_color = "#ffffff"
        self.title_bg_color_btn = QPushButton("Hintergrundfarbe: #ffffff")
        self.title_bg_color_btn.clicked.connect(self._choose_title_bg_color)
        title_form.addRow("Hintergrundfarbe:", self.title_bg_color_btn)
        self.title_alpha = QSlider(Qt.Orientation.Horizontal)
        self.title_alpha.setRange(0, 100)
        self.title_alpha.setValue(0)
        self.title_alpha.valueChanged.connect(self._title_alpha_changed)
        title_form.addRow("Hintergrund-Deckkraft:", self.title_alpha)
        title_layout.addWidget(title_group)
        title_layout.addStretch(1)
        self.tools_box.addItem(title_page, "Titel")

        # Größe / Gitter
        map_page = QWidget()
        map_layout = QVBoxLayout(map_page)
        map_layout.setContentsMargins(8, 0, 8, 8)
        group = QGroupBox("")
        group.setObjectName("ohneTitel")
        form = QFormLayout(group)
        self.paper_size_combo = QComboBox()
        self.paper_size_combo.addItems(PAGE_SIZE_ORDER)
        self.paper_size_combo.setCurrentText("A4")
        self.paper_size_combo.currentTextChanged.connect(self._paper_size_changed)
        form.addRow("Papiergröße:", self.paper_size_combo)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Querformat", "Hochformat"])
        self.orientation_combo.currentTextChanged.connect(self._orientation_changed)
        form.addRow("Format:", self.orientation_combo)
        self.border_width = QSlider(Qt.Orientation.Horizontal)
        self.border_width.setRange(10, 100)
        self.border_width.setValue(30)
        self.border_width.valueChanged.connect(self._border_changed)
        form.addRow("Randbreite:", self.border_width)
        self.density_combo = QComboBox()
        self.density_combo.addItems(["Locker", "Mittel", "Eng"])
        self.density_combo.currentIndexChanged.connect(lambda _=0: self.canvas.set_density(self._combo_source(self.density_combo)))
        form.addRow("Gitter:", self.density_combo)
        self.grid_box = QCheckBox("roten Rand anzeigen")
        self.grid_box.setChecked(True)
        self.grid_box.stateChanged.connect(self._grid_toggled)
        form.addRow(self.grid_box)
        self.grid_lines_box = QCheckBox("Gitterlinien anzeigen")
        self.grid_lines_box.setChecked(True)
        self.grid_lines_box.stateChanged.connect(self._grid_lines_toggled)
        form.addRow(self.grid_lines_box)
        self.scale_box = QCheckBox("Maßstab anzeigen")
        self.scale_box.stateChanged.connect(self._scale_toggled)
        form.addRow(self.scale_box)
        self.scale_pos_combo = QComboBox()
        self.scale_pos_combo.addItems(["Links oben", "Rechts oben", "Links unten", "Rechts unten"])
        self.scale_pos_combo.setCurrentText("Rechts unten")
        self.scale_pos_combo.currentTextChanged.connect(self._scale_position_changed)
        form.addRow("Maßstab Position:", self.scale_pos_combo)
        self.scale_length = QSpinBox(); self.scale_length.setRange(10, 100000); self.scale_length.setValue(1000); self.scale_length.setSingleStep(100)
        self.scale_length.valueChanged.connect(self._scale_length_changed)
        form.addRow("Maßstab Länge m:", self.scale_length)
        self.scale_opacity = QSlider(Qt.Orientation.Horizontal)
        self.scale_opacity.setRange(0, 100)
        self.scale_opacity.setValue(100)
        self.scale_opacity.valueChanged.connect(self._scale_opacity_changed)
        form.addRow("Maßstab Deckkraft:", self.scale_opacity)
        map_layout.addWidget(group)
        map_layout.addStretch(1)
        self.tools_box.addItem(map_page, "Größe / Gitter")

        # Symbol-Punkte
        points_page = QWidget()
        points_layout = QVBoxLayout(points_page)
        points_layout.setContentsMargins(8, 0, 8, 8)

        group = QGroupBox("Neuer Symbol-Punkt")
        form = QFormLayout(group)
        self.point_mode_label = QLabel("• Klick in die Karte setzt einen Symbol-Punkt.\n• Bestehende Punkte können ausgewählt und bearbeitet werden.\n• Im Routenmodus sind Symbole nicht klickbar.\n• Rechtsklick in Karte wählt Auswahl ab.")
        self.point_mode_label.setProperty("hint", True)
        self.point_mode_label.setWordWrap(True)
        form.addRow(self.point_mode_label)
        points_layout.addWidget(group)

        color_grid = QGridLayout()
        self.color_buttons: Dict[str, QPushButton] = {}
        for i, color in enumerate(COLORS):
            b = QPushButton()
            b.setFixedSize(32, 32)
            b.setMinimumSize(32, 32)
            b.setMaximumSize(32, 32)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            b.setFlat(True)
            b.setStyleSheet(f"background:{color}; border: 2px solid #333; border-radius: 0px; padding: 0px; min-width: 32px; min-height: 32px; max-width: 32px; max-height: 32px;")
            b.clicked.connect(lambda _=False, c=color: self._choose_color(c))
            self.color_buttons[color] = b
            color_grid.addWidget(b, i // 6, i % 6)
        custom = QPushButton("andere Farbe...")
        custom.clicked.connect(self._choose_custom_color)

        group = QGroupBox("Symbole")
        v = QVBoxLayout(group)
        sym_grid = QGridLayout()
        self.symbol_buttons: Dict[str, QPushButton] = {}
        for i, (key, item) in enumerate(ICON_DATA.items()):
            b = QPushButton()
            b.setToolTip(item["label"])
            b.setFixedSize(38, 38)
            b.setIcon(QIcon(self.icons.pixmap(key, self.canvas.current_color)))
            b.setIconSize(QSize(30, 30))
            b.clicked.connect(lambda _=False, k=key: self._choose_symbol(k))
            self.symbol_buttons[key] = b
            sym_grid.addWidget(b, i // 7, i % 7)
        v.addLayout(sym_grid)
        v.addLayout(color_grid)
        v.addWidget(custom)
        points_layout.addWidget(group)

        group = QGroupBox("Ausgewählter Punkt")
        form = QFormLayout(group)
        self.sel_info = QLabel("kein Punkt ausgewählt")
        self.sel_info.setWordWrap(True)
        form.addRow(self.sel_info)
        self.marker_combo = QComboBox()
        self.marker_combo.currentIndexChanged.connect(self._marker_combo_changed)
        form.addRow("Bestehende Punkte:", self.marker_combo)
        self.marker_label = QLineEdit()
        self.marker_label.setVisible(False)
        self.marker_desc = QTextEdit()
        self.marker_desc.setFixedHeight(70)
        form.addRow("Text:", self.marker_desc)
        self.label_pos_combo = QComboBox()
        self.label_pos_combo.addItems(["Rechts", "Links", "Oben", "Unten"])
        form.addRow("Textposition:", self.label_pos_combo)
        self.label_w = QSpinBox(); self.label_w.setRange(40, 500); self.label_w.setValue(150); self.label_w.setVisible(False)
        self.label_h = QSpinBox(); self.label_h.setRange(24, 260); self.label_h.setValue(54); self.label_h.setVisible(False)
        self.label_gap = QSlider(Qt.Orientation.Horizontal); self.label_gap.setRange(0, 100); self.label_gap.setValue(4)
        form.addRow("Abstand:", self.label_gap)
        self.label_font = QSpinBox(); self.label_font.setRange(6, 36); self.label_font.setValue(12)
        form.addRow("Schriftgröße:", self.label_font)
        self.label_alpha = QSlider(Qt.Orientation.Horizontal)
        self.label_alpha.setRange(0, 100)
        self.label_alpha.setValue(100)
        form.addRow("Box-Deckkraft:", self.label_alpha)
        self.marker_text_color = "#000000"
        self.marker_text_color_btn = QPushButton("Textfarbe: #000000")
        self.marker_text_color_btn.clicked.connect(self._choose_marker_text_color)
        form.addRow("Textfarbe:", self.marker_text_color_btn)
        marker_style_row = QHBoxLayout()
        self.marker_bold = QCheckBox("Fett")
        self.marker_italic = QCheckBox("Kursiv")
        self.marker_underline = QCheckBox("Unterstrichen")
        for _w in (self.marker_desc, self.label_pos_combo, self.label_gap, self.label_font, self.label_alpha, self.marker_bold, self.marker_italic, self.marker_underline):
            try:
                signal = _w.textChanged if hasattr(_w, "textChanged") else (_w.currentIndexChanged if hasattr(_w, "currentIndexChanged") else (_w.valueChanged if hasattr(_w, "valueChanged") else _w.stateChanged))
                signal.connect(self._live_update_marker)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        marker_style_row.addWidget(self.marker_bold)
        marker_style_row.addWidget(self.marker_italic)
        marker_style_row.addWidget(self.marker_underline)
        form.addRow("Stil:", marker_style_row)
        self.icon_size = QSlider(Qt.Orientation.Horizontal)
        self.icon_size.setRange(17, 161)
        self.icon_size.setValue(52)
        self.icon_size.valueChanged.connect(self._live_update_marker)
        form.addRow("Symbolgröße:", self.icon_size)
        row = QHBoxLayout()
        apply_btn = QPushButton("Symbol aktualisieren")
        apply_btn.clicked.connect(self.apply_marker_values)
        del_btn = QPushButton("Punkt löschen")
        del_btn.clicked.connect(self.canvas.delete_selected_marker)
        row.addWidget(apply_btn); row.addWidget(del_btn)
        form.addRow(row)
        points_layout.addWidget(group)
        points_layout.addStretch(1)
        self.tools_box.addItem(points_page, "Symbol-Punkte")

        # Routen
        route_page = QWidget()
        route_layout = QVBoxLayout(route_page)
        route_layout.setContentsMargins(8, 0, 8, 8)
        group = QGroupBox("")
        group.setObjectName("ohneTitel")
        form = QFormLayout(group)
        self.route_mode_label = QLabel("• Klick in die Karte setzt Routenpunkte.\n• Route berechnen erstellt Pfad.\n• Ohne Berechnung speichert die Klicklinie.\n• Rechtsklick in Karte wählt Auswahl ab.")
        self.route_mode_label.setProperty("hint", True)
        self.route_mode_label.setWordWrap(True)
        form.addRow(self.route_mode_label)
        self.route_combo = QComboBox()
        self.route_combo.currentIndexChanged.connect(self._route_combo_changed)
        form.addRow("Bestehende Routen:", self.route_combo)
        self.route_profile_combo = QComboBox()
        self.route_profile_combo.addItems(["Fuß-Route", "Fahrrad-Route", "PKW-Route"])
        self.route_profile_combo.setCurrentText("Fuß-Route")
        self.route_profile_combo.currentIndexChanged.connect(self._route_profile_changed)
        form.addRow("Berechnungsart:", self.route_profile_combo)
        self.route_name = QLineEdit()
        self.route_name.setPlaceholderText("z. B. Route 1")
        self.route_name.textChanged.connect(self._live_update_route)
        form.addRow("Name:", self.route_name)
        self.route_color = "#ff0505"
        self.route_color_btn = QPushButton("Farbe: #ff0505")
        self.route_color_btn.setStyleSheet("background:#ff0505;color:#000;")
        self.route_color_btn.clicked.connect(self._choose_route_color)
        form.addRow("Linie:", self.route_color_btn)
        self.route_width = QSpinBox(); self.route_width.setRange(1, 30); self.route_width.setValue(6)
        self.route_width.valueChanged.connect(self._route_width_changed)
        form.addRow("Breite:", self.route_width)
        self.route_opacity = QSlider(Qt.Orientation.Horizontal)
        self.route_opacity.setRange(0, 100)
        self.route_opacity.setValue(80)
        self.route_opacity.valueChanged.connect(self._route_opacity_changed)
        form.addRow("Deckkraft:", self.route_opacity)
        row = QHBoxLayout()
        save_route = QPushButton("Ohne Berechnung speichern")
        save_route.clicked.connect(self.save_clicked_route)
        undo_route = QPushButton("Punkt zurück")
        undo_route.clicked.connect(self.canvas.remove_last_route_point)
        row.addWidget(save_route); row.addWidget(undo_route)
        form.addRow(row)
        row2 = QHBoxLayout()
        calc_route = QPushButton("Route berechnen")
        calc_route.clicked.connect(self.calculate_route_from_clicks)
        del_selected_route = QPushButton("Ausgewählte Route löschen")
        del_selected_route.clicked.connect(self.canvas.delete_selected_route)
        row2.addWidget(calc_route); row2.addWidget(del_selected_route)
        form.addRow(row2)
        row3 = QHBoxLayout()
        edit_route = QPushButton("Route bearbeiten")
        edit_route.clicked.connect(self.edit_selected_route_as_points)
        clear_routes = QPushButton("Alle Routen löschen")
        clear_routes.clicked.connect(self.canvas.clear_routes)
        row3.addWidget(edit_route); row3.addWidget(clear_routes)
        form.addRow(row3)
        self.route_directions = QTextEdit()
        self.route_directions.setReadOnly(True)
        self.route_directions.setMinimumHeight(150)
        self.route_directions.setPlaceholderText("Nach Route berechnen steht hier die kopierbare Wegbeschreibung mit Länge und Dauer.")
        form.addRow("Wegbeschreibung:", self.route_directions)
        copy_directions = QPushButton("Kopieren")
        copy_directions.clicked.connect(self._copy_route_directions)
        form.addRow(copy_directions)
        route_layout.addWidget(group)
        route_layout.addStretch(1)
        self.tools_box.addItem(route_page, "Routen")

        # Zonen
        zone_page = QWidget()
        zone_layout = QVBoxLayout(zone_page)
        zone_layout.setContentsMargins(8, 0, 8, 8)
        zone_group = QGroupBox("")
        zone_group.setObjectName("ohneTitel")
        zone_form = QFormLayout(zone_group)
        self.zone_mode_label = QLabel("• Klick in die Karte setzt Eckpunkte einer Zone.\n• Mindestens drei Punkte speichern eine Fläche.\n• Rechtsklick in Karte wählt Auswahl ab.")
        self.zone_mode_label.setProperty("hint", True)
        self.zone_mode_label.setWordWrap(True)
        zone_form.addRow(self.zone_mode_label)
        self.zone_combo = QComboBox()
        self.zone_combo.currentIndexChanged.connect(self._zone_combo_changed)
        zone_form.addRow("Bestehende Zonen:", self.zone_combo)
        self.zone_name = QLineEdit()
        self.zone_name.setPlaceholderText("Zone")
        zone_form.addRow("Name:", self.zone_name)
        self.zone_label = QTextEdit()
        self.zone_label.setFixedHeight(60)
        self.zone_label.textChanged.connect(self._live_update_zone)
        zone_form.addRow("Text:", self.zone_label)
        self.zone_label_pos = QComboBox()
        self.zone_label_pos.addItems(["Mitte", "Rechts", "Links", "Oben", "Unten"])
        self.zone_label_pos.currentIndexChanged.connect(self._live_update_zone)
        zone_form.addRow("Beschriftung Position:", self.zone_label_pos)
        self.zone_fill_color = "#ff0505"
        self.zone_fill_btn = QPushButton("Füllfarbe: #ff0505")
        self.zone_fill_btn.clicked.connect(self._choose_zone_fill_color)
        zone_form.addRow("Füllfarbe", self.zone_fill_btn)
        self.zone_alpha = QSlider(Qt.Orientation.Horizontal)
        self.zone_alpha.setRange(0, 100)
        self.zone_alpha.setValue(28)
        self.zone_alpha.valueChanged.connect(self._live_update_zone)
        zone_form.addRow("Deckkraft:", self.zone_alpha)
        self.zone_border_color = "#ff0505"
        self.zone_border_btn = QPushButton("Konturfarbe: #ff0505")
        self.zone_border_btn.clicked.connect(self._choose_zone_border_color)
        zone_form.addRow("Konturfarbe", self.zone_border_btn)
        self.zone_border_width = QSpinBox(); self.zone_border_width.setRange(1, 50); self.zone_border_width.setValue(4)
        self.zone_border_width.valueChanged.connect(self._live_update_zone)
        zone_form.addRow("Konturbreite:", self.zone_border_width)
        self.zone_font = QSpinBox(); self.zone_font.setRange(6, 36); self.zone_font.setValue(13)
        self.zone_font.valueChanged.connect(self._live_update_zone)
        zone_form.addRow("Schriftgröße:", self.zone_font)
        self.zone_text_color = "#000000"
        self.zone_text_color_btn = QPushButton("Textfarbe: #000000")
        self.zone_text_color_btn.clicked.connect(self._choose_zone_text_color)
        zone_form.addRow("Textfarbe:", self.zone_text_color_btn)
        self.zone_label_bg_color = "#ffffff"
        self.zone_label_bg_btn = QPushButton("Hintergrundfarbe: #ffffff")
        self.zone_label_bg_btn.clicked.connect(self._choose_zone_label_bg_color)
        zone_form.addRow("Texthintergrund:", self.zone_label_bg_btn)
        self.zone_label_bg_alpha = QSlider(Qt.Orientation.Horizontal)
        self.zone_label_bg_alpha.setRange(0, 100)
        self.zone_label_bg_alpha.setValue(70)
        self.zone_label_bg_alpha.valueChanged.connect(self._live_update_zone)
        zone_form.addRow("Text-Hintergrund Deckkraft:", self.zone_label_bg_alpha)
        zone_style_row = QHBoxLayout()
        self.zone_bold = QCheckBox("Fett")
        self.zone_italic = QCheckBox("Kursiv")
        self.zone_underline = QCheckBox("Unterstrichen")
        for _w in (self.zone_bold, self.zone_italic, self.zone_underline):
            _w.stateChanged.connect(self._live_update_zone)
            zone_style_row.addWidget(_w)
        zone_form.addRow("Stil:", zone_style_row)
        zone_buttons = QHBoxLayout()
        save_zone = QPushButton("Zone speichern")
        save_zone.clicked.connect(self.save_zone_from_clicks)
        undo_zone = QPushButton("Punkt zurück")
        undo_zone.clicked.connect(self.canvas.remove_last_zone_point)
        zone_buttons.addWidget(save_zone); zone_buttons.addWidget(undo_zone)
        zone_form.addRow(zone_buttons)
        zone_buttons2 = QHBoxLayout()
        update_zone = QPushButton("Zone aktualisieren")
        update_zone.clicked.connect(self.apply_zone_values)
        del_zone = QPushButton("Zone löschen")
        del_zone.clicked.connect(self.canvas.delete_selected_zone)
        zone_buttons2.addWidget(update_zone); zone_buttons2.addWidget(del_zone)
        zone_form.addRow(zone_buttons2)
        zone_layout.addWidget(zone_group)
        zone_layout.addStretch(1)
        self.tools_box.addItem(zone_page, "Zonen")

        # Bilddatei
        logo_page = QWidget()
        logo_layout = QVBoxLayout(logo_page)
        logo_layout.setContentsMargins(8, 0, 8, 8)
        group = QGroupBox("")
        group.setObjectName("ohneTitel")
        form = QFormLayout(group)
        self.logo_hint_top = QLabel("• JPG oder PNG hochladen.\n• Bilddatei kann verschoben und skaliert werden.\n• Rechtsklick in Karte wählt Auswahl ab.")
        self.logo_hint_top.setProperty("hint", True)
        self.logo_hint_top.setWordWrap(True)
        form.addRow(self.logo_hint_top)
        self.logo_info = QLabel("")
        self.logo_info.setVisible(False)
        self.logo_combo = QComboBox()
        self.logo_combo.currentIndexChanged.connect(self._logo_combo_changed)
        form.addRow("Bestehende Bilddateien:", self.logo_combo)
        upload_logo = QPushButton("Bilddatei hochladen…")
        upload_logo.clicked.connect(self.upload_logo)
        form.addRow(upload_logo)
        self.logo_width = QSpinBox(); self.logo_width.setRange(20, 900); self.logo_width.setValue(180)
        self.logo_width.valueChanged.connect(self._logo_width_changed)
        form.addRow("Breite:", self.logo_width)
        self.logo_height = QSpinBox(); self.logo_height.setRange(20, 900); self.logo_height.setValue(90)
        self.logo_height.valueChanged.connect(self._logo_height_changed)
        form.addRow("Höhe:", self.logo_height)
        del_logo = QPushButton("Bilddatei löschen")
        del_logo.clicked.connect(self.canvas.delete_selected_logo)
        form.addRow(del_logo)
        logo_layout.addWidget(group)
        logo_layout.addStretch(1)
        self.tools_box.addItem(logo_page, "Bilddatei")

        # Legende
        legend_page = QWidget()
        legend_layout = QVBoxLayout(legend_page)
        legend_layout.setContentsMargins(8, 0, 8, 8)
        group = QGroupBox("")
        group.setObjectName("ohneTitel")
        form = QFormLayout(group)
        self.legend_mode_label = QLabel("• Text eingeben und frei formatieren.\n• Markierte Wörter können Fett/Kursiv/Unterstrichen und farbig werden.\n• Symbole können in den Text eingefügt werden.\n• Rechtsklick in Karte wählt Auswahl ab.")
        self.legend_mode_label.setProperty("hint", True)
        self.legend_mode_label.setWordWrap(True)
        form.addRow(self.legend_mode_label)
        self.note_combo = QComboBox()
        self.note_combo.currentIndexChanged.connect(self._note_combo_changed)
        form.addRow("Bestehende Textfelder:", self.note_combo)
        new_note_btn = QPushButton("Neues Textfeld")
        new_note_btn.clicked.connect(self.new_note)
        form.addRow(new_note_btn)
        self.note_name = QLineEdit()
        self.note_name.setPlaceholderText("z. B. Textfeld 1")
        self.note_name.textChanged.connect(self._live_update_note)
        form.addRow("Name:", self.note_name)
        self.note_pos = QComboBox()
        self.note_pos.addItems(["Rechts oben", "Rechts unten", "Links oben", "Links unten", "Zentriert"])
        self.note_pos.currentIndexChanged.connect(self._live_update_note)
        form.addRow("Position:", self.note_pos)
        self.note_visible = QCheckBox("Textfeld anzeigen")
        self.note_visible.setChecked(False)
        self.note_visible.stateChanged.connect(self._note_visible_changed)
        form.addRow(self.note_visible)
        self.note_text = QTextEdit()
        self.note_text.setAcceptRichText(True)
        self.note_text.setPlainText("Textfeld / Legende")
        self.note_text.setFixedHeight(120)
        self.note_text.setStyleSheet("background:#ffffff;color:#000000;border:1px solid #444;padding:6px;")
        self.note_text.setTextColor(QColor("#000000"))
        self.note_text.selectionChanged.connect(self._remember_note_selection)
        self.note_text.textChanged.connect(self._live_update_note)
        text_style_row = QHBoxLayout()
        self.note_sel_bold = QPushButton("Fett")
        self.note_sel_bold.setCheckable(True)
        self.note_sel_bold.clicked.connect(lambda checked: self._format_note_selection("bold", checked))
        self.note_sel_italic = QPushButton("Kursiv")
        self.note_sel_italic.setCheckable(True)
        self.note_sel_italic.clicked.connect(lambda checked: self._format_note_selection("italic", checked))
        self.note_sel_underline = QPushButton("Unterstrichen")
        self.note_sel_underline.setCheckable(True)
        self.note_sel_underline.clicked.connect(lambda checked: self._format_note_selection("underline", checked))
        text_style_row.addWidget(self.note_sel_bold)
        text_style_row.addWidget(self.note_sel_italic)
        text_style_row.addWidget(self.note_sel_underline)
        form.addRow("Textstil Auswahl:", text_style_row)
        self.note_selection_color_btn = QPushButton("Textfarbe Auswahl")
        self.note_selection_color_btn.clicked.connect(self._choose_note_selection_color)
        form.addRow("Farbe für Auswahl:", self.note_selection_color_btn)
        legend_symbol_row = QHBoxLayout()
        self.note_symbol_combo = QComboBox()
        for _key, _item in ICON_DATA.items():
            self.note_symbol_combo.addItem(_item.get("label", _key), _key)
        self.note_symbol_color = self.canvas.current_color
        self.note_selection_color = getattr(self, "note_text_color", "#000000")
        self.note_symbol_color_buttons: Dict[str, QPushButton] = {}
        note_symbol_color_grid = QGridLayout()
        for _i, _color in enumerate(COLORS):
            _b = QPushButton()
            _b.setFixedSize(32, 32)
            _b.setMinimumSize(32, 32)
            _b.setMaximumSize(32, 32)
            _b.setFlat(False)
            _b.clicked.connect(lambda _=False, c=_color: self._choose_note_symbol_color(c))
            self.note_symbol_color_buttons[_color] = _b
            note_symbol_color_grid.addWidget(_b, _i // 6, _i % 6)
        self.note_symbol_custom_color_btn = QPushButton("+")
        self.note_symbol_custom_color_btn.setFixedSize(32, 32)
        self.note_symbol_custom_color_btn.setMinimumSize(32, 32)
        self.note_symbol_custom_color_btn.setMaximumSize(32, 32)
        self.note_symbol_custom_color_btn.clicked.connect(self._choose_custom_note_symbol_color)
        note_symbol_color_grid.addWidget(self.note_symbol_custom_color_btn, len(COLORS) // 6, len(COLORS) % 6)
        form.addRow("Symbolfarbe:", note_symbol_color_grid)
        insert_symbol_btn = QPushButton("Symbol einfügen")
        insert_symbol_btn.clicked.connect(self._insert_note_symbol)
        legend_symbol_row.addWidget(self.note_symbol_combo, 1)
        legend_symbol_row.addWidget(insert_symbol_btn)
        form.addRow("Symbol im Text:", legend_symbol_row)
        form.addRow("Text:", self.note_text)
        self.note_align = QComboBox()
        self.note_align.addItems(["Links", "Zentriert", "Rechts"])
        self.note_align.currentIndexChanged.connect(self._live_update_note)
        form.addRow("Textausrichtung:", self.note_align)
        self.note_color = "#ffffff"
        self.note_color_btn = QPushButton("Füllfarbe: #ffffff")
        self.note_color_btn.clicked.connect(self._choose_note_color)
        form.addRow("Füllfarbe:", self.note_color_btn)
        self.note_text_color = "#000000"
        self.note_text_color_btn = QPushButton("Textfarbe: #000000")
        self.note_text_color_btn.clicked.connect(self._choose_note_text_color)
        form.addRow("Textfarbe:", self.note_text_color_btn)
        self.note_alpha = QSlider(Qt.Orientation.Horizontal)
        self.note_alpha.setRange(0, 100)
        self.note_alpha.setValue(100)
        self.note_alpha.valueChanged.connect(self._live_update_note)
        form.addRow("Deckkraft:", self.note_alpha)
        self.note_include_routes = QCheckBox("Routen Legende hinzufügen")
        self.note_include_routes.stateChanged.connect(self._note_include_routes_changed)
        form.addRow(self.note_include_routes)
        self.note_w = QSpinBox(); self.note_w.setRange(80, 700); self.note_w.setValue(230); self.note_w.setVisible(False)
        self.note_h = QSpinBox(); self.note_h.setRange(40, 500); self.note_h.setValue(110); self.note_h.setVisible(False)
        self.note_font = QSpinBox(); self.note_font.setRange(6, 61); self.note_font.setValue(13)
        self.note_font.valueChanged.connect(self._note_font_changed)
        form.addRow("Schriftgröße:", self.note_font)
        self.note_bold = QCheckBox("alles Fett"); self.note_bold.setVisible(False)
        self.note_italic = QCheckBox("alles Kursiv"); self.note_italic.setVisible(False)
        self.note_underline = QCheckBox("alles Unterstrichen"); self.note_underline.setVisible(False)
        row = QHBoxLayout()
        add_note = QPushButton("Feld aktualisieren")
        add_note.clicked.connect(self.add_or_update_note)
        del_note = QPushButton("Textfeld löschen")
        del_note.clicked.connect(self.canvas.delete_selected_note)
        row.addWidget(add_note); row.addWidget(del_note)
        form.addRow(row)
        legend_layout.addWidget(group)
        legend_layout.addStretch(1)
        self.tools_box.addItem(legend_page, "Legende / Textfeld")

        # Anleitung
        manual_page = QWidget()
        manual_layout = QVBoxLayout(manual_page)
        manual_layout.setContentsMargins(8, 0, 8, 8)
        self.manual_text = QTextEdit()
        self.manual_text.setReadOnly(True)
        self.manual_text.setPlainText(self._manual_text_for_lang("de"))
        manual_layout.addWidget(self.manual_text)
        self.tools_box.addItem(manual_page, "Anleitung")

        for _hint in [getattr(self, name, None) for name in ("search_hint", "point_mode_label", "route_mode_label", "zone_mode_label", "logo_hint_top", "legend_mode_label")]:
            if _hint is not None:
                _hint.setStyleSheet("font-size: 12px; font-weight: bold; margin: 0px; padding: 0px;")
        dock.setWidget(root)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.tools_box.currentChanged.connect(self._toolbox_changed)
        self.tools_box.setCurrentIndex(0)
        self._register_i18n_tree(root)
        self._apply_language()
        self._toolbox_changed(self.tools_box.currentIndex())
        self._refresh_symbol_button_styles()
        self._refresh_color_button_styles()

    # ---------- language ----------
    def _tr(self, text: str) -> str:
        return tr_text(text, self._current_lang())

    def _current_lang(self) -> str:
        if hasattr(self, "language_combo"):
            data = self.language_combo.currentData()
            if data in ("de", "en"):
                return data
        return "de"

    def _register_i18n_tree(self, root: QWidget) -> None:
        self._i18n_widgets = getattr(self, "_i18n_widgets", [])
        widgets = [root] + root.findChildren(QWidget)
        for w in widgets:
            try:
                if hasattr(w, "text") and hasattr(w, "setText"):
                    txt = w.text()
                    if txt and not w.property("i18n_source"):
                        w.setProperty("i18n_source", txt)
                        self._i18n_widgets.append(w)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            try:
                if hasattr(w, "title") and hasattr(w, "setTitle"):
                    title = w.title()
                    if title and not w.property("i18n_title_source"):
                        w.setProperty("i18n_title_source", title)
                        self._i18n_widgets.append(w)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            try:
                if isinstance(w, QLineEdit):
                    ph = w.placeholderText()
                    if ph and not w.property("i18n_placeholder_source"):
                        w.setProperty("i18n_placeholder_source", ph)
                        self._i18n_widgets.append(w)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            try:
                if isinstance(w, QComboBox) and w is not getattr(self, "language_combo", None):
                    for i in range(w.count()):
                        if w.itemData(i, Qt.ItemDataRole.UserRole + 100) is None:
                            w.setItemData(i, w.itemText(i), Qt.ItemDataRole.UserRole + 100)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        if hasattr(self, "tools_box"):
            # QToolBox has no itemData/setItemData methods in PySide6.
            # Store the untranslated page titles on the contained page widgets instead.
            for i in range(self.tools_box.count()):
                page = self.tools_box.widget(i)
                if page is not None and not page.property("toolbox_i18n_source"):
                    page.setProperty("toolbox_i18n_source", self.tools_box.itemText(i))


    def _color_label(self, label_source: str, color: str) -> str:
        return f"{tr_text(label_source, self._current_lang())} {color}"

    def _set_color_button_text(self, button: QPushButton, label_source: str, color: str) -> None:
        try:
            button.setText(self._color_label(label_source, color))
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def _button_text_color_for_bg(self, color: str) -> str:
        q = QColor(color)
        if not q.isValid():
            return "#ffffff"
        return "#000000" if q.lightness() > 150 else "#ffffff"

    def _style_color_button(self, button: QPushButton, color: str) -> None:
        try:
            q = QColor(color)
            if not q.isValid():
                color = "#777777"
            button.setStyleSheet(f"background:{color}; color:{self._button_text_color_for_bg(color)}; border:1px solid #555;")
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def _set_named_color_button(self, button: QPushButton, label_source: str, color: str) -> None:
        self._set_color_button_text(button, label_source, color)
        self._style_color_button(button, color)

    def _refresh_dynamic_labels(self) -> None:
        if hasattr(self, "title_bg_color_btn"):
            self._set_named_color_button(self.title_bg_color_btn, "Hintergrundfarbe:", self.title_bg_color)
        if hasattr(self, "title_text_color_btn"):
            self._set_named_color_button(self.title_text_color_btn, "Textfarbe:", self.title_text_color)
        if hasattr(self, "marker_text_color_btn"):
            self._set_named_color_button(self.marker_text_color_btn, "Textfarbe:", self.marker_text_color)
        if hasattr(self, "route_color_btn"):
            self._set_named_color_button(self.route_color_btn, "Farbe:", self.route_color)
        if hasattr(self, "zone_fill_btn"):
            self._set_named_color_button(self.zone_fill_btn, "Füllfarbe:", self.zone_fill_color)
        if hasattr(self, "zone_border_btn"):
            self._set_named_color_button(self.zone_border_btn, "Konturfarbe:", self.zone_border_color)
        if hasattr(self, "zone_text_color_btn"):
            self._set_named_color_button(self.zone_text_color_btn, "Textfarbe:", self.zone_text_color)
        if hasattr(self, "zone_label_bg_btn"):
            self._set_named_color_button(self.zone_label_bg_btn, "Hintergrundfarbe:", self.zone_label_bg_color)
        if hasattr(self, "note_color_btn"):
            self._set_named_color_button(self.note_color_btn, "Füllfarbe:", self.note_color)
        if hasattr(self, "note_text_color_btn"):
            self._set_named_color_button(self.note_text_color_btn, "Textfarbe:", self.note_text_color)
        if hasattr(self, "note_selection_color_btn"):
            self._set_named_color_button(self.note_selection_color_btn, "Farbe für Auswahl:", getattr(self, "note_selection_color", self.note_text_color))
        if hasattr(self, "note_symbol_color_buttons"):
            self._refresh_note_symbol_color_button_styles()

    def _manual_text_for_lang(self, lang: str) -> str:
        if lang == "en":
            return (
                "Map view / places\n"
                "• Search for places, addresses or squares.\n"
                "• Selecting a result in the drop-down jumps the map straight to it. Center repeats the jump; the result can also be added as a symbol point.\n"
                "• Zoom smoothly with the slider, mouse wheel or trackpad.\n"
                "• Select the map layer/map style in this tab.\n"
                "• Map type: choose Raster (map tiles) or Vector (MapLibre). The choice is saved with the project.\n"
                "• A new project starts in Vector with the map layer Bicycle and the POI filter switched on.\n"
                "• Each map type keeps its own map layer: Vector starts with Bicycle, Raster with Standard.\n"
                "• Map names/symbols: in the vector view, POI names and map symbols can be shown or hidden by type. The slider POIs from zoom shows them earlier or later. Map layers without POIs disable the filter.\n\n"
                "Title\n"
                "• Add a title to the map. Empty title field means no title is drawn.\n"
                "• Text color, background color and background opacity can be set.\n\n"
                "Size / grid\n"
                "• Choose A3, A4 or A5 and portrait or landscape.\n"
                "• Set border width, grid density and optional scale bar.\n"
                "• Reload map requests missing or broken map tiles again; in the vector view it reloads the vector map.\n\n"
                "Symbol points\n"
                "• Open this tab and click the map to place a symbol point.\n"
                "• Select existing points from the list or by clicking them on the map.\n"
                "• Text, symbol, color, size, text position and text box opacity can be edited.\n"
                "• Ctrl+click adds points to the selection; changes are applied to all selected points.\n"
                "• Right-click the map to clear selection.\n\n"
                "Routes\n"
                "• Click the map to add route points. The first point is visible immediately.\n"
                "• Choose the calculation type (walking, bicycle or car); Calculate route creates the matching path.\n"
                "• Without calculation saves the clicked line directly.\n"
                "• Existing routes can be selected, renamed, recolored or deleted.\n"
                "• Copy below the directions puts the text on the clipboard.\n"
                "• Select a calculated route and change the calculation type: the route is recalculated in place.\n"
                "• Right-click the map to clear selection.\n\n"
                "Zones\n"
                "• Click several corner points on the map, then save the zone.\n"
                "• Fill color, fill opacity, outline color, outline width and label style can be adjusted.\n"
                "• Zone labels can be placed in the middle of the zone.\n"
                "• Right-click the map to clear selection.\n\n"
                "Image file\n"
                "• Upload JPG or PNG images.\n"
                "• Images can be moved freely and scaled with width and height.\n"
                "• Existing image files can be selected from the list and deleted.\n"
                "• Right-click the map to clear selection.\n\n"
                "Legend / text box\n"
                "• Show the text box with the checkbox and hide it again when needed.\n"
                "• Text can be formatted with bold, italic, underline, colors and inserted symbols.\n"
                "• Existing text boxes can be selected in the list and given a name. Another text box is only added with New text box.\n"
                "• Position Centered places the text box in the middle of the map, horizontally and vertically.\n"
                "• Add routes legend adds the routes automatically in their route color.\n"
                "• Position, alignment, background color and opacity can be adjusted.\n\n"
                "Privacy / network\n"
                "• Online services used: place search nominatim.openstreetmap.org; raster tiles tile.openstreetmap.org (Standard), tile-cyclosm.openstreetmap.fr (Bicycle), tile.openstreetmap.fr (Humanitarian); route calculation routing.openstreetmap.de, fallback router.project-osrm.org; vector view tiles.openfreemap.org.\n"
                "• Sent to them: the search text, the map areas you look at, and start, destination and intermediate points of routes. As with any request they also see your IP address; search, raster tiles and routing also get the system language, the vector view the usual browser identification (operating system, Chromium version).\n"
                "• The program starts in the vector view, so the vector map service is contacted from program start. It is only contacted while the vector view is selected. MapLibre itself is loaded from local files.\n"
                "• The tile cache is automatically cleared when the program closes and when it starts.\n"
                "• Enable debugging only when needed; it writes a text log into the program folder.\n\n"
                "Shortcuts\n"
                "• Ctrl+Z undo, Ctrl+Y redo. This covers content only (points, texts, images, routes, zones, title); the map view and the settings stay as they are.\n"
                "• Ctrl+A selects all elements in the current tab.\n"
                "• Ctrl+click adds elements to a multi-selection.\n"
                "• Before export every selection is cleared automatically."
            )
        return (
            "Karten Ausschnitt / Orte\n"
            "• Orte, Adressen oder Plätze suchen.\n"
            "• Ergebnis im Klappmenü wählen: die Karte springt direkt dorthin. Zentrieren wiederholt den Sprung; das Ergebnis lässt sich auch als Symbol-Punkt setzen.\n"
            "• Stufenlos über Schieberegler, Mausrad oder Trackpad zoomen.\n"
            "• Kartenebene/Kartenstil in diesem Reiter auswählen.\n"
            "• Kartenart: Raster (Kartenkacheln) oder Vektor (MapLibre) wählen. Die Wahl wird im Projekt gespeichert.\n"
            "• Ein neues Projekt startet in Vektor mit der Kartenebene Fahrrad und eingeschaltetem POI-Filter.\n"
            "• Jede Kartenart merkt sich ihre eigene Kartenebene: Vektor beginnt mit Fahrrad, Raster mit Standard.\n"
            "• Kartennamen/Symbole: in der Vektor-Ansicht POI-Namen und Kartensymbole nach Typ ein-/ausblenden. Der Regler „POIs ab Zoom“ blendet sie früher oder später ein. Bei Kartenebenen ohne POIs ist der Filter gesperrt.\n\n"
            "Titel\n"
            "• Titel für die Karte setzen. Ein leeres Titelfeld wird nicht gezeichnet.\n"
            "• Textfarbe, Hintergrundfarbe und Hintergrund-Deckkraft sind einstellbar.\n\n"
            "Größe / Gitter\n"
            "• A3, A4 oder A5 sowie Hochformat oder Querformat wählen.\n"
            "• Randbreite, Gitterdichte und optionalen Maßstab einstellen.\n"
            "• Map neu laden fordert fehlende oder defekte Kartenkacheln erneut an; in der Vektor-Ansicht wird die Vektorkarte neu geladen.\n\n"
            "Symbol-Punkte\n"
            "• Reiter öffnen und in die Karte klicken, um einen Symbol-Punkt zu setzen.\n"
            "• Bestehende Punkte über Liste oder Klick in der Karte auswählen.\n"
            "• Text, Symbol, Farbe, Größe, Textposition und Textbox-Deckkraft bearbeiten.\n"
            "• Strg+Klick erweitert die Auswahl; Änderungen werden auf alle ausgewählten Punkte angewendet.\n"
            "• Rechtsklick in die Karte hebt jede Auswahl auf.\n\n"
            "Routen\n"
            "• In die Karte klicken, um Routenpunkte zu setzen. Der erste Punkt ist sofort sichtbar.\n"
            "• Berechnungsart wählen (Fuß, Fahrrad oder PKW); Route berechnen erstellt den passenden Pfad.\n"
            "• Ohne Berechnung speichern speichert die geklickte Linie direkt.\n"
            "• Bestehende Routen können ausgewählt, umbenannt, eingefärbt oder gelöscht werden.\n"
            "• Kopieren unter der Wegbeschreibung legt den Text in die Zwischenablage.\n"
            "• Berechnete Route auswählen und die Berechnungsart ändern: die Route wird an Ort und Stelle neu berechnet.\n"
            "• Rechtsklick in die Karte hebt jede Auswahl auf.\n\n"
            "Zonen\n"
            "• Mehrere Eckpunkte in die Karte klicken und danach die Zone speichern.\n"
            "• Füllfarbe, Füll-Deckkraft, Konturfarbe, Konturbreite und Beschriftung einstellen.\n"
            "• Beschriftungen können mittig in der Zone platziert werden.\n"
            "• Rechtsklick in die Karte hebt jede Auswahl auf.\n\n"
            "Bilddatei\n"
            "• JPG- oder PNG-Bilder hochladen.\n"
            "• Bilder können frei verschoben und über Breite/Höhe skaliert werden.\n"
            "• Genutzte Bilddateien sind auswählbar und löschbar.\n"
            "• Rechtsklick in die Karte hebt jede Auswahl auf.\n\n"
            "Legende / Textfeld\n"
            "• Textfeld per Checkbox einblenden und bei Bedarf wieder ausblenden.\n"
            "• Text kann fett, kursiv, unterstrichen, farbig und mit Symbolen gestaltet werden.\n"
            "• Bestehende Textfelder lassen sich in der Liste auswählen und benennen. Ein weiteres Textfeld entsteht nur über Neues Textfeld.\n"
            "• Position Zentriert setzt das Textfeld waagerecht und senkrecht in die Mitte der Karte.\n"
            "• Routen Legende hinzufügen ergänzt die Routen automatisch in ihrer Routenfarbe.\n"
            "• Position, Ausrichtung, Hintergrundfarbe und Deckkraft sind einstellbar.\n\n"
            "Datenschutz / Netzwerk\n"
            "• Genutzte Online-Dienste: Ortssuche nominatim.openstreetmap.org; Rasterkacheln tile.openstreetmap.org (Standard), tile-cyclosm.openstreetmap.fr (Fahrrad), tile.openstreetmap.fr (Humanitär); Routenberechnung routing.openstreetmap.de, als Ausweich router.project-osrm.org; Vektor-Ansicht tiles.openfreemap.org.\n"
            "• Dorthin gehen: der Suchtext, die betrachteten Kartenausschnitte sowie Start-, Ziel- und Zwischenpunkte von Routen. Wie bei jedem Abruf sehen die Dienste außerdem deine IP-Adresse; Suche, Rasterkacheln und Routing bekommen zusätzlich die Systemsprache, die Vektor-Ansicht die übliche Browser-Kennung (Betriebssystem, Chromium-Version).\n"
            "• Das Programm startet in der Vektor-Ansicht, der Vektor-Kartendienst wird also ab Programmstart angesprochen. Er wird nur angesprochen, solange die Vektor-Ansicht gewählt ist. MapLibre selbst wird aus lokalen Dateien geladen.\n"
            "• Der Kachel-Cache wird beim Schließen und beim Start automatisch gelöscht.\n"
            "• Debugging nur bei Bedarf aktivieren; dann wird eine Textdatei im Programmordner geschrieben.\n\n"
            "Tastatur / Auswahl\n"
            "• Strg+Z macht rückgängig, Strg+Y wiederholt. Das betrifft nur Inhalte (Punkte, Texte, Bilder, Routen, Zonen, Titel); Kartenausschnitt und Einstellungen bleiben, wie sie sind.\n"
            "• Strg+A wählt alle Elemente im aktuellen Reiter.\n"
            "• Strg+Klick erweitert eine Mehrfachauswahl.\n"
            "• Vor dem Export wird jede Auswahl automatisch abgewählt."
        )

    def _apply_language(self) -> None:
        lang = self._current_lang()
        for act in getattr(self, "_i18n_actions", []):
            src = act.property("i18n_source")
            if src:
                act.setText(tr_text(src, lang))
        if hasattr(self, "language_label"):
            self.language_label.setText(tr_text("Sprache:", lang))
        if hasattr(self, "debug_checkbox"):
            self.debug_checkbox.setText(tr_text("Debugging aktivieren", lang))
        if hasattr(self, "status_zoom_label"):
            self.status_zoom_label.setText(f"{tr_text('Zoom', lang)} {float(self.canvas.zoom):.2f}")
        if hasattr(self, "manual_text"):
            self.manual_text.setPlainText(self._manual_text_for_lang(lang))
        if hasattr(self, "route_directions"):
            self.route_directions.setPlaceholderText(tr_text("Nach Route berechnen steht hier die kopierbare Wegbeschreibung mit Länge und Dauer.", lang))
        for w in getattr(self, "_i18n_widgets", []):
            try:
                src = w.property("i18n_source")
                if src and hasattr(w, "setText"):
                    w.setText(tr_text(src, lang))
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            try:
                src = w.property("i18n_title_source")
                if src and hasattr(w, "setTitle"):
                    w.setTitle(tr_text(src, lang))
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            try:
                src = w.property("i18n_placeholder_source")
                if src and isinstance(w, QLineEdit):
                    w.setPlaceholderText(tr_text(src, lang))
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        if hasattr(self, "tools_box"):
            for i in range(self.tools_box.count()):
                page = self.tools_box.widget(i)
                src = page.property("toolbox_i18n_source") if page is not None else None
                if src:
                    self.tools_box.setItemText(i, tr_text(str(src), lang))
        for combo_name in ["paper_size_combo", "orientation_combo", "density_combo", "label_pos_combo", "note_pos", "note_align", "scale_pos_combo", "zone_label_pos", "map_layer_combo", "route_profile_combo"]:
            combo = getattr(self, combo_name, None)
            if combo is not None:
                for i in range(combo.count()):
                    src = combo.itemData(i, Qt.ItemDataRole.UserRole + 100)
                    if src:
                        combo.setItemText(i, tr_text(src, lang))
        self._refresh_dynamic_labels()
        if hasattr(self, "poi_filter_checkbox"):
            self._refresh_poi_filter_ui()
        try:
            self.statusBar().showMessage(tr_text("Bereit", lang))
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def _language_changed(self) -> None:
        self._apply_language()

    def _combo_source(self, combo: QComboBox) -> str:
        src = combo.itemData(combo.currentIndex(), Qt.ItemDataRole.UserRole + 100)
        return str(src) if src else combo.currentText()

    def _set_combo_by_source(self, combo: QComboBox, source: str) -> None:
        for i in range(combo.count()):
            src = combo.itemData(i, Qt.ItemDataRole.UserRole + 100) or combo.itemText(i)
            if src == source:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentText(source)

    def _pick_color(self, initial: str, title: str) -> Optional[QColor]:
        """Robuster Farbwähler für Windows/Linux.

        Einige Qt-Plattformdialoge übernehmen freie Farben erst nach einem
        vorherigen Klick auf ein Basisfarbenfeld. Deshalb wird der nicht-native
        Qt-Dialog genutzt und die aktuell gewählte Farbe zusätzlich über
        currentColorChanged/colorSelected zwischengespeichert.
        """
        start = QColor(initial)
        if not start.isValid():
            start = QColor("#000000")
        chosen = {"color": QColor(start)}
        dlg = QColorDialog(start, self)
        dlg.setWindowTitle(title)
        try:
            dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
            dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, False)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        try:
            dlg.setCurrentColor(start)
            dlg.currentColorChanged.connect(lambda c: chosen.__setitem__("color", QColor(c)))
            dlg.colorSelected.connect(lambda c: chosen.__setitem__("color", QColor(c)))
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        if dlg.exec():
            colors = []
            try:
                colors.append(dlg.currentColor())
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            try:
                colors.append(dlg.selectedColor())
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            colors.append(chosen.get("color"))
            for color in colors:
                if color is not None and color.isValid():
                    out = QColor(color)
                    if out.name().lower() != start.name().lower() or len(colors) == 1:
                        return out
            for color in colors:
                if color is not None and color.isValid():
                    return QColor(color)
        return None

    # ---------- UI callbacks ----------
    def _poi_set_status(self, source_text: str) -> None:
        if hasattr(self, "poi_status_label"):
            self.poi_status_label.setText(tr_text(source_text, self._current_lang()))

    def _poi_layers_changed(self) -> None:
        if hasattr(self, "poi_filter_checkbox"):
            self._refresh_poi_filter_ui()

    def _map_mode_chosen(self, vector: bool) -> None:
        available = bool(getattr(self.canvas, "vector_preview", False))
        self.canvas.vector_mode = bool(vector and available)
        self._refresh_poi_filter_ui()

    def _refresh_poi_filter_ui(self) -> None:
        enabled = bool(getattr(self.canvas, "poi_filter_enabled", False))
        available = bool(getattr(self.canvas, "vector_preview", False))
        if not available:
            self.canvas.vector_mode = False
        vector = bool(getattr(self.canvas, "vector_mode", False))
        # Die Kartenebene gehört zur Kartenart: nach einem Wechsel Kacheln und Auswahlfeld nachziehen.
        layer = self.canvas.map_layer
        if self.canvas.tiles.layer != layer:
            self.canvas.tiles.set_layer(layer)
        if hasattr(self, "map_layer_combo") and self._combo_source(self.map_layer_combo) != layer:
            self.map_layer_combo.blockSignals(True)
            self._set_combo_by_source(self.map_layer_combo, layer)
            self.map_layer_combo.blockSignals(False)
        # Kartenebene ohne POI-Ebenen (z. B. Humanitär in Vektor): Filter hat nichts zu tun.
        no_pois = bool(vector and int(getattr(self.canvas, "vector_poi_layers", -1)) == 0)
        if hasattr(self, "map_mode_raster_btn"):
            self.map_mode_raster_btn.setChecked(not vector)
            self.map_mode_vector_btn.setChecked(vector)
            self.map_mode_vector_btn.setEnabled(available)
        if hasattr(self, "poi_filter_checkbox"):
            self.poi_filter_checkbox.blockSignals(True)
            self.poi_filter_checkbox.setChecked(enabled and available)
            self.poi_filter_checkbox.setEnabled(available and vector and not no_pois)
            self.poi_filter_checkbox.blockSignals(False)
        if hasattr(self, "poi_options_widget"):
            self.poi_options_widget.setVisible(enabled and available and vector and not no_pois)
        if hasattr(self, "poi_names_checkbox"):
            self.poi_names_checkbox.blockSignals(True)
            self.poi_names_checkbox.setChecked(bool(getattr(self.canvas, "poi_show_names", True)))
            self.poi_names_checkbox.blockSignals(False)
        if hasattr(self, "poi_icons_checkbox"):
            self.poi_icons_checkbox.blockSignals(True)
            self.poi_icons_checkbox.setChecked(bool(getattr(self.canvas, "poi_show_icons", True)))
            self.poi_icons_checkbox.blockSignals(False)
        selected_categories = set(getattr(self.canvas, "poi_categories_enabled", set(POI_CATEGORY_LABELS.keys())))
        for key, checkbox in getattr(self, "poi_category_checkboxes", {}).items():
            checkbox.blockSignals(True)
            checkbox.setChecked(key in selected_categories)
            checkbox.blockSignals(False)
        if hasattr(self, "poi_zoom_slider"):
            self.poi_zoom_slider.blockSignals(True)
            self.poi_zoom_slider.setValue(int(round(float(getattr(self.canvas, "poi_zoom_offset", 0.0)) * 2)))
            self.poi_zoom_slider.blockSignals(False)
            self._update_poi_zoom_label()
        if not available:
            self.canvas.poi_filter_enabled = False
            self._poi_set_status("Vektor-Ansicht nicht verfügbar")
        elif not vector:
            self._poi_set_status("Der POI-Filter ist nur in der Vektor-Ansicht bedienbar.")
        elif no_pois:
            self._poi_set_status("Diese Kartenebene enthält in der Vektor-Ansicht keine POIs.")
        elif enabled:
            self._poi_set_status("Vektorfilter aktiv")
        else:
            self._poi_set_status("Vektor-Ansicht aktiv")
        self.canvas._sync_vector_map()
        self.canvas.update()

    def _poi_filter_toggled(self, checked: bool) -> None:
        if checked and not bool(getattr(self.canvas, "vector_preview", False)):
            self.canvas.poi_filter_enabled = False
            self._refresh_poi_filter_ui()
            QMessageBox.warning(self, self._tr("Kartennamen / Symbole"), self._tr("Vektor-Ansicht nicht verfügbar"))
            return
        if checked and not bool(getattr(self.canvas, "vector_mode", False)):
            self._refresh_poi_filter_ui()
            return
        self.canvas.poi_filter_enabled = bool(checked)
        self._refresh_poi_filter_ui()

    def _poi_names_toggled(self, checked: bool) -> None:
        self.canvas.poi_show_names = bool(checked)
        self.canvas._sync_vector_map()
        self.canvas.update()

    def _poi_icons_toggled(self, checked: bool) -> None:
        self.canvas.poi_show_icons = bool(checked)
        self.canvas._sync_vector_map()
        self.canvas.update()

    def _poi_category_toggled(self, category: str, checked: bool) -> None:
        selected = set(getattr(self.canvas, "poi_categories_enabled", set()))
        if checked:
            selected.add(category)
        else:
            selected.discard(category)
        self.canvas.poi_categories_enabled = selected
        self.canvas._sync_vector_map()
        self.canvas.update()

    def _poi_zoom_offset_changed(self, value: int) -> None:
        self.canvas.poi_zoom_offset = clamp(float(value) / 2.0, POI_ZOOM_OFFSET_MIN, POI_ZOOM_OFFSET_MAX)
        self._update_poi_zoom_label()
        self.canvas._sync_vector_map()
        self.canvas.update()

    def _update_poi_zoom_label(self) -> None:
        # Zeigt, ab welchem angezeigten Zoom die erste POI-Rangstufe erscheint. Der Zoom der
        # Vektorkarte weicht vom angezeigten Zoom ab (siehe MapLibreContainer.maplibre_zoom).
        if not hasattr(self, "poi_zoom_value_label"):
            return
        offset = float(getattr(self.canvas, "poi_zoom_offset", 0.0))
        scale, _ox, _oy = self.canvas.page_transform()
        shown = POI_STYLE_FIRST_ZOOM + offset + 1.0 - math.log2(max(1e-6, float(scale)))
        text = f"{shown:.1f}".replace(".", ",") if self._current_lang() == "de" else f"{shown:.1f}"
        if abs(offset) < 1e-9:
            text += " " + self._tr("(Vorgabe)")
        self.poi_zoom_value_label.setText(text)


    def search_place(self) -> None:
        query = self.place_search.text().strip()
        if not query:
            return
        url = QUrl(f"https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=12&q={quote(query)}")
        req = QNetworkRequest(url)
        req.setRawHeader(b"User-Agent", NETWORK_USER_AGENT.encode("ascii"))
        req.setRawHeader(b"Accept", b"application/json")
        reply = self.net.get(req)
        reply.finished.connect(lambda r=reply: self._place_search_finished(r))
        self.statusBar().showMessage(tr_text("Suche läuft...", self._current_lang()))

    def _place_search_finished(self, reply: QNetworkReply) -> None:
        try:
            data = bytes(reply.readAll())
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise RuntimeError(reply.errorString())
            results = json.loads(data.decode("utf-8"))
        except Exception as exc:
            QMessageBox.warning(self, tr_text("Ortssuche", self._current_lang()), f"{self._tr('Suche fehlgeschlagen:')}\n{exc}")
            reply.deleteLater()
            return
        finally:
            try:
                reply.deleteLater()
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        self.search_results = []
        self.search_result_combo.clear()
        for item in results:
            try:
                lat = float(item.get("lat"))
                lon = float(item.get("lon"))
            except (TypeError, ValueError):
                continue
            display = item.get("display_name", "Ort")
            bbox = None
            try:
                raw_bbox = item.get("boundingbox") or []
                if len(raw_bbox) == 4:
                    bbox = [float(v) for v in raw_bbox]
            except Exception:
                bbox = None
            self.search_results.append({"display": display, "lat": lat, "lon": lon, "bbox": bbox})
            self.search_result_combo.addItem(display)
        self.statusBar().showMessage(f"{len(self.search_results)} {self._tr('Suchergebnisse')}")
        if self.search_results:
            self.center_selected_search_result()

    def _zoom_for_search_bbox(self, bbox, fallback: float) -> float:
        try:
            lat_min, lat_max, lon_min, lon_max = [float(v) for v in bbox]
            r = self.canvas.map_rect()
            fallback_zoom = float(fallback)
            if fallback_zoom > 19.0:
                fallback_zoom /= 20.0
            for step in range(380, 39, -1):
                z = step / 20.0
                x1, y1 = latlon_to_world(lat_min, lon_min, z)
                x2, y2 = latlon_to_world(lat_max, lon_max, z)
                if abs(x2 - x1) <= r.width() * 0.82 and abs(y2 - y1) <= r.height() * 0.82:
                    return z
            return float(clamp(fallback_zoom, 2.0, 19.0))
        except Exception:
            try:
                value = float(fallback)
                if value > 19.0:
                    value /= 20.0
                return float(clamp(value, 2.0, 19.0))
            except Exception:
                return 6.0

    def _search_result_changed(self, *_args) -> None:
        # Belegt nur den Zoom-Regler vor. Gesprungen wird, wenn der Nutzer ein Ergebnis wählt
        # (activated) oder „Zentrieren“ drückt – nicht schon beim Füllen der Liste.
        idx = self.search_result_combo.currentIndex() if hasattr(self, "search_result_combo") else -1
        if idx < 0 or idx >= len(self.search_results):
            return
        item = self.search_results[idx]
        bbox = item.get("bbox")
        if bbox and hasattr(self, "search_zoom_slider"):
            current_zoom = float(self.search_zoom_slider.value()) / 20.0
            zoom = self._zoom_for_search_bbox(bbox, current_zoom)
            self.search_zoom_slider.blockSignals(True)
            self.search_zoom_slider.setValue(int(round(float(clamp(zoom, 2.0, 19.0)) * 20.0)))
            self.search_zoom_slider.blockSignals(False)

    def center_selected_search_result(self) -> None:
        idx = self.search_result_combo.currentIndex()
        if idx < 0 or idx >= len(self.search_results):
            return
        item = self.search_results[idx]
        zoom = (
            float(self.search_zoom_slider.value()) / 20.0
            if hasattr(self, "search_zoom_slider")
            else max(float(self.canvas.zoom), 15.0)
        )
        bbox = item.get("bbox")
        if bbox:
            zoom = self._zoom_for_search_bbox(bbox, zoom)
            try:
                self.search_zoom_slider.blockSignals(True)
                self.search_zoom_slider.setValue(int(round(float(clamp(zoom, 2.0, 19.0)) * 20.0)))
                self.search_zoom_slider.blockSignals(False)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        self.canvas.center_on(item["lat"], item["lon"], zoom)
        self.canvas.repaint()

    def add_search_result_as_marker(self) -> None:
        idx = self.search_result_combo.currentIndex()
        if idx < 0 or idx >= len(self.search_results):
            return
        item = self.search_results[idx]
        label = self.place_search.text().strip() or item["display"].split(",")[0]
        self.canvas.add_marker_from_controls(item["lat"], item["lon"], label)

    def _set_work_mode(self, mode: str) -> None:
        self.canvas.set_mode = mode == "points"
        self.canvas.route_mode = mode == "route"
        self.canvas.zone_mode = mode == "zone"
        self.canvas.logo_mode = mode == "logo"
        self.canvas.update_status()
        self.canvas.update()

    def _toolbox_changed(self, index: int) -> None:
        # Order: 0 search, 1 title, 2 size/grid, 3 points, 4 route, 5 zones, 6 image file, 7 legend
        if index == 3:
            self._set_work_mode("points")
        elif index == 4:
            self._set_work_mode("route")
        elif index == 5:
            self._set_work_mode("zone")
        elif index == 6:
            self._set_work_mode("logo")
        else:
            self._set_work_mode("pan")

    def _set_mode_toggled(self) -> None:
        self._set_work_mode("points")

    def _route_mode_toggled(self) -> None:
        self._set_work_mode("route")

    def _remember_note_selection(self) -> None:
        try:
            cursor = self.note_text.textCursor()
            if cursor.hasSelection():
                self._note_saved_selection = (cursor.selectionStart(), cursor.selectionEnd())
        except Exception:
            self._note_saved_selection = (0, 0)

    def _note_color_target_range(self) -> Tuple[int, int]:
        cursor = self.note_text.textCursor()
        if cursor.hasSelection():
            return cursor.selectionStart(), cursor.selectionEnd()
        start, end = getattr(self, "_note_saved_selection", (0, 0))
        doc_len = max(0, int(self.note_text.document().characterCount()) - 1)
        start = max(0, min(int(start), doc_len))
        end = max(0, min(int(end), doc_len))
        if end > start:
            return start, end
        pos = cursor.position()
        return pos, pos

    def _apply_note_char_format_to_range(self, fmt: QTextCharFormat, start: int, end: int, keep_selection: bool = True) -> None:
        doc = self.note_text.document()
        doc_len = max(0, int(doc.characterCount()) - 1)
        start = max(0, min(int(start), doc_len))
        end = max(0, min(int(end), doc_len))
        if end > start:
            cur = QTextCursor(doc)
            cur.setPosition(start)
            cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cur.mergeCharFormat(fmt)
            restore = QTextCursor(doc)
            if keep_selection:
                restore.setPosition(start)
                restore.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                self._note_saved_selection = (start, end)
            else:
                restore.setPosition(end)
                self._note_saved_selection = (0, 0)
            self.note_text.setTextCursor(restore)
            return
        self.note_text.mergeCurrentCharFormat(fmt)

    def _format_note_selection(self, attr: str, enabled: bool) -> None:
        cursor = self.note_text.textCursor()
        fmt = QTextCharFormat()
        if attr == "bold":
            fmt.setFontWeight(QFont.Weight.Bold if enabled else QFont.Weight.Normal)
        elif attr == "italic":
            fmt.setFontItalic(enabled)
        elif attr == "underline":
            fmt.setFontUnderline(enabled)
        cursor.mergeCharFormat(fmt)
        self.note_text.mergeCurrentCharFormat(fmt)
        self.note_text.setFocus()
        self._live_update_note()

    def _choose_route_color(self) -> None:
        c = self._pick_color(self.route_color, tr_text("Routenfarbe wählen", self._current_lang()))
        if c.isValid():
            self.route_color = c.name()
            self.canvas.current_route_color = self.route_color
            if self.canvas.selected_route() is not None:
                self.canvas.update_selected_route(color=self.route_color)
            self._set_color_button_text(self.route_color_btn, "Farbe:", self.route_color)
            self.route_color_btn.setStyleSheet(f"background:{self.route_color}; color:#000;")
            self.canvas.update()

    def _route_width_changed(self, value: int) -> None:
        self.canvas.current_route_width = int(value)
        self._live_update_route()

    def _route_opacity_changed(self, value: int) -> None:
        self.canvas.current_route_opacity = int(value)
        self._live_update_route()
        self.canvas.update()

    def _live_update_route(self, *args) -> None:
        if getattr(self, "_loading_selection", False):
            return
        r = self.canvas.selected_route()
        if not r:
            return
        self.canvas._restoring_history = True
        try:
            self.canvas.update_selected_route(
                name=self.route_name.text() or f"Route {r.id}",
                color=self.route_color,
                width=int(self.route_width.value()),
                opacity=self.route_opacity.value() if hasattr(self, "route_opacity") else 80,
            )
            self._refresh_route_list()
        finally:
            self.canvas._restoring_history = False

    def save_clicked_route(self) -> None:
        pts = list(self.canvas.active_route_points)
        distance_m = self._polyline_distance_m(pts)
        directions = self._manual_route_text(distance_m, self._current_lang())
        route = self.canvas.add_route(
            pts,
            self.route_name.text() or f"Route {self.canvas.next_route_id}",
            self.route_color,
            self.route_width.value(),
            calculated=False,
            opacity=self.route_opacity.value() if hasattr(self, "route_opacity") else 80,
            distance_m=distance_m,
            duration_s=0.0,
            directions_text=directions,
            control_points=pts,
        )
        if not route:
            QMessageBox.information(self, self._tr("Route"), self._tr("Bitte mindestens zwei Routenpunkte setzen."))
        elif hasattr(self, "route_directions"):
            self.route_directions.setPlainText(route.directions_text)


    def edit_selected_route_as_points(self) -> None:
        route = self.canvas.selected_route()
        if route is None:
            QMessageBox.information(self, tr_text("Route", self._current_lang()), tr_text("Bitte zuerst eine Route auswählen.", self._current_lang()))
            return
        raw_points = list(getattr(route, "control_points", []) or getattr(route, "points", []) or [])
        pts: List[Tuple[float, float]] = []
        for lat, lon in raw_points:
            try:
                pts.append((float(lat), float(lon)))
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        if len(pts) < 2:
            QMessageBox.information(self, tr_text("Route", self._current_lang()), tr_text("Bitte mindestens zwei Routenpunkte setzen.", self._current_lang()))
            return
        self.canvas.remember()
        self.route_name.setText(str(getattr(route, "name", "Route") or "Route"))
        self.route_color = str(getattr(route, "color", "#ff0505") or "#ff0505")
        self.canvas.current_route_color = self.route_color
        self.canvas.current_route_width = int(getattr(route, "width", 6) or 6)
        self.canvas.current_route_opacity = int(getattr(route, "opacity", 80) or 80)
        try:
            self._set_color_button_text(self.route_color_btn, "Farbe:", self.route_color)
            self.route_color_btn.setStyleSheet(f"background:{self.route_color}; color:#000;")
            self.route_width.setValue(self.canvas.current_route_width)
            if hasattr(self, "route_opacity"):
                self.route_opacity.setValue(self.canvas.current_route_opacity)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        self.canvas.active_route_points = pts
        route_id = int(getattr(route, "id", -1))
        self.canvas.routes = [r for r in self.canvas.routes if int(getattr(r, "id", -2)) != route_id]
        self.canvas.selected_route_id = None
        self.canvas.selected_route_ids.clear()
        self._refresh_route_list()
        if hasattr(self, "route_directions"):
            self.route_directions.setPlainText(tr_text("Route wird als bearbeitbare Punkte weitergeführt. Danach Punkt zurück, weitere Punkte setzen oder erneut berechnen/speichern.", self._current_lang()))
        self.canvas.update_status()
        self.canvas.update()

    def add_selected_marker_to_route(self) -> None:
        m = self.canvas.selected_marker()
        if not m:
            QMessageBox.information(self, self._tr("Route"), self._tr("Bitte zuerst einen Punkt auswählen."))
            return
        self.canvas.active_route_points.append((m.lat, m.lon))
        self.canvas.update_status()
        self.canvas.update()

    def _copy_route_directions(self) -> None:
        text = self.route_directions.toPlainText() if hasattr(self, "route_directions") else ""
        if not text.strip():
            self.statusBar().showMessage(self._tr("Keine Wegbeschreibung vorhanden."))
            return
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(self._tr("Wegbeschreibung kopiert."))

    def _route_profile_changed(self, *_args) -> None:
        if not hasattr(self, "route_profile_combo"):
            return
        profile = self._combo_source(self.route_profile_combo)
        self.canvas.current_route_profile = profile
        if getattr(self, "_loading_selection", False) or getattr(self.canvas, "_restoring_history", False):
            return
        # Ist eine berechnete Route gewählt, rechnet die neue Berechnungsart sie an Ort und Stelle neu.
        # Nicht, solange Punkte für eine neue Route gesetzt sind: dann gilt die Wahl der neuen Route.
        route = self.canvas.selected_route()
        if route is None or not route.calculated or self.canvas.active_route_points:
            return
        if getattr(route, "profile", "") == profile:
            return
        points = list(getattr(route, "control_points", []) or [])
        if len(points) < 2:
            return
        coords = ";".join(f"{float(lon):.7f},{float(lat):.7f}" for lat, lon in points)
        self._request_route(coords, profile, 0, replace_id=int(route.id))
        self.statusBar().showMessage(self._tr("Route wird neu berechnet..."))

    def calculate_route_from_clicks(self) -> None:
        points = list(self.canvas.active_route_points)
        if len(points) < 2:
            QMessageBox.information(self, self._tr("Route"), self._tr("Bitte mindestens Start und Ziel setzen."))
            return
        coords = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in points)
        profile = self._combo_source(self.route_profile_combo) if hasattr(self, "route_profile_combo") else "Fuß-Route"
        self.canvas.current_route_profile = profile
        self._request_route(coords, profile, 0)
        status_by_profile = {
            "Fuß-Route": "Fußroute wird berechnet...",
            "Fahrrad-Route": "Fahrradroute wird berechnet...",
            "PKW-Route": "PKW-Route wird berechnet...",
        }
        self.statusBar().showMessage(tr_text(status_by_profile.get(profile, "Fußroute wird berechnet..."), self._current_lang()))

    def _route_urls(self, coords: str, profile: str) -> List[str]:
        profile = profile if profile in ("Fuß-Route", "Fahrrad-Route", "PKW-Route") else "Fuß-Route"
        if profile == "Fahrrad-Route":
            return [
                f"https://routing.openstreetmap.de/routed-bike/route/v1/bike/{coords}?overview=full&geometries=geojson&steps=true",
                f"https://routing.openstreetmap.de/routed-bike/route/v1/bicycle/{coords}?overview=full&geometries=geojson&steps=true",
            ]
        if profile == "PKW-Route":
            return [
                f"https://routing.openstreetmap.de/routed-car/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true",
                f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true",
            ]
        return [
            f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{coords}?overview=full&geometries=geojson&steps=true",
            f"https://router.project-osrm.org/route/v1/foot/{coords}?overview=full&geometries=geojson&steps=true",
        ]

    def _request_route(self, coords: str, profile: str, attempt: int, replace_id: int = 0) -> None:
        urls = self._route_urls(coords, profile)
        attempt = max(0, min(int(attempt), len(urls) - 1))
        req = QNetworkRequest(QUrl(urls[attempt]))
        req.setRawHeader(b"User-Agent", NETWORK_USER_AGENT.encode("ascii"))
        req.setRawHeader(b"Accept", b"application/json")
        reply = self.net.get(req)
        reply.setProperty("route_coords", coords)
        reply.setProperty("route_profile", profile)
        reply.setProperty("route_attempt", attempt)
        reply.setProperty("route_replace_id", int(replace_id))
        reply.finished.connect(lambda r=reply: self._route_finished(r))

    def _route_finished(self, reply: QNetworkReply) -> None:
        coords_prop = str(reply.property("route_coords") or "")
        profile_prop = str(reply.property("route_profile") or "Fuß-Route")
        attempt = int(reply.property("route_attempt") or 0)
        replace_id = int(reply.property("route_replace_id") or 0)
        try:
            data = bytes(reply.readAll())
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise RuntimeError(reply.errorString())
            obj = json.loads(data.decode("utf-8"))
            routes = obj.get("routes", [])
            if not routes:
                raise RuntimeError(obj.get("message", "Keine Route gefunden"))
            route_obj = routes[0]
            coords = route_obj.get("geometry", {}).get("coordinates", [])
            points = [(float(lat), float(lon)) for lon, lat in coords]
            if len(points) < 2:
                raise RuntimeError("Route enthält zu wenige Punkte")
            distance_m = float(route_obj.get("distance", 0.0) or 0.0)
            duration_s = float(route_obj.get("duration", 0.0) or 0.0)
            directions_text = self._format_route_directions(route_obj, self._current_lang())
            route_control_points: List[Tuple[float, float]] = []
            for pair in coords_prop.split(";"):
                try:
                    lon_s, lat_s = pair.split(",", 1)
                    route_control_points.append((float(lat_s), float(lon_s)))
                except Exception as exc:
                    log_debug("Stiller Fehler", exc)
            if len(route_control_points) < 2:
                route_control_points = list(points)
        except Exception as exc:
            try:
                reply.deleteLater()
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            if coords_prop and attempt + 1 < len(self._route_urls(coords_prop, profile_prop)):
                self.statusBar().showMessage(tr_text("Route wird mit Alternativ-Endpunkt berechnet...", self._current_lang()))
                self._request_route(coords_prop, profile_prop, attempt + 1, replace_id=replace_id)
                return
            if replace_id:
                # Neuberechnung gescheitert: die Route bleibt, das Auswahlfeld zeigt wieder ihre Berechnungsart.
                kept = next((r for r in self.canvas.routes if r.id == replace_id), None)
                if kept is not None and getattr(kept, "profile", "") and self.canvas.selected_route_id == replace_id:
                    self._loading_selection = True
                    try:
                        self._set_combo_by_source(self.route_profile_combo, kept.profile)
                    finally:
                        self._loading_selection = False
            QMessageBox.warning(self, self._tr("Route"), f"{self._tr('Routenberechnung fehlgeschlagen:')}\n{exc}")
            return
        finally:
            try:
                reply.deleteLater()
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        if replace_id:
            target = next((r for r in self.canvas.routes if r.id == replace_id), None)
            if target is None:
                return
            self.canvas.remember()
            target.points = points
            target.control_points = route_control_points
            target.calculated = True
            target.distance_m = distance_m
            target.duration_s = duration_s
            target.directions_text = directions_text
            target.profile = profile_prop
            if self.canvas.selected_route_id == target.id and hasattr(self, "route_directions"):
                self.route_directions.setPlainText(target.directions_text)
            self.canvas.update_status()
            self.canvas.update()
            self.statusBar().showMessage(self._tr("Route neu berechnet"))
            return
        name = self.route_name.text() or f"Route {self.canvas.next_route_id}"
        route = self.canvas.add_route(points, name, self.route_color, self.route_width.value(), calculated=True,
                                      opacity=self.route_opacity.value() if hasattr(self, "route_opacity") else 80,
                                      distance_m=distance_m, duration_s=duration_s, directions_text=directions_text,
                                      control_points=route_control_points)
        if route is not None:
            route.profile = profile_prop
        if route is not None and hasattr(self, "route_directions"):
            self.route_directions.setPlainText(route.directions_text)
        self.statusBar().showMessage(tr_text("Route berechnet", self._current_lang()))


    def _format_distance(self, meters: float, lang: Optional[str] = None) -> str:
        lang = lang or self._current_lang()
        meters = max(0.0, float(meters or 0.0))
        if meters >= 1000.0:
            value = f"{meters/1000.0:.2f}"
            if lang == "de":
                value = value.replace(".", ",")
            return f"{value} km"
        return f"{int(round(meters))} m"

    def _format_duration(self, seconds: float, lang: Optional[str] = None) -> str:
        lang = lang or self._current_lang()
        seconds = max(0.0, float(seconds or 0.0))
        minutes = int(round(seconds / 60.0))
        if minutes < 60:
            return f"{minutes} min"
        h, m = divmod(minutes, 60)
        return f"{h} h {m:02d} min"

    def _polyline_distance_m(self, points: List[Tuple[float, float]]) -> float:
        def haversine(a, b):
            lat1, lon1 = a
            lat2, lon2 = b
            r = 6371000.0
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            h = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
            return 2.0 * r * math.asin(min(1.0, math.sqrt(h)))
        total = 0.0
        for a, b in zip(points, points[1:]):
            try:
                total += haversine(a, b)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
        return total

    def _manual_route_text(self, distance_m: float, lang: Optional[str] = None) -> str:
        lang = lang or self._current_lang()
        if lang == "en":
            return "Manual click route\nLength: " + self._format_distance(distance_m, lang) + "\nDuration: not calculated"
        return "Manuelle Klickroute\nLänge: " + self._format_distance(distance_m, lang) + "\nDauer: nicht berechnet"

    def _route_summary_text(self, route) -> str:
        if not route:
            return ""
        lang = self._current_lang()
        lines = [str(getattr(route, "name", "Route") or "Route")]
        if getattr(route, "distance_m", 0.0):
            label = "Length: " if lang == "en" else "Länge: "
            lines.append(label + self._format_distance(getattr(route, "distance_m", 0.0), lang))
        if getattr(route, "duration_s", 0.0):
            label = "Duration: " if lang == "en" else "Dauer: "
            lines.append(label + self._format_duration(getattr(route, "duration_s", 0.0), lang))
        return "\n".join(lines)

    def _direction_modifier_text(self, modifier: str, lang: Optional[str] = None) -> str:
        lang = lang or self._current_lang()
        key = str(modifier or "").strip().lower().replace("_", " ").replace("-", " ")
        de = {
            "right": "rechts",
            "left": "links",
            "slight right": "leicht rechts",
            "slight left": "leicht links",
            "sharp right": "scharf rechts",
            "sharp left": "scharf links",
            "straight": "geradeaus",
            "uturn": "wenden",
            "u turn": "wenden",
        }
        en = {
            "right": "right",
            "left": "left",
            "slight right": "slight right",
            "slight left": "slight left",
            "sharp right": "sharp right",
            "sharp left": "sharp left",
            "straight": "straight",
            "uturn": "make a U-turn",
            "u turn": "make a U-turn",
        }
        table = en if lang == "en" else de
        return table.get(key, key)

    def _maneuver_to_text(self, maneuver: dict, road_name: str, lang: Optional[str] = None) -> str:
        lang = lang or self._current_lang()
        typ = str(maneuver.get("type", "") or "").strip().lower().replace("_", " ").replace("-", " ")
        mod_raw = str(maneuver.get("modifier", "") or "")
        mod = self._direction_modifier_text(mod_raw, lang)
        road = road_name.strip()
        if lang == "en":
            road_txt = road or "unnamed road/path"
            if typ == "depart":
                return f"Start on {road_txt}"
            if typ == "arrive":
                return ""
            if typ in ("turn", "end of road"):
                return f"Turn {mod} onto {road_txt}" if mod else f"Continue onto {road_txt}"
            if typ in ("new name", "continue", "notification"):
                return f"Continue on {road_txt}"
            if typ in ("roundabout", "rotary", "roundabout turn"):
                exit_no = maneuver.get("exit")
                if exit_no:
                    return f"At the roundabout take exit {exit_no} onto {road_txt}"
                return f"Enter the roundabout onto {road_txt}"
            if typ in ("merge", "on ramp"):
                return f"Merge onto {road_txt}"
            if typ == "off ramp":
                return f"Take the ramp onto {road_txt}"
            if typ == "fork":
                return f"At the fork keep {mod} onto {road_txt}" if mod else f"At the fork continue onto {road_txt}"
            return f"{typ or 'Continue'} {mod} onto {road_txt}".strip()

        road_txt = road or "unbenannte Straße/Weg"
        if typ == "depart":
            return f"Start auf {road_txt}"
        if typ == "arrive":
            return ""
        if typ in ("turn", "end of road"):
            if mod:
                return f"{mod.capitalize()} abbiegen auf {road_txt}"
            return f"Weiter auf {road_txt}"
        if typ in ("new name", "continue", "notification"):
            return f"Weiter auf {road_txt}"
        if typ in ("roundabout", "rotary", "roundabout turn"):
            exit_no = maneuver.get("exit")
            if exit_no:
                return f"Im Kreisverkehr Ausfahrt {exit_no} nehmen auf {road_txt}"
            return f"In den Kreisverkehr auf {road_txt}"
        if typ in ("merge", "on ramp"):
            return f"Einfädeln auf {road_txt}"
        if typ == "off ramp":
            return f"Ausfahrt nehmen auf {road_txt}"
        if typ == "fork":
            return f"An der Gabelung {mod} halten auf {road_txt}" if mod else f"An der Gabelung auf {road_txt} weiter"
        return f"{typ or 'Weiter'} {mod} auf {road_txt}".strip()

    def _format_route_directions(self, route_obj: dict, lang: Optional[str] = None) -> str:
        lang = lang or self._current_lang()
        distance_m = float(route_obj.get("distance", 0.0) or 0.0)
        duration_s = float(route_obj.get("duration", 0.0) or 0.0)
        if lang == "en":
            lines = ["Directions", "Length: " + self._format_distance(distance_m, lang), "Duration: " + self._format_duration(duration_s, lang), ""]
            no_steps = "No turn-by-turn directions were received from the routing service."
        else:
            lines = ["Wegbeschreibung", "Länge: " + self._format_distance(distance_m, lang), "Dauer: " + self._format_duration(duration_s, lang), ""]
            no_steps = "Keine einzelnen Abbiegehinweise vom Routingdienst erhalten."
        step_no = 1
        for leg in route_obj.get("legs", []) or []:
            for step in leg.get("steps", []) or []:
                dist = float(step.get("distance", 0.0) or 0.0)
                dur = float(step.get("duration", 0.0) or 0.0)
                name = str(step.get("name", "") or "")
                instr = self._maneuver_to_text(step.get("maneuver", {}) or {}, name, lang)
                if not instr:
                    continue
                lines.append(f"{step_no}. {instr} — {self._format_distance(dist, lang)}, {self._format_duration(dur, lang)}")
                step_no += 1
        if step_no == 1:
            lines.append(no_steps)
        return "\n".join(lines).strip()

    def _paper_size_changed(self, text: str) -> None:
        self.canvas.set_paper_size(self._combo_source(self.paper_size_combo))
        self.canvas.update_status()

    def _orientation_changed(self, text: str) -> None:
        self.canvas.set_orientation(self._combo_source(self.orientation_combo))
        self.canvas.update_status()

    def _map_title_changed(self, text: str) -> None:
        self.canvas.map_title = text
        self.canvas.update_status()
        self.canvas.update()

    def _border_changed(self, value: int) -> None:
        self.canvas.border = float(value)
        self.canvas.update_status()
        self.canvas.update()

    def _grid_toggled(self) -> None:
        self.canvas.show_grid = self.grid_box.isChecked()
        self.canvas.update()

    def _grid_lines_toggled(self) -> None:
        self.canvas.show_grid_lines = self.grid_lines_box.isChecked()
        self.canvas.update()

    def _choose_color(self, color: str) -> None:
        self.canvas.set_current_color(color)
        if self.canvas.selected_marker_ids or self.canvas.selected_marker_id is not None:
            self.canvas.update_selected_marker(color=color)
        else:
            self.canvas.update()
        self._refresh_symbol_button_styles()
        self._refresh_color_button_styles()

    def _choose_custom_color(self) -> None:
        c = self._pick_color(self.canvas.current_color, tr_text("Symbolfarbe wählen", self._current_lang()))
        if c.isValid():
            self._choose_color(c.name())

    def _choose_symbol(self, key: str) -> None:
        self.canvas.set_current_symbol(key)
        if self.canvas.selected_marker_ids or self.canvas.selected_marker_id is not None:
            self.canvas.update_selected_marker(symbol=key)
        else:
            self.canvas.update()
        self._refresh_symbol_button_styles()

    def _choose_marker_text_color(self) -> None:
        c = self._pick_color(self.marker_text_color, tr_text("Textfarbe wählen", self._current_lang()))
        if c.isValid():
            self.marker_text_color = c.name()
            self._set_color_button_text(self.marker_text_color_btn, "Textfarbe:", self.marker_text_color)
            self.marker_text_color_btn.setStyleSheet(f"background:{self.marker_text_color}; color:#ffffff;")
            if self.canvas.selected_marker_ids or self.canvas.selected_marker_id is not None:
                self.canvas.update_selected_marker(text_color=self.marker_text_color)
            else:
                self.canvas.update()

    def upload_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Bilddatei hochladen", "", "Bilddateien (*.png *.jpg *.jpeg)")
        if not path:
            return
        logo = self.canvas.add_logo_from_path(path)
        if not logo:
            QMessageBox.warning(self, self._tr("Bilddatei"), self._tr("Bilddatei konnte nicht geladen werden. Bitte PNG oder JPG verwenden."))

    def _logo_selected(self, logo) -> None:
        self._refresh_logo_list()
        if logo is None:
            if hasattr(self, "logo_info"):
                self.logo_info.setText("")
            return
        if hasattr(self, "logo_info"):
            self.logo_info.setText("")
        self.logo_width.blockSignals(True)
        self.logo_height.blockSignals(True)
        self.logo_width.setValue(int(round(logo.w)))
        self.logo_height.setValue(int(round(logo.h)))
        self.logo_width.blockSignals(False)
        self.logo_height.blockSignals(False)

    def _logo_width_changed(self, value: int) -> None:
        logo = self.canvas.selected_logo()
        if not logo:
            return
        if logo.w > 0 and logo.h > 0:
            ratio = logo.h / logo.w
            logo.w = float(value)
            logo.h = max(8.0, float(value) * ratio)
            self.logo_height.blockSignals(True)
            self.logo_height.setValue(int(round(logo.h)))
            self.logo_height.blockSignals(False)
        else:
            logo.w = float(value)
        self.canvas.update_status()
        self.canvas.update()

    def _logo_height_changed(self, value: int) -> None:
        logo = self.canvas.selected_logo()
        if not logo:
            return
        logo.h = float(value)
        self.canvas.update_status()
        self.canvas.update()

    def _note_font_changed(self, value: int) -> None:
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(value))
        cursor = self.note_text.textCursor()
        if not cursor.hasSelection():
            saved = self.note_text.textCursor()
            self.note_text.selectAll()
            cursor = self.note_text.textCursor()
            cursor.mergeCharFormat(fmt)
            self.note_text.setTextCursor(saved)
        else:
            cursor.mergeCharFormat(fmt)
        self.note_text.mergeCurrentCharFormat(fmt)
        self._resize_note_symbols_to_font()
        self._live_update_note()

    def _choose_note_color(self) -> None:
        c = self._pick_color(self.note_color, tr_text("Füllfarbe wählen", self._current_lang()))
        if c.isValid():
            self.note_color = c.name()
            self._set_color_button_text(self.note_color_btn, "Füllfarbe:", self.note_color)
            self._style_color_button(self.note_color_btn, self.note_color)
            self._live_update_note()

    def _choose_note_text_color(self) -> None:
        c = self._pick_color(self.note_text_color, tr_text("Textfarbe wählen", self._current_lang()))
        if c and c.isValid():
            self.note_text_color = c.name()
            self._set_named_color_button(self.note_text_color_btn, "Textfarbe:", self.note_text_color)
            fmt = QTextCharFormat()
            fmt.setForeground(c)
            # Die globale Textfarbe ist der Grundstil für nicht individuell
            # formatierte Textbereiche und neue Eingaben. Bereits markierte
            # Einzelbereiche bleiben als Rich-Text erhalten.
            self.note_text.mergeCurrentCharFormat(fmt)
            self.note_text.setTextColor(c)
            self._live_update_note()

    def _choose_note_selection_color(self) -> None:
        start, end = self._note_color_target_range()
        c = self._pick_color(getattr(self, "note_selection_color", getattr(self, "note_text_color", "#000000")), tr_text("Textfarbe wählen", self._current_lang()))
        if c and c.isValid():
            self.note_selection_color = c.name()
            if hasattr(self, "note_selection_color_btn"):
                self._set_named_color_button(self.note_selection_color_btn, "Farbe für Auswahl:", self.note_selection_color)
            fmt = QTextCharFormat()
            fmt.setForeground(c)
            self.note_text.setFocus()
            if end > start:
                self._apply_note_char_format_to_range(fmt, start, end, keep_selection=False)
            else:
                self.note_text.setCurrentCharFormat(fmt)
                self.note_text.mergeCurrentCharFormat(fmt)
            self._restore_note_editor_base_format()
            self._live_update_note()

    def _note_symbol_pixel_size(self) -> int:
        try:
            return max(12, int(round(float(self.note_font.value()) * 1.68)))
        except Exception:
            return 20

    def _choose_note_symbol_color(self, color: str) -> None:
        self.note_symbol_color = color
        self._refresh_note_symbol_color_button_styles()
        self._apply_note_symbol_color_to_selection(color)
        self._restore_note_editor_base_format()

    def _refresh_note_symbol_color_button_styles(self) -> None:
        current = getattr(self, "note_symbol_color", self.canvas.current_color)
        palette_hit = False
        for color, button in getattr(self, "note_symbol_color_buttons", {}).items():
            active = color.lower() == current.lower()
            palette_hit = palette_hit or active
            border = "3px solid #00aaff" if active else "1px solid #555"
            button.setFixedSize(32, 32)
            button.setMinimumSize(32, 32)
            button.setMaximumSize(32, 32)
            button.setStyleSheet(f"background:{color}; border:{border}; border-radius:0px; padding:0px; min-width:32px; min-height:32px; max-width:32px; max-height:32px;")
        if hasattr(self, "note_symbol_custom_color_btn"):
            border = "3px solid #00aaff" if not palette_hit else "1px solid #555"
            self.note_symbol_custom_color_btn.setStyleSheet(f"background:{current}; color:#000; border:{border}; border-radius:0px; padding:0px; min-width:32px; min-height:32px; max-width:32px; max-height:32px;")

    def _choose_custom_note_symbol_color(self) -> None:
        c = self._pick_color(getattr(self, "note_symbol_color", self.canvas.current_color), tr_text("Symbolfarbe wählen", self._current_lang()))
        if c and c.isValid():
            self._choose_note_symbol_color(c.name())

    def _apply_note_symbol_color_to_selection(self, color: str) -> None:
        start, end = self._note_color_target_range()
        if end <= start:
            return
        doc = self.note_text.document()
        changed = False
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    fp = frag.position()
                    fe = fp + frag.length()
                    if fe > start and fp < end:
                        cf = frag.charFormat()
                        if cf.isImageFormat():
                            img_fmt = cf.toImageFormat()
                            src = img_fmt.name()
                            m = re.match(r"aktionsicon:([^:]+):", src or "")
                            key = m.group(1) if m else (self.note_symbol_combo.currentData() if hasattr(self, "note_symbol_combo") else "punkt")
                            new_src = f"aktionsicon:{key}:{color.lstrip('#')}"
                            pix = self.icons.pixmap(str(key), color)
                            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(new_src), pix.toImage())
                            img_fmt.setName(new_src)
                            size = self._note_symbol_pixel_size()
                            img_fmt.setWidth(size)
                            img_fmt.setHeight(size)
                            try:
                                img_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignMiddle)
                            except Exception as exc:
                                log_debug("Stiller Fehler", exc)
                            c2 = QTextCursor(doc)
                            c2.setPosition(fp)
                            c2.setPosition(fe, QTextCursor.MoveMode.KeepAnchor)
                            c2.setCharFormat(img_fmt)
                            changed = True
                it += 1
            block = block.next()
        if changed:
            self._live_update_note()

    def _resize_note_symbols_to_font(self) -> None:
        doc = self.note_text.document()
        size = self._note_symbol_pixel_size()
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    cf = frag.charFormat()
                    if cf.isImageFormat():
                        img_fmt = cf.toImageFormat()
                        src = img_fmt.name()
                        if src.startswith("aktionsicon:"):
                            img_fmt.setWidth(size)
                            img_fmt.setHeight(size)
                            try:
                                img_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignMiddle)
                            except Exception as exc:
                                log_debug("Stiller Fehler", exc)
                            c2 = QTextCursor(doc)
                            c2.setPosition(frag.position())
                            c2.setPosition(frag.position() + frag.length(), QTextCursor.MoveMode.KeepAnchor)
                            c2.setCharFormat(img_fmt)
                it += 1
            block = block.next()

    def _insert_note_symbol(self) -> None:
        key = self.note_symbol_combo.currentData() if hasattr(self, "note_symbol_combo") else None
        if not key:
            return
        color = getattr(self, "note_symbol_color", self.canvas.current_color)
        src = f"aktionsicon:{key}:{str(color).lstrip('#')}"
        pix = self.icons.pixmap(str(key), color)
        try:
            self.note_text.document().addResource(QTextDocument.ResourceType.ImageResource, QUrl(src), pix.toImage())
            size = self._note_symbol_pixel_size()
            cursor = self.note_text.textCursor()
            # HTML-Einfügung verhindert, dass QTextEdit die Bildformatierung auf
            # die folgende Texteingabe vererbt. Das stabilisiert die Vorschau.
            cursor.insertHtml(
                f'<img src="{html.escape(src)}" width="{size}" height="{size}" '
                f'style="vertical-align:middle;">&nbsp;'
            )
            after_fmt = QTextCharFormat()
            after_fmt.setFontFamily("Arial")
            after_fmt.setFontPointSize(float(self.note_font.value()))
            if self.note_text_color:
                after_fmt.setForeground(QColor(self.note_text_color))
            try:
                after_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
            except Exception as exc:
                log_debug("Stiller Fehler", exc)
            self.note_text.setTextCursor(cursor)
            self.note_text.setCurrentCharFormat(after_fmt)
            self.note_text.mergeCurrentCharFormat(after_fmt)
        except Exception:
            self.note_text.insertPlainText(f"[{ICON_DATA.get(str(key), {}).get('label', key)}] ")
        self._live_update_note()

    def _restore_note_editor_base_format(self) -> None:
        try:
            fmt = QTextCharFormat()
            fmt.setFontFamily("Arial")
            fmt.setFontPointSize(float(self.note_font.value()))
            if getattr(self, "note_text_color", None):
                fmt.setForeground(QColor(self.note_text_color))
            cursor = self.note_text.textCursor()
            if not cursor.hasSelection():
                self.note_text.setCurrentCharFormat(fmt)
        except Exception as exc:
            log_debug("Stiller Fehler", exc)

    def _refresh_symbol_button_styles(self) -> None:
        for key, b in self.symbol_buttons.items():
            b.setIcon(QIcon(self.icons.pixmap(key, self.canvas.current_color)))
            border = "3px solid #00aaff" if key == self.canvas.current_symbol else "1px solid #555"
            b.setStyleSheet(f"border:{border}; background:#222;")

    def _refresh_color_button_styles(self) -> None:
        for c, b in self.color_buttons.items():
            border = "3px solid #00aaff" if c.lower() == self.canvas.current_color.lower() else "2px solid #333"
            b.setFixedSize(32, 32)
            b.setMinimumSize(32, 32)
            b.setMaximumSize(32, 32)
            b.setStyleSheet(f"background:{c}; border:{border}; border-radius: 0px; padding: 0px; min-width: 32px; min-height: 32px; max-width: 32px; max-height: 32px;")

    def _marker_selected(self, marker) -> None:
        self._refresh_marker_list()
        if marker is None:
            self.sel_info.setText("kein Punkt ausgewählt")
            return
        self._loading_selection = True
        self.sel_info.setText(f"Punkt {marker.id} - {marker.lat:.5f}, {marker.lon:.5f}")
        self.marker_label.setText("")
        self.marker_desc.setPlainText(marker.description or marker.label)
        self._set_combo_by_source(self.label_pos_combo, marker.label_position)
        self.label_w.setValue(marker.label_w)
        self.label_h.setValue(marker.label_h)
        self.label_gap.setValue(marker.label_gap)
        self.label_font.setValue(marker.label_font)
        self.marker_bold.setChecked(marker.label_bold)
        self.marker_italic.setChecked(marker.label_italic)
        self.marker_underline.setChecked(marker.label_underline)
        self.label_alpha.setValue(round(int(clamp(marker.label_bg_alpha, 0, 255)) * 100 / 255))
        self.marker_text_color = marker.text_color or "#000000"
        self._set_color_button_text(self.marker_text_color_btn, "Textfarbe:", self.marker_text_color)
        self.marker_text_color_btn.setStyleSheet(f"background:{self.marker_text_color}; color:#ffffff;")
        self.icon_size.setValue(marker.icon_size)
        self.canvas.current_symbol = marker.symbol
        self.canvas.current_color = marker.color
        self._refresh_symbol_button_styles()
        self._refresh_color_button_styles()
        self._loading_selection = False

    def _note_selected(self, note) -> None:
        self._refresh_note_list()
        if note is None:
            return
        self._loading_selection = True
        if hasattr(self, "note_name"):
            self.note_name.setText(getattr(note, "name", "") or f"Textfeld {note.id}")
        if note.text_html:
            self.note_text.setHtml(note.text_html)
        else:
            self.note_text.setPlainText(note.text)
        self._set_combo_by_source(self.note_pos, note.position)
        self.note_color = note.bg_color
        self._set_color_button_text(self.note_color_btn, "Füllfarbe:", self.note_color)
        self._style_color_button(self.note_color_btn, self.note_color)
        self.note_text_color = getattr(note, "text_color", "#000000") or "#000000"
        if not getattr(self, "note_selection_color", None):
            self.note_selection_color = self.note_text_color
        self._set_combo_by_source(self.note_align, getattr(note, "align", "Links"))
        self.note_alpha.setValue(round(int(clamp(getattr(note, "bg_alpha", 255), 0, 255)) * 100 / 255))
        self._set_color_button_text(self.note_text_color_btn, "Textfarbe:", self.note_text_color)
        self._style_color_button(self.note_text_color_btn, self.note_text_color)
        self.note_text.setTextColor(QColor(self.note_text_color))
        self.note_w.setValue(note.w)
        self.note_h.setValue(note.h)
        self.note_font.setValue(note.font)
        self.note_bold.setChecked(note.bold)
        self.note_italic.setChecked(note.italic)
        self.note_underline.setChecked(note.underline)
        if hasattr(self, "note_include_routes"):
            self.note_include_routes.setChecked(bool(getattr(note, "include_routes", False)))
        if hasattr(self, "note_visible"):
            self.note_visible.setChecked(bool(getattr(note, "visible", True)))
        self._loading_selection = False

    def apply_marker_values(self, show_message: bool = True) -> None:
        m = self.canvas.selected_marker()
        if not m:
            if show_message:
                QMessageBox.information(self, self._tr("Punkt"), self._tr("Bitte zuerst einen Punkt auswählen."))
            return
        self.canvas.update_selected_marker(
            label="",
            description=self.marker_desc.toPlainText(),
            label_position=self._combo_source(self.label_pos_combo),
            label_w=self.label_w.value(),
            label_h=self.label_h.value(),
            label_gap=self.label_gap.value(),
            label_font=self.label_font.value(),
            label_bold=self.marker_bold.isChecked(),
            label_italic=self.marker_italic.isChecked(),
            label_underline=self.marker_underline.isChecked(),
            label_bg_alpha=round(self.label_alpha.value() * 255 / 100),
            text_color=self.marker_text_color,
            icon_size=self.icon_size.value(),
            symbol=self.canvas.current_symbol,
            color=self.canvas.current_color,
        )
        self._refresh_marker_list()

    def new_note(self) -> None:
        # Legt immer ein weiteres Textfeld mit den Grundwerten an und wählt es aus.
        self.canvas.add_or_update_note(NoteBox(id=0, visible=True), update_existing=False)
        self._refresh_note_list()

    def add_or_update_note(self) -> None:
        # Gibt es schon Textfelder und ist keins gewählt, entsteht hier kein weiteres:
        # ein weiteres Textfeld legt nur „Neues Textfeld“ an. Das erste entsteht wie bisher.
        if self.canvas.notes and self.canvas.selected_note() is None and not self.canvas.selected_note_ids:
            self.statusBar().showMessage(self._tr("Kein Textfeld gewählt: bitte ein Textfeld auswählen oder „Neues Textfeld“ drücken."))
            return
        note = NoteBox(
            id=0,
            text=self.note_text.toPlainText(),
            text_html=self.note_text.toHtml(),
            position=self._combo_source(self.note_pos),
            bg_color=self.note_color,
            bg_alpha=round(self.note_alpha.value() * 255 / 100) if hasattr(self, "note_alpha") else 255,
            text_color=self.note_text_color,
            align=self._combo_source(self.note_align) if hasattr(self, "note_align") else "Links",
            w=self.note_w.value(),
            h=self.note_h.value(),
            font=self.note_font.value(),
            bold=self.note_bold.isChecked(),
            italic=self.note_italic.isChecked(),
            underline=self.note_underline.isChecked(),
            include_routes=self.note_include_routes.isChecked() if hasattr(self, "note_include_routes") else False,
            visible=self.note_visible.isChecked() if hasattr(self, "note_visible") else True,
            name=self.note_name.text().strip() if hasattr(self, "note_name") else "",
        )
        self.canvas.add_or_update_note(note, update_existing=True)
        self._refresh_note_list()

    # ---------- Additional UI helpers ----------
    def _search_zoom_changed(self, value: int) -> None:
        zoom = float(value) / 20.0
        if hasattr(self, "status_zoom_slider"):
            self.status_zoom_slider.blockSignals(True)
            self.status_zoom_slider.setValue(int(round(zoom * 20.0)))
            self.status_zoom_slider.blockSignals(False)
        if getattr(self, "search_results", None) and hasattr(self, "search_result_combo") and self.search_result_combo.currentIndex() >= 0:
            idx = self.search_result_combo.currentIndex()
            if idx < len(self.search_results):
                item = self.search_results[idx]
                self.canvas.center_on(item["lat"], item["lon"], zoom)
                return
        self.canvas.center_on(self.canvas.center_lat, self.canvas.center_lon, zoom)

    def _choose_title_bg_color(self) -> None:
        c = self._pick_color(self.title_bg_color, tr_text("Hintergrundfarbe wählen", self._current_lang()))
        if c.isValid():
            self.title_bg_color = c.name()
            self.canvas.title_bg_color = self.title_bg_color
            self._set_color_button_text(self.title_bg_color_btn, "Hintergrundfarbe:", self.title_bg_color)
            self.title_bg_color_btn.setStyleSheet(f"background:{self.title_bg_color}; color:#000;")
            self.canvas.update()

    def _choose_title_text_color(self) -> None:
        c = self._pick_color(self.title_text_color, tr_text("Textfarbe wählen", self._current_lang()))
        if c.isValid():
            self.title_text_color = c.name()
            self.canvas.title_text_color = self.title_text_color
            self._set_color_button_text(self.title_text_color_btn, "Textfarbe:", self.title_text_color)
            self.title_text_color_btn.setStyleSheet(f"background:{self.title_text_color}; color:#fff;")
            self.canvas.update()

    def _title_alpha_changed(self, value: int) -> None:
        self.canvas.title_bg_alpha = round(int(value) * 255 / 100)
        self.canvas.update()

    def _map_layer_changed(self, _text: str = "") -> None:
        layer = self._combo_source(self.map_layer_combo) if hasattr(self, "map_layer_combo") else "Standard"
        self.canvas.set_map_layer(layer)

    def _scale_toggled(self) -> None:
        self.canvas.show_scale = self.scale_box.isChecked()
        self.canvas.update()

    def _scale_position_changed(self) -> None:
        self.canvas.scale_position = self._combo_source(self.scale_pos_combo)
        self.canvas.update()

    def _scale_length_changed(self, value: int) -> None:
        self.canvas.scale_length_m = int(value)
        self.canvas.update()

    def _scale_opacity_changed(self, value: int) -> None:
        self.canvas.scale_alpha = round(int(value) * 255 / 100)
        self.canvas.update()

    def _refresh_marker_list(self) -> None:
        if not hasattr(self, "marker_combo"):
            return
        self.marker_combo.blockSignals(True)
        self.marker_combo.clear()
        self.marker_combo.addItem("--", None)
        for m in self.canvas.markers:
            text = (m.description or m.label or f"Punkt {m.id}").strip().splitlines()[0]
            self.marker_combo.addItem(f"{m.id}: {text}", m.id)
        if self.canvas.selected_marker_id is not None:
            for i in range(self.marker_combo.count()):
                if self.marker_combo.itemData(i) == self.canvas.selected_marker_id:
                    self.marker_combo.setCurrentIndex(i)
                    break
        self.marker_combo.blockSignals(False)

    def _marker_combo_changed(self) -> None:
        if not hasattr(self, "marker_combo"):
            return
        mid = self.marker_combo.currentData()
        if mid is None:
            return
        self.canvas.selected_marker_id = int(mid)
        self.canvas.markerSelected.emit(self.canvas.selected_marker())
        self.canvas.update()

    def _live_update_marker(self, *args) -> None:
        if getattr(self, "_loading_selection", False):
            return
        if self.canvas.selected_marker() is None:
            return
        self.canvas._restoring_history = True
        try:
            self.apply_marker_values(show_message=False)
        finally:
            self.canvas._restoring_history = False

    def _refresh_note_list(self) -> None:
        if not hasattr(self, "note_combo"):
            return
        self.note_combo.blockSignals(True)
        self.note_combo.clear()
        self.note_combo.addItem("--", None)
        for n in self.canvas.notes:
            note_name = getattr(n, "name", "") or f"Textfeld {n.id}"
            self.note_combo.addItem(f"{n.id}: {note_name}", n.id)
        if self.canvas.selected_note_id is not None:
            for i in range(self.note_combo.count()):
                if self.note_combo.itemData(i) == self.canvas.selected_note_id:
                    self.note_combo.setCurrentIndex(i)
                    break
        self.note_combo.blockSignals(False)

    def _note_combo_changed(self) -> None:
        nid = self.note_combo.currentData() if hasattr(self, "note_combo") else None
        if nid is None:
            return
        self.canvas.select_note_by_id(int(nid))

    def _refresh_route_list(self) -> None:
        if not hasattr(self, "route_combo"):
            return
        self.route_combo.blockSignals(True)
        self.route_combo.clear()
        self.route_combo.addItem("--", None)
        for r in self.canvas.routes:
            self.route_combo.addItem(f"{r.id}: {r.name}", r.id)
        if self.canvas.selected_route_id is not None:
            for i in range(self.route_combo.count()):
                if self.route_combo.itemData(i) == self.canvas.selected_route_id:
                    self.route_combo.setCurrentIndex(i)
                    break
        self.route_combo.blockSignals(False)

    def _route_combo_changed(self) -> None:
        rid = self.route_combo.currentData() if hasattr(self, "route_combo") else None
        if rid is None:
            return
        self.canvas.select_route_by_id(int(rid))

    def _route_selected(self, route) -> None:
        self._refresh_route_list()
        if route is None:
            if hasattr(self, "route_directions"):
                self.route_directions.clear()
            return
        if route is not None:
            self._loading_selection = True
            self.route_name.setText(route.name)
            self.route_color = route.color
            self._set_color_button_text(self.route_color_btn, "Farbe:", self.route_color)
            self.route_color_btn.setStyleSheet(f"background:{self.route_color}; color:#000;")
            self.route_width.setValue(int(route.width))
            if hasattr(self, "route_opacity"):
                self.route_opacity.setValue(int(getattr(route, "opacity", 80)))
            if getattr(route, "profile", "") and hasattr(self, "route_profile_combo"):
                self._set_combo_by_source(self.route_profile_combo, route.profile)
            if hasattr(self, "route_directions"):
                self.route_directions.setPlainText(getattr(route, "directions_text", "") or self._route_summary_text(route))
            self._loading_selection = False

    def _refresh_logo_list(self) -> None:
        if not hasattr(self, "logo_combo"):
            return
        self.logo_combo.blockSignals(True)
        self.logo_combo.clear()
        self.logo_combo.addItem("--", None)
        for logo in self.canvas.logos:
            self.logo_combo.addItem(f"{logo.id}: {logo.name}", logo.id)
        if self.canvas.selected_logo_id is not None:
            for i in range(self.logo_combo.count()):
                if self.logo_combo.itemData(i) == self.canvas.selected_logo_id:
                    self.logo_combo.setCurrentIndex(i)
                    break
        self.logo_combo.blockSignals(False)

    def _logo_combo_changed(self) -> None:
        lid = self.logo_combo.currentData() if hasattr(self, "logo_combo") else None
        if lid is None:
            return
        self.canvas.selected_logo_id = int(lid)
        self.canvas.logoSelected.emit(self.canvas.selected_logo())
        self.canvas.update()

    def _refresh_zone_list(self) -> None:
        if not hasattr(self, "zone_combo"):
            return
        self.zone_combo.blockSignals(True)
        self.zone_combo.clear()
        self.zone_combo.addItem("--", None)
        for z in self.canvas.zones:
            self.zone_combo.addItem(f"{z.id}: {z.name}", z.id)
        if self.canvas.selected_zone_id is not None:
            for i in range(self.zone_combo.count()):
                if self.zone_combo.itemData(i) == self.canvas.selected_zone_id:
                    self.zone_combo.setCurrentIndex(i)
                    break
        self.zone_combo.blockSignals(False)

    def _zone_combo_changed(self) -> None:
        zid = self.zone_combo.currentData() if hasattr(self, "zone_combo") else None
        if zid is None:
            return
        self.canvas.select_zone_by_id(int(zid))

    def _zone_selected(self, zone) -> None:
        self._refresh_zone_list()
        if zone is None:
            return
        self._loading_selection = True
        self.zone_name.setText(zone.name)
        self.zone_label.setPlainText(zone.label)
        self._set_combo_by_source(self.zone_label_pos, zone.label_position)
        self.zone_fill_color = zone.fill_color
        self._set_color_button_text(self.zone_fill_btn, "Füllfarbe:", self.zone_fill_color)
        self.zone_fill_btn.setStyleSheet(f"background:{self.zone_fill_color}; color:#000;")
        self.zone_alpha.setValue(round(int(clamp(zone.fill_alpha, 0, 255)) * 100 / 255))
        self.zone_border_color = zone.border_color
        self._set_color_button_text(self.zone_border_btn, "Konturfarbe:", self.zone_border_color)
        self.zone_border_btn.setStyleSheet(f"background:{self.zone_border_color}; color:#000;")
        self.zone_border_width.setValue(int(zone.border_width))
        self.zone_font.setValue(int(zone.label_font))
        self.zone_text_color = zone.text_color
        self._set_color_button_text(self.zone_text_color_btn, "Textfarbe:", self.zone_text_color)
        self.zone_text_color_btn.setStyleSheet(f"background:{self.zone_text_color}; color:#fff;")
        self.zone_label_bg_color = getattr(zone, "label_bg_color", "#ffffff") or "#ffffff"
        self._set_color_button_text(self.zone_label_bg_btn, "Hintergrundfarbe:", self.zone_label_bg_color)
        self.zone_label_bg_btn.setStyleSheet(f"background:{self.zone_label_bg_color}; color:#000;")
        self.zone_label_bg_alpha.setValue(round(int(clamp(getattr(zone, "label_bg_alpha", 180), 0, 255)) * 100 / 255))
        self.zone_bold.setChecked(zone.label_bold)
        self.zone_italic.setChecked(zone.label_italic)
        self.zone_underline.setChecked(zone.label_underline)
        self._loading_selection = False

    def _choose_zone_fill_color(self) -> None:
        c = self._pick_color(self.zone_fill_color, tr_text("Füllfarbe wählen", self._current_lang()))
        if c.isValid():
            self.zone_fill_color = c.name()
            self._set_color_button_text(self.zone_fill_btn, "Füllfarbe:", self.zone_fill_color)
            self.zone_fill_btn.setStyleSheet(f"background:{self.zone_fill_color}; color:#000;")
            self.canvas.current_zone_fill_color = self.zone_fill_color
            self._live_update_zone()

    def _choose_zone_border_color(self) -> None:
        c = self._pick_color(self.zone_border_color, tr_text("Konturfarbe wählen", self._current_lang()))
        if c.isValid():
            self.zone_border_color = c.name()
            self._set_color_button_text(self.zone_border_btn, "Konturfarbe:", self.zone_border_color)
            self.zone_border_btn.setStyleSheet(f"background:{self.zone_border_color}; color:#000;")
            self.canvas.current_zone_border_color = self.zone_border_color
            self._live_update_zone()

    def _choose_zone_text_color(self) -> None:
        c = self._pick_color(self.zone_text_color, tr_text("Textfarbe wählen", self._current_lang()))
        if c.isValid():
            self.zone_text_color = c.name()
            self._set_color_button_text(self.zone_text_color_btn, "Textfarbe:", self.zone_text_color)
            self.zone_text_color_btn.setStyleSheet(f"background:{self.zone_text_color}; color:#fff;")
            self._live_update_zone()

    def _choose_zone_label_bg_color(self) -> None:
        c = self._pick_color(self.zone_label_bg_color, tr_text("Hintergrundfarbe wählen", self._current_lang()))
        if c.isValid():
            self.zone_label_bg_color = c.name()
            self._set_color_button_text(self.zone_label_bg_btn, "Hintergrundfarbe:", self.zone_label_bg_color)
            self.zone_label_bg_btn.setStyleSheet(f"background:{self.zone_label_bg_color}; color:#000;")
            self._live_update_zone()

    def _live_update_zone(self, *args) -> None:
        if getattr(self, "_loading_selection", False):
            return
        self.canvas.current_zone_fill_color = self.zone_fill_color
        self.canvas.current_zone_fill_alpha = round(self.zone_alpha.value() * 255 / 100)
        self.canvas.current_zone_border_color = self.zone_border_color
        self.canvas.current_zone_border_width = int(self.zone_border_width.value())
        if self.canvas.selected_zone() is None:
            self.canvas.update()
            return
        self.canvas._restoring_history = True
        try:
            self.apply_zone_values(show_message=False)
        finally:
            self.canvas._restoring_history = False

    def save_zone_from_clicks(self) -> None:
        zone = self.canvas.add_zone(
            self.canvas.active_zone_points,
            self.zone_name.text() or f"Zone {self.canvas.next_zone_id}",
            self.zone_label.toPlainText(),
            self.zone_fill_color,
            round(self.zone_alpha.value() * 255 / 100),
            self.zone_border_color,
            self.zone_border_width.value(),
            self._combo_source(self.zone_label_pos),
            self.zone_label_bg_color,
            round(self.zone_label_bg_alpha.value() * 255 / 100),
            self.zone_text_color,
        )
        if not zone:
            QMessageBox.information(self, self._tr("Zone"), self._tr("Bitte mindestens drei Zonenpunkte setzen."))
        self._refresh_zone_list()

    def apply_zone_values(self, show_message: bool = True) -> None:
        if self.canvas.selected_zone() is None:
            if show_message:
                QMessageBox.information(self, self._tr("Zone"), self._tr("Bitte zuerst eine Zone auswählen."))
            return
        self.canvas.update_selected_zone(
            name=self.zone_name.text() or "Zone",
            label=self.zone_label.toPlainText(),
            label_position=self._combo_source(self.zone_label_pos),
            fill_color=self.zone_fill_color,
            fill_alpha=round(self.zone_alpha.value() * 255 / 100),
            border_color=self.zone_border_color,
            border_width=self.zone_border_width.value(),
            text_color=self.zone_text_color,
            label_font=self.zone_font.value(),
            label_bold=self.zone_bold.isChecked(),
            label_italic=self.zone_italic.isChecked(),
            label_underline=self.zone_underline.isChecked(),
            label_bg_color=self.zone_label_bg_color,
            label_bg_alpha=round(self.zone_label_bg_alpha.value() * 255 / 100),
        )
        self._refresh_zone_list()

    def _note_include_routes_changed(self, *args) -> None:
        if getattr(self, "_loading_selection", False):
            return
        # Diese Checkbox soll ohne zusätzlichen Klick auf „Feld aktualisieren“ sichtbar wirken.
        if self.canvas.selected_note() is None:
            if hasattr(self, "note_visible") and self.note_visible.isChecked():
                self.add_or_update_note()
            return
        try:
            self._note_live_timer.stop()
        except Exception as exc:
            log_debug("Stiller Fehler", exc)
        self._perform_live_update_note()

    def _note_visible_changed(self, *args) -> None:
        if getattr(self, "_loading_selection", False):
            return
        # Beim Einschalten sofort ein sichtbares Textfeld erzeugen, auch wenn noch keines ausgewählt ist.
        if self.note_visible.isChecked() and self.canvas.selected_note() is None:
            self.add_or_update_note()
            return
        self._live_update_note()

    def _live_update_note(self, *args) -> None:
        if getattr(self, "_loading_selection", False):
            return
        if self.canvas.selected_note() is None:
            return
        try:
            self._note_live_timer.start(220)
        except Exception:
            self._perform_live_update_note()

    def _perform_live_update_note(self) -> None:
        if getattr(self, "_loading_selection", False):
            return
        if self.canvas.selected_note() is None:
            return
        self.canvas._restoring_history = True
        try:
            self.add_or_update_note()
        finally:
            self.canvas._restoring_history = False

    # ---------- File actions ----------
    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", "aktionskarte.json", "Aktionskarten-Projekt (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            Path(path).write_text(json.dumps(self.canvas.project_state(), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, self._tr("Speichern"), f"{self._tr('Projekt konnte nicht gespeichert werden:')}\n{exc}")
            return
        self.statusBar().showMessage(f"{self._tr('Projekt gespeichert:')} {path}")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Projekt laden", "", "Aktionskarten-Projekt (*.json);;Alle Dateien (*)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, self._tr("Laden"), f"{self._tr('Projekt konnte nicht geladen werden:')}\n{exc}")
            return
        self.canvas.load_project_state(data)
        self._refresh_poi_filter_ui()
        self._set_combo_by_source(self.orientation_combo, self.canvas.orientation)
        self.map_title_edit.setText(self.canvas.map_title)
        self.title_bg_color = self.canvas.title_bg_color
        self._set_color_button_text(self.title_bg_color_btn, "Hintergrundfarbe:", self.title_bg_color)
        self.title_bg_color_btn.setStyleSheet(f"background:{self.title_bg_color}; color:#000;")
        self.title_text_color = getattr(self.canvas, "title_text_color", "#000000")
        self._set_color_button_text(self.title_text_color_btn, "Textfarbe:", self.title_text_color)
        self.title_text_color_btn.setStyleSheet(f"background:{self.title_text_color}; color:#fff;")
        self.title_alpha.setValue(round(int(clamp(self.canvas.title_bg_alpha, 0, 255)) * 100 / 255))
        self._set_combo_by_source(self.paper_size_combo, self.canvas.paper_size)
        self.border_width.setValue(int(self.canvas.border))
        self._set_combo_by_source(self.density_combo, self.canvas.grid_density)
        self.grid_box.setChecked(self.canvas.show_grid)
        self.grid_lines_box.setChecked(self.canvas.show_grid_lines)
        self._set_combo_by_source(self.map_layer_combo, self.canvas.map_layer)
        self.scale_box.setChecked(self.canvas.show_scale)
        self._set_combo_by_source(self.scale_pos_combo, self.canvas.scale_position)
        self.scale_length.setValue(int(self.canvas.scale_length_m))
        if hasattr(self, "scale_opacity"):
            self.scale_opacity.setValue(round(int(clamp(getattr(self.canvas, "scale_alpha", 255), 0, 255)) * 100 / 255))
        self.search_zoom_slider.setValue(int(round(float(self.canvas.zoom) * 20.0)))
        if hasattr(self, "route_profile_combo"):
            self._set_combo_by_source(self.route_profile_combo, getattr(self.canvas, "current_route_profile", "Fuß-Route"))
        self._refresh_marker_list(); self._refresh_route_list(); self._refresh_logo_list(); self._refresh_zone_list(); self._refresh_note_list()
        self.statusBar().showMessage(f"{self._tr('Projekt geladen:')} {path}")

    def reset_project(self) -> None:
        # Eigene Knöpfe: die Standardknöpfe von Qt bleiben sonst englisch (Yes/No).
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(self._tr("Zurücksetzen"))
        box.setText(self._tr("Aktuelle Punkte und Textfelder wirklich löschen?"))
        ja_btn = box.addButton(self._tr("Ja"), QMessageBox.ButtonRole.YesRole)
        nein_btn = box.addButton(self._tr("Nein"), QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(nein_btn)
        box.setEscapeButton(nein_btn)
        box.exec()
        if box.clickedButton() is ja_btn:
            self.canvas.reset_project()
            self._refresh_poi_filter_ui()
            self._set_combo_by_source(self.paper_size_combo, self.canvas.paper_size)
            self._set_combo_by_source(self.orientation_combo, self.canvas.orientation)
            self.map_title_edit.setText(self.canvas.map_title)
            self.title_bg_color = self.canvas.title_bg_color
            self._set_color_button_text(self.title_bg_color_btn, "Hintergrundfarbe:", self.title_bg_color)
            self.title_bg_color_btn.setStyleSheet(f"background:{self.title_bg_color}; color:#000;")
            self.title_text_color = self.canvas.title_text_color
            self._set_color_button_text(self.title_text_color_btn, "Textfarbe:", self.title_text_color)
            self.title_text_color_btn.setStyleSheet(f"background:{self.title_text_color}; color:#fff;")
            self.title_alpha.setValue(0)
            self.border_width.setValue(int(self.canvas.border))
            self._set_combo_by_source(self.density_combo, self.canvas.grid_density)
            self.grid_box.setChecked(self.canvas.show_grid)
            self.grid_lines_box.setChecked(self.canvas.show_grid_lines)
            self._set_combo_by_source(self.map_layer_combo, self.canvas.map_layer)
            self.scale_box.setChecked(self.canvas.show_scale)
            self._set_combo_by_source(self.scale_pos_combo, self.canvas.scale_position)
            self.scale_length.setValue(int(self.canvas.scale_length_m))
            if hasattr(self, "scale_opacity"):
                self.scale_opacity.setValue(round(int(clamp(getattr(self.canvas, "scale_alpha", 255), 0, 255)) * 100 / 255))
            self.search_zoom_slider.setValue(int(round(float(self.canvas.zoom) * 20.0)))
            if hasattr(self, "route_profile_combo"):
                self._set_combo_by_source(self.route_profile_combo, getattr(self.canvas, "current_route_profile", "Fuß-Route"))
            self._refresh_marker_list(); self._refresh_route_list(); self._refresh_logo_list(); self._refresh_zone_list(); self._refresh_note_list()

    def _undo(self) -> None:
        self.canvas.undo()
        self._refresh_controls_from_canvas()

    def _redo(self) -> None:
        self.canvas.redo()
        self._refresh_controls_from_canvas()

    def _refresh_controls_from_canvas(self) -> None:
        # Rückgängig/Wiederholen stellt die Inhalte wieder her (Punkte, Texte, Bilder, Routen,
        # Zonen, Titel). Die Bedienfelder müssen danach denselben Stand zeigen. Währenddessen
        # wird nichts neu gemerkt.
        self.canvas._restoring_history = True
        try:
            self._refresh_poi_filter_ui()
            self._set_combo_by_source(self.orientation_combo, self.canvas.orientation)
            self.map_title_edit.setText(self.canvas.map_title)
            self.title_bg_color = self.canvas.title_bg_color
            self._set_color_button_text(self.title_bg_color_btn, "Hintergrundfarbe:", self.title_bg_color)
            self.title_bg_color_btn.setStyleSheet(f"background:{self.title_bg_color}; color:#000;")
            self.title_text_color = getattr(self.canvas, "title_text_color", "#000000")
            self._set_color_button_text(self.title_text_color_btn, "Textfarbe:", self.title_text_color)
            self.title_text_color_btn.setStyleSheet(f"background:{self.title_text_color}; color:#fff;")
            self.title_alpha.setValue(round(int(clamp(self.canvas.title_bg_alpha, 0, 255)) * 100 / 255))
            self._set_combo_by_source(self.paper_size_combo, self.canvas.paper_size)
            self.border_width.setValue(int(self.canvas.border))
            self._set_combo_by_source(self.density_combo, self.canvas.grid_density)
            self.grid_box.setChecked(self.canvas.show_grid)
            self.grid_lines_box.setChecked(self.canvas.show_grid_lines)
            self._set_combo_by_source(self.map_layer_combo, self.canvas.map_layer)
            self.scale_box.setChecked(self.canvas.show_scale)
            self._set_combo_by_source(self.scale_pos_combo, self.canvas.scale_position)
            self.scale_length.setValue(int(self.canvas.scale_length_m))
            if hasattr(self, "scale_opacity"):
                self.scale_opacity.setValue(round(int(clamp(getattr(self.canvas, "scale_alpha", 255), 0, 255)) * 100 / 255))
            self.search_zoom_slider.setValue(int(round(float(self.canvas.zoom) * 20.0)))
            if hasattr(self, "route_profile_combo"):
                self._set_combo_by_source(self.route_profile_combo, getattr(self.canvas, "current_route_profile", "Fuß-Route"))
            self._refresh_marker_list(); self._refresh_route_list(); self._refresh_logo_list(); self._refresh_zone_list(); self._refresh_note_list()
        except Exception as exc:
            log_debug("Bedienfelder konnten nicht nachgezogen werden", exc)
        finally:
            self.canvas._restoring_history = False
        self.canvas.update_status()
        self.canvas.update()

    def retry_tiles(self) -> None:
        if bool(getattr(self.canvas, "vector_mode", False)) and hasattr(self, "map_container"):
            self.map_container.reload_vector_map()
        else:
            self.canvas.tiles.retry_failed()
        self.canvas.update()
        self.statusBar().showMessage(tr_text("Map wird neu geladen...", self._current_lang()))

    def _scrubbed_jpg_image(self, img: QImage) -> QImage:
        clean = QImage(img.size(), QImage.Format.Format_RGB32)
        clean.fill(QColor("#ffffff"))
        p = QPainter(clean)
        p.drawImage(0, 0, img)
        p.end()
        return clean

    def _scrub_pdf_metadata(self, path: str) -> None:
        try:
            from pypdf import PdfReader, PdfWriter
            src = Path(path)
            tmp = src.with_suffix(src.suffix + ".tmp")
            reader = PdfReader(str(src))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata({
                "/Title": "",
                "/Author": "",
                "/Subject": "",
                "/Keywords": "",
                "/Creator": "unknown",
                "/Producer": "unknown",
                "/CreationDate": FIXED_PDF_DATE,
                "/ModDate": FIXED_PDF_DATE,
            })
            with tmp.open("wb") as fh:
                writer.write(fh)
            tmp.replace(src)
        except Exception as exc:
            log_debug("PDF-Metadaten konnten nicht vollständig bereinigt werden", exc)

    def _render_export_image(self, width: int, height: int) -> Optional[QImage]:
        if bool(getattr(self.canvas, "vector_mode", False)):
            if not bool(getattr(self.canvas, "vector_preview", False)) or not hasattr(self, "map_container"):
                QMessageBox.warning(self, self._tr("Export"), self._tr("Die Vektor-Ansicht ist nicht verfügbar. Der Export wurde abgebrochen, damit keine andere Karte gespeichert wird."))
                return None
            pw, ph = self.canvas.page_size()
            mr = self.canvas.map_rect()
            map_w = max(64, int(round(width * mr.width() / pw)))
            map_h = max(64, int(round(height * mr.height() / ph)))
            base = self.map_container.capture_map_image(map_w, map_h)
            if base is None or base.isNull():
                QMessageBox.warning(self, self._tr("Export"), self._tr("Die Vektorkarte konnte nicht erfasst werden. Der Export wurde abgebrochen, damit keine andere Karte gespeichert wird."))
                return None
            return self.canvas.render_to_image(width, height, base_map_image=base)
        return self.canvas.render_to_image(width, height)

    def export_jpg(self) -> None:
        self.canvas.deselect_all()
        paper = self.canvas.paper_size if self.canvas.paper_size in PAGE_EXPORTS else "A4"
        title = f"JPG {paper} exportieren"
        default_name = f"aktionskarte_{paper.lower()}.jpg"
        path, _ = QFileDialog.getSaveFileName(self, title, default_name, "JPEG-Bild (*.jpg *.jpeg)")
        if not path:
            return
        if not path.lower().endswith((".jpg", ".jpeg")):
            path += ".jpg"
        w, h = PAGE_EXPORTS[paper][self.canvas.orientation]
        rendered = self._render_export_image(w, h)
        if rendered is None:
            return
        img = self._scrubbed_jpg_image(rendered)
        ok = img.save(path, "JPG", 95)
        if ok:
            self.statusBar().showMessage(f"JPG {paper} {self._tr('exportiert:')} {path}")
        else:
            QMessageBox.critical(self, self._tr("Export"), self._tr("JPG konnte nicht gespeichert werden."))

    def export_pdf(self) -> None:
        self.canvas.deselect_all()
        paper = self.canvas.paper_size if self.canvas.paper_size in PAGE_EXPORTS else "A4"
        title = f"PDF {paper} exportieren"
        default_name = f"aktionskarte_{paper.lower()}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, title, default_name, "PDF-Datei (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        w, h = PAGE_EXPORTS[paper][self.canvas.orientation]
        img = self._render_export_image(w, h)
        if img is None:
            return
        try:
            writer = QPdfWriter(path)
            try:
                writer.setCreator("unknown")
                writer.setTitle("")
                for method, value in (("setAuthor", ""), ("setSubject", ""), ("setKeywords", "")):
                    if hasattr(writer, method):
                        getattr(writer, method)(value)
            except Exception as exc:
                log_debug("PDF-Basismetadaten konnten nicht gesetzt werden", exc)
            writer.setResolution(300)
            writer.setPageSize(QPageSize(PAGE_EXPORTS[paper]["pdf"]))
            writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
            if self.canvas.orientation == "Querformat":
                writer.setPageOrientation(QPageLayout.Orientation.Landscape)
            else:
                writer.setPageOrientation(QPageLayout.Orientation.Portrait)
            painter = QPainter(writer)
            rect = QRectF(0, 0, writer.width(), writer.height())
            painter.drawImage(rect, img)
            painter.end()
            self._scrub_pdf_metadata(path)
        except Exception as exc:
            QMessageBox.critical(self, self._tr("Export"), f"{self._tr('PDF konnte nicht gespeichert werden:')}\n{exc}")
            return
        self.statusBar().showMessage(f"PDF {paper} {self._tr('exportiert:')} {path}")

    def cleanup_on_exit(self) -> None:
        try:
            self.canvas.tiles.clear_disk_cache()
        except Exception as exc:
            log_debug("Aufräumen beim Schließen fehlgeschlagen", exc)

    def closeEvent(self, event) -> None:
        self.cleanup_on_exit()
        super().closeEvent(event)


def _dunkle_systemdialoge() -> None:
    # Native Windows-Dateidialoge kommen in Qt sonst hell (uxtheme Ordinal 135,
    # SetPreferredAppMode(2)). Muss vor dem ersten Fenster laufen.
    if sys.platform != "win32":
        return
    try:
        import ctypes
        set_mode = ctypes.WinDLL("uxtheme")[135]
        set_mode.argtypes = [ctypes.c_int]
        set_mode.restype = ctypes.c_int
        set_mode(2)
    except Exception as exc:
        log_debug("Dunkle Systemdialoge konnten nicht gesetzt werden", exc)


def _eigene_taskleisten_gruppe() -> None:
    # Ohne eigene Kennung ordnet Windows das Fenster pythonw.exe zu und zeigt in der
    # Taskleiste nicht das Programmsymbol. Muss vor dem ersten Fenster laufen.
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_NAME)
    except Exception as exc:
        log_debug("Taskleisten-Kennung konnte nicht gesetzt werden", exc)


def main() -> int:
    print(f"Starte {APP_NAME} {APP_VERSION}")
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception as exc:
        log_debug("Stiller Fehler", exc)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(theme.QSS)
    _dunkle_systemdialoge()
    _eigene_taskleisten_gruppe()
    window = MainWindow()
    app.setWindowIcon(window.windowIcon())
    app.aboutToQuit.connect(window.cleanup_on_exit)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
