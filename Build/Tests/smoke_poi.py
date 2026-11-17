# -*- coding: utf-8 -*-
r"""
Smoke-Test POI-Filter ohne Bildschirm und ohne Internet.

Die Kartenseite bekommt selbst erzeugte Vektor-Kacheln und die echten Filterregeln der
POI-Ebenen des Stils OpenFreeMap Liberty (Stand 14.11.2026). Geprueft wird, welche POIs je
Filtereinstellung uebrig bleiben.

Aufruf:  python Build\Tests\smoke_poi.py
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parents[1] / "App"))
sys.path.insert(0, str(HIER))

import mvt_testkachel as mvt  # noqa: E402
import AktionskartenGenerator as akg  # noqa: E402
import theme  # noqa: E402
from PySide6.QtCore import QBuffer, QByteArray, QEventLoop, QIODevice, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

LIBERTY_POI_FILTER = json.loads(r"""{"poi_r20": ["all", ["match", ["geometry-type"], ["MultiPoint", "Point"], true, false], [">=", ["get", "rank"], 20]], "poi_r7": ["all", ["match", ["geometry-type"], ["MultiPoint", "Point"], true, false], [">=", ["get", "rank"], 7], ["<", ["get", "rank"], 20]], "poi_r1": ["all", ["match", ["geometry-type"], ["MultiPoint", "Point"], true, false], [">=", ["get", "rank"], 1], ["<", ["get", "rank"], 7]], "poi_transit": ["match", ["get", "class"], ["airport", "bus", "rail"], true, false]}""")

LIBERTY_POI_MINZOOM = {"poi_r20": 17, "poi_r7": 16, "poi_r1": 15, "poi_transit": None}

POIS = [
    (1000, 1000, {"class": "school", "subclass": "school", "rank": 3, "name": "Schule"}),
    (2000, 1000, {"class": "restaurant", "subclass": "restaurant", "rank": 3, "name": "Lokal"}),
    (3000, 1000, {"class": "fountain", "subclass": "fountain", "rank": 3, "name": "Brunnen"}),
    (1500, 2000, {"class": "shop", "subclass": "florist", "rank": 12, "name": "Blumen"}),
    (2500, 2000, {"class": "bus", "rank": 25, "name": "Halt"}),
]
ALLE = ["Blumen", "Brunnen", "Halt", "Lokal", "Schule"]
FEHLER = []


def pruef(name, ist, soll):
    ok = ist == soll
    print(("OK   " if ok else "FEHL ") + name + ("" if ok else f"  ist {ist}  soll {soll}"), flush=True)
    if not ok:
        FEHLER.append(name)


def warte(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def js(win, code):
    out = {}
    loop = QEventLoop()
    win.map_container.web.page().runJavaScript(code, lambda v: (out.setdefault("v", v), loop.quit()))
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    return out.get("v")


def minzoom(win):
    info = json.loads(js(win, "window.aktionsPoiInfo ? window.aktionsPoiInfo() : '{}'") or "{}")
    return {k: v.get("minzoom") for k, v in info.items()}


def namen(win):
    info = json.loads(js(win, "window.aktionsPoiInfo ? window.aktionsPoiInfo() : '{}'") or "{}")
    alle = set()
    for eintrag in info.values():
        if not isinstance(eintrag["names"], list):
            return [str(eintrag["names"])]
        if eintrag["visibility"] != "none":
            alle |= set(eintrag["names"])
    return sorted(alle)


def main():
    if not akg.HAS_WEBENGINE:
        print("QtWebEngine fehlt - Test uebersprungen")
        return 0
    original = akg.MapLibreSchemeHandler.requestStarted

    def request_started(self, job):
        if job.requestUrl().path().lstrip("/").startswith("tiles/"):
            buf = QBuffer(job)
            buf.setData(QByteArray(mvt.tile(POIS)))
            buf.open(QIODevice.OpenModeFlag.ReadOnly)
            job.reply(b"application/x-protobuf", buf)
            return
        original(self, job)

    akg.MapLibreSchemeHandler.requestStarted = request_started
    ebenen = []
    for k, f in LIBERTY_POI_FILTER.items():
        ebene = {"id": k, "type": "symbol", "source": "openmaptiles", "source-layer": "poi", "filter": f, "layout": {"text-size": 12}}
        if LIBERTY_POI_MINZOOM.get(k) is not None:
            ebene["minzoom"] = LIBERTY_POI_MINZOOM[k]
        ebenen.append(ebene)
    akg.MAPLIBRE_STYLES["Standard"] = {
        "version": 8,
        "sources": {"openmaptiles": {"type": "vector", "tiles": ["akg://karte/tiles/{z}/{x}/{y}.pbf"], "minzoom": 0, "maxzoom": 14}},
        "layers": [{"id": "bg", "type": "background", "paint": {"background-color": "#ffffff"}}] + ebenen,
    }
    # Vorbelegung ist die Kartenebene Fahrrad: sie bekommt im Test denselben Stil.
    akg.MAPLIBRE_STYLES["Fahrrad"] = akg.MAPLIBRE_STYLES["Standard"]
    # Kartenebene ohne POI-Ebenen (wie Positron/Humanitaer)
    akg.MAPLIBRE_STYLES["Humanitär"] = {
        "version": 8,
        "sources": {"openmaptiles": {"type": "vector", "tiles": ["akg://karte/tiles/{z}/{x}/{y}.pbf"], "minzoom": 0, "maxzoom": 14}},
        "layers": [{"id": "bg", "type": "background", "paint": {"background-color": "#eeeeee"}}],
    }

    app = QApplication(sys.argv)
    app.setStyleSheet(theme.QSS)
    win = akg.MainWindow()
    win.resize(1900, 1050)
    win.show()
    warte(300)
    win.canvas.center_on(50.9795, 11.3295, 14.6)
    warte(200)
    typ = win.poi_category_checkboxes

    # Vorbelegung eines neuen Projekts: Vektor, Kartenebene Fahrrad, POI-Filter ein.
    vorbelegt = ["Halt", "Lokal", "Schule"]
    for _ in range(40):
        warte(250)
        if namen(win) == vorbelegt:
            break
    pruef("Vorbelegung: Vektor, Fahrrad, Filter ein", (win.canvas.vector_mode, win.canvas.map_layer, win._combo_source(win.map_layer_combo), win.poi_filter_checkbox.isChecked()), (True, "Fahrrad", "Fahrrad", True))
    pruef("Vorbelegung: Typen", sorted(k for k, box in typ.items() if box.isChecked()), ["accommodation", "education", "food", "health", "public", "transit"])
    pruef("Vorbelegung: Namen und Symbole an", (win.poi_names_checkbox.isChecked(), win.poi_icons_checkbox.isChecked()), (True, True))
    pruef("Vorbelegung: Regler ganz links", (win.poi_zoom_slider.value(), win.poi_zoom_slider.minimum()), (-8, -8))
    pruef("Vorbelegung: gezeigte POIs", namen(win), vorbelegt)
    pruef("Vorbelegung: Mindest-Zoom vier Stufen frueher", minzoom(win), {k: (v - 4 if v is not None else None) for k, v in LIBERTY_POI_MINZOOM.items()})
    pruef("Typ heisst Religioes", typ["religious"].text(), "Religiös")

    # Ab hier der Stand, von dem die folgenden Pruefungen ausgehen: Standard, Filter aus, alle Typen, Regler 0.
    win._set_combo_by_source(win.map_layer_combo, "Standard")
    win.poi_zoom_slider.setValue(0)
    for box in typ.values():
        box.setChecked(True)
    win.poi_filter_checkbox.setChecked(False)
    for _ in range(40):
        warte(250)
        if namen(win) == ALLE:
            break

    pruef("ohne Filter: alle POIs", namen(win), ALLE)
    win.poi_filter_checkbox.setChecked(True); warte(700)
    pruef("Filter an, alle Typen: alle POIs", namen(win), ALLE)
    typ["education"].setChecked(False); warte(700)
    pruef("ohne Bildung", namen(win), ["Blumen", "Brunnen", "Halt", "Lokal"])
    typ["other"].setChecked(False); warte(700)
    pruef("ohne Bildung und Sonstige (Halt ist OEPNV)", namen(win), ["Blumen", "Halt", "Lokal"])
    typ["transit"].setChecked(False); warte(700)
    pruef("ohne Bildung, Sonstige und OEPNV", namen(win), ["Blumen", "Lokal"])
    typ["transit"].setChecked(True); warte(700)
    typ["other"].setChecked(True); warte(700)
    pruef("Sonstige wieder an", namen(win), ["Blumen", "Brunnen", "Halt", "Lokal"])
    typ["education"].setChecked(True); warte(700)
    pruef("Bildung wieder an", namen(win), ALLE)
    for box in typ.values():
        box.setChecked(False)
    warte(700)
    pruef("alle Typen aus", namen(win), [])
    typ["food"].setChecked(True); warte(700)
    pruef("nur Gastronomie", namen(win), ["Lokal"])
    # Regler "POIs ab Zoom": verschiebt den Mindest-Zoom der Rangstufen, Ebenen ohne Mindest-Zoom bleiben.
    vorgabe = {k: v for k, v in LIBERTY_POI_MINZOOM.items()}
    soll = dict(vorgabe)
    pruef("Mindest-Zoom Vorgabe", minzoom(win), soll)
    win.poi_zoom_slider.setValue(-4); warte(700)
    pruef("POIs ab Zoom: zwei Stufen frueher", minzoom(win), {k: (v - 2 if v is not None else None) for k, v in vorgabe.items()})
    pruef("Anzeige am Regler ohne Vorgabe-Hinweis", "(" in win.poi_zoom_value_label.text(), False)
    win.poi_filter_checkbox.setChecked(False); warte(700)
    pruef("Filter aus: alle POIs", namen(win), ALLE)
    pruef("Filter aus: Mindest-Zoom wieder Vorgabe", minzoom(win), soll)
    win.poi_filter_checkbox.setChecked(True); warte(300)
    win.poi_zoom_slider.setValue(0); warte(300)

    # Kartenebene ohne POIs sperrt den Filter, mit POIs gibt sie ihn wieder frei.
    win._set_combo_by_source(win.map_layer_combo, "Humanitär")
    for _ in range(30):
        warte(250)
        if win.canvas.vector_poi_layers == 0:
            break
    pruef("Kartenebene ohne POIs: Filter gesperrt", (win.canvas.vector_poi_layers, win.poi_filter_checkbox.isEnabled(), win.poi_options_widget.isVisibleTo(win)), (0, False, False))
    win._set_combo_by_source(win.map_layer_combo, "Standard")
    for _ in range(30):
        warte(250)
        if win.canvas.vector_poi_layers > 0:
            break
    pruef("Kartenebene mit POIs: Filter wieder frei", (win.canvas.vector_poi_layers > 0, win.poi_filter_checkbox.isEnabled()), (True, True))

    # "Map neu laden" in der Vektor-Ansicht laedt den Stil neu.
    win.retry_tiles()
    pruef("Map neu laden: Stil laedt neu", win.canvas.vector_poi_layers in (-1, 4), True)
    for _ in range(30):
        warte(250)
        if win.canvas.vector_poi_layers > 0 and namen(win) == ALLE:
            break
    win.poi_filter_checkbox.setChecked(False); warte(500)
    pruef("nach Neuladen: alle POIs", namen(win), ALLE)

    win.close()
    warte(200)
    print("\nErgebnis:", "alle gruen" if not FEHLER else "FEHLER: " + ", ".join(FEHLER), flush=True)
    return 1 if FEHLER else 0


if __name__ == "__main__":
    sys.exit(main())
