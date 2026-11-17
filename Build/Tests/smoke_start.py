# -*- coding: utf-8 -*-
r"""
Smoke-Test ohne Bildschirm: Start, Umschalter Raster | Vektor, POI-Filter, Export, Projektstand.

Aufruf:  python Build\Tests\smoke_start.py        (Linux/Cloud: xvfb nicht noetig)
Der Test schreibt nur in einen temporaeren Ordner und loescht ihn wieder.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = Path(__file__).resolve().parents[2] / "App"
sys.path.insert(0, str(APP))

import AktionskartenGenerator as akg  # noqa: E402
import theme  # noqa: E402
from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

FEHLER = []


def pruef(name, bedingung, info=""):
    print(("OK   " if bedingung else "FEHL ") + name + (f"  [{info}]" if info else ""), flush=True)
    if not bedingung:
        FEHLER.append(name)


def warte(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def js(win, code, ms=3000):
    out = {"v": None}
    loop = QEventLoop()

    def fertig(v):
        out["v"] = v
        loop.quit()

    win.map_container.web.page().runJavaScript(code, fertig)
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    return out["v"]


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(akg.APP_NAME)
    app.setStyleSheet(theme.QSS)
    win = akg.MainWindow()
    win.show()
    warte(300)

    pruef("Fenstertitel", win.windowTitle() == f"{akg.APP_NAME} {akg.APP_VERSION}", win.windowTitle())
    pruef("Version 2.9", akg.APP_VERSION == "2.9")
    # Kachel-Cache: Reste eines frueheren Laufs werden beim Start geloescht.
    cache_ordner = Path(win.canvas.tiles.network.cache().cacheDirectory())
    cache_ordner.mkdir(parents=True, exist_ok=True)
    (cache_ordner / "rest_vom_absturz.bin").write_bytes(b"x")
    akg.TileManager()
    pruef("Kachel-Cache wird beim Start geleert", not (cache_ordner / "rest_vom_absturz.bin").exists())
    pruef("MapLibre-Dateien vorhanden", not akg.maplibre_files_missing(), str(akg.maplibre_files_missing()))
    vektor = bool(win.canvas.vector_preview)
    pruef("Vektor-Ansicht verfuegbar", vektor)
    pruef("Start in Vektor", win.canvas.vector_mode is vektor and win.map_mode_vector_btn.isChecked() is vektor
          and win.map_mode_raster_btn.isChecked() is (not vektor))
    pruef("Start mit Kartenebene Fahrrad", win.canvas.map_layer == "Fahrrad" and win._combo_source(win.map_layer_combo) == "Fahrrad"
          and win.canvas.tiles.layer == "Fahrrad", f"{win.canvas.map_layer} / {win._combo_source(win.map_layer_combo)} / {win.canvas.tiles.layer}")
    pruef("Start mit POI-Vorbelegung", win.canvas.poi_show_names and win.canvas.poi_show_icons
          and win.canvas.poi_categories_enabled == {"education", "health", "food", "public", "transit", "accommodation"}
          and win.canvas.poi_zoom_offset == -4.0, f"{sorted(win.canvas.poi_categories_enabled)} {win.canvas.poi_zoom_offset}")
    if vektor:
        pruef("Start: POI-Filter ein", win.canvas.poi_filter_enabled is True and win.poi_filter_checkbox.isChecked())
        win.map_mode_raster_btn.click()
        pruef("Raster: POI-Filter gesperrt", win.canvas.vector_mode is False and not win.poi_filter_checkbox.isEnabled())
        # Die Kartenebene gehoert zur Kartenart: Raster beginnt mit Standard, Vektor mit Fahrrad.
        def ebene():
            return (win.canvas.map_layer, win._combo_source(win.map_layer_combo), win.canvas.tiles.layer)
        pruef("Erstes Umschalten auf Raster: Standard", ebene() == ("Standard",) * 3, str(ebene()))
        win._set_combo_by_source(win.map_layer_combo, "Humanitär")
        win.map_mode_vector_btn.click()
        pruef("Vektor behaelt Fahrrad", ebene() == ("Fahrrad",) * 3, str(ebene()))
        win.map_mode_raster_btn.click()
        pruef("Raster behaelt eigene Ebene", ebene() == ("Humanitär",) * 3, str(ebene()))
        ui = win.canvas.project_state()["ui"]
        pruef("Projektstand: Ebene je Kartenart", (ui["map_layer"], ui["map_layer_raster"], ui["map_layer_vector"]) == ("Humanitär", "Humanitär", "Fahrrad"))
        alt = win.canvas.project_state()
        del alt["ui"]["map_layer_raster"], alt["ui"]["map_layer_vector"]
        win.canvas.load_project_state(alt)
        win._refresh_poi_filter_ui()
        pruef("Projekt ohne die neuen Felder", win.canvas.map_layers == {"raster": "Humanitär", "vector": "Fahrrad"} and ebene() == ("Humanitär",) * 3, str(win.canvas.map_layers))
        win._set_combo_by_source(win.map_layer_combo, "Standard")
        win.map_mode_vector_btn.click()
        pruef("Umschalten auf Vektor", win.canvas.vector_mode is True and win.map_mode_vector_btn.isChecked())
        pruef("POI-Filter in Vektor bedienbar", win.poi_filter_checkbox.isEnabled())
        zustand = None
        for _ in range(60):
            warte(250)
            zustand = js(win, "window.aktionsMapSet ? 'bereit' : 'wartet'")
            if zustand == "bereit":
                break
        pruef("MapLibre aus lokalen Dateien geladen", zustand == "bereit", str(zustand))
        grund = js(win, "getComputedStyle(document.body).backgroundColor + '|' + getComputedStyle(document.getElementById('map')).backgroundColor")
        pruef("Kartenseite: dunkle Grundfarbe", grund == "rgb(22, 24, 29)|rgb(22, 24, 29)"
              and win.map_container.web.page().backgroundColor().name() == "#16181d", str(grund))
        # Raster und Vektor muessen deckungsgleich sein: dieselben Koordinaten landen in der
        # Vektorkarte auf demselben Bildschirmpunkt wie in der Raster-Rechnung des Programms.
        import json as _json
        win.canvas.center_on(50.9795, 11.3295, 16.9)
        warte(1500)
        skala, _ox, _oy = win.canvas.page_transform()
        rahmen = win.canvas.map_rect()
        groesste = 0.0
        for lat, lon in ((50.9795, 11.3295), (50.9830, 11.3200), (50.9760, 11.3400)):
            seite = win.canvas.latlon_to_page(lat, lon)
            soll = ((seite.x() - rahmen.left()) * skala, (seite.y() - rahmen.top()) * skala)
            ist = _json.loads(js(win, f"window.aktionsProject({lon}, {lat})") or "[1e9, 1e9]")
            groesste = max(groesste, abs(ist[0] - soll[0]), abs(ist[1] - soll[1]))
        pruef("Raster und Vektor deckungsgleich", groesste < 1.5, f"groesste Abweichung {groesste:.2f} px")
        win.poi_filter_checkbox.setChecked(True)
        pruef("POI-Filter aktiv", win.canvas.poi_filter_enabled is True and win.poi_options_widget.isVisibleTo(win))
        bild = win._render_export_image(1240, 877)
        pruef("Export-Bild Vektor", bild is not None and not bild.isNull(), "" if bild is None else f"{bild.width()}x{bild.height()}")

        stand = win.canvas.project_state() if hasattr(win.canvas, "project_state") else None
        if stand is not None:
            pruef("Kartenart im Projektstand", stand.get("ui", {}).get("vector_mode") is True)

        win.map_mode_raster_btn.click()
        pruef("Zurueck auf Raster", win.canvas.vector_mode is False and not win.poi_filter_checkbox.isEnabled())

    bild = win._render_export_image(1240, 877)
    pruef("Export-Bild Raster", bild is not None and not bild.isNull())

    tmp = Path(tempfile.mkdtemp(prefix="akg_smoke_"))
    try:
        jpg = tmp / "test.jpg"
        pdf = tmp / "test.pdf"
        original = akg.QFileDialog.getSaveFileName
        try:
            akg.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(jpg), ""))
            win.export_jpg()
            akg.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(pdf), ""))
            win.export_pdf()
        finally:
            akg.QFileDialog.getSaveFileName = original
        pruef("JPG exportiert", jpg.is_file() and jpg.stat().st_size > 1000)
        pruef("PDF exportiert", pdf.is_file() and pdf.stat().st_size > 1000)
        if pdf.is_file():
            from pypdf import PdfReader
            meta = PdfReader(str(pdf)).metadata or {}
            pruef("PDF-Metadaten neutral",
                  meta.get("/Creator") == "unknown" and meta.get("/Producer") == "unknown"
                  and not meta.get("/Author") and not meta.get("/Title")
                  and meta.get("/CreationDate") == akg.FIXED_PDF_DATE,
                  str(dict(meta)))
    finally:
        for f in tmp.glob("*"):
            f.unlink()
        tmp.rmdir()

    # Rueckgaengig/Wiederholen betrifft nur Inhalte; Kartenausschnitt und Einstellungen bleiben.
    c = win.canvas
    c.undo_stack.clear(); c.redo_stack.clear()
    win._set_combo_by_source(win.paper_size_combo, "A4")
    warte(50)
    c.remember()                      # Stand 0: Titel leer, kein Punkt
    c.map_title = "Test"
    c.remember()                      # Stand 1: Titel "Test"
    c.add_marker_from_controls(50.98, 11.33)
    punkte = len(c.markers)
    win._set_combo_by_source(win.paper_size_combo, "A3")
    c.center_on(50.9795, 11.3295, 15.0)
    c.remember()                      # derselbe Inhalt: darf keinen leeren Schritt ergeben
    if c.vector_preview:
        win.map_mode_raster_btn.click()
    art = bool(c.vector_mode)
    win._undo()
    warte(100)
    pruef("Rueckgaengig: Punkt weg, Titel bleibt", len(c.markers) == punkte - 1 and c.map_title == "Test", f"{len(c.markers)} {c.map_title!r}")
    pruef("Rueckgaengig: Ausschnitt bleibt", abs(c.center_lat - 50.9795) < 1e-6 and abs(c.center_lon - 11.3295) < 1e-6 and abs(c.zoom - 15.0) < 1e-6,
          f"{c.center_lat} {c.center_lon} {c.zoom}")
    pruef("Rueckgaengig: Einstellungen bleiben", c.paper_size == "A3" and win._combo_source(win.paper_size_combo) == "A3"
          and bool(c.vector_mode) == art and win.map_mode_vector_btn.isChecked() == art, f"{c.paper_size} {c.vector_mode}")
    win._undo()
    warte(100)
    pruef("Rueckgaengig: Titel weg, Feld passt", c.map_title == "" and win.map_title_edit.text() == "", repr(c.map_title))
    win._undo()
    pruef("Rueckgaengig: nichts mehr da, nichts passiert", c.map_title == "" and c.paper_size == "A3")
    win._redo()
    win._redo()
    warte(100)
    pruef("Wiederholen: Titel und Punkt wieder da", c.map_title == "Test" and win.map_title_edit.text() == "Test" and len(c.markers) == punkte,
          f"{c.map_title!r} {len(c.markers)}")
    pruef("Wiederholen: Einstellungen bleiben", c.paper_size == "A3" and bool(c.vector_mode) == art)

    # Zuruecksetzen: Knoepfe in der gewaehlten Sprache, danach die Vorbelegung.
    knoepfe = []
    original_exec = akg.QMessageBox.exec
    akg.QMessageBox.exec = lambda box: knoepfe.append([b.text() for b in box.buttons()]) or 0
    try:
        win.reset_project()
        win.language_combo.setCurrentIndex(1)
        win.reset_project()
        win.language_combo.setCurrentIndex(0)
    finally:
        akg.QMessageBox.exec = original_exec
    pruef("Zuruecksetzen: Ja/Nein und Yes/No", knoepfe == [["Ja", "Nein"], ["Yes", "No"]], str(knoepfe))
    pruef("Zuruecksetzen ohne Ja aendert nichts", c.map_title == "Test")
    c.reset_project()
    win._refresh_poi_filter_ui()
    pruef("Zuruecksetzen: Vorbelegung", c.map_layer == "Fahrrad" and bool(c.vector_mode) == bool(c.vector_preview)
          and c.poi_categories_enabled == {"education", "health", "food", "public", "transit", "accommodation"}
          and c.poi_zoom_offset == -4.0 and c.map_title == "" and not c.markers, f"{c.map_layer} {c.vector_mode}")
    win.map_mode_raster_btn.click()

    # Wegbeschreibung kopieren
    win.route_directions.setPlainText("Wegbeschreibung\nLaenge: 1 km")
    win._copy_route_directions()
    pruef("Wegbeschreibung kopiert", QApplication.clipboard().text() == "Wegbeschreibung\nLaenge: 1 km", repr(QApplication.clipboard().text()))

    # Textfelder: Auswahl "Bestehende Textfelder" und Name
    pruef("Haken heisst Routen Legende hinzufuegen", win.note_include_routes.text() == "Routen Legende hinzufügen", win.note_include_routes.text())
    win.note_name.setText("")
    win.note_visible.setChecked(True)
    warte(50)
    erstes = c.selected_note_id
    pruef("Textfeld angelegt und in der Liste", len(c.notes) == 1 and win.note_combo.count() == 2
          and win.note_combo.currentText() == f"{erstes}: Textfeld {erstes}" and win.note_name.text() == f"Textfeld {erstes}",
          f"{win.note_combo.currentText()!r} {win.note_name.text()!r}")
    win.note_name.setText("Legende")
    warte(400)
    pruef("Textfeld umbenannt", c.notes[0].name == "Legende" and win.note_combo.currentText() == f"{erstes}: Legende", win.note_combo.currentText())
    c.select_note_by_id(None)
    pruef("Keine Auswahl: Liste zeigt --", win.note_combo.currentIndex() == 0)
    # Gibt es schon ein Textfeld und ist keins gewaehlt, legen die alten Wege kein weiteres an.
    win.note_visible.setChecked(False)
    win.note_visible.setChecked(True)
    win.add_or_update_note()
    win.note_include_routes.setChecked(not win.note_include_routes.isChecked())
    warte(50)
    pruef("Alte Wege legen kein weiteres Textfeld an", len(c.notes) == 1 and "Neues Textfeld" in win.statusBar().currentMessage(), f"{len(c.notes)} {win.statusBar().currentMessage()!r}")
    win.new_note()
    pruef("Zweites Textfeld in der Liste", len(c.notes) == 2 and win.note_combo.count() == 3, f"{len(c.notes)} {win.note_combo.count()}")
    # Position Zentriert: waagerecht und senkrecht mittig im Kartenrahmen
    win._set_combo_by_source(win.note_pos, "Zentriert")
    warte(400)
    feld, rahmen = c._note_rect(c.selected_note()), c.map_rect()
    pruef("Position Zentriert", c.selected_note().position == "Zentriert" and abs(feld.center().x() - rahmen.center().x()) < 0.01
          and abs(feld.center().y() - rahmen.center().y()) < 0.01, f"{c.selected_note().position} {feld.center()} {rahmen.center()}")
    win.note_combo.setCurrentIndex(1)
    pruef("Auswahl in der Liste waehlt das Textfeld", c.selected_note_id == erstes and win.note_name.text() == "Legende", f"{c.selected_note_id} {win.note_name.text()!r}")
    stand = c.project_state()
    c.load_project_state(stand)
    pruef("Name im Projektstand", [n.name for n in c.notes][0] == "Legende")
    c.delete_selected_note() if c.selected_note_id else None
    c.notes.clear(); c.selected_note_id = None; win._refresh_note_list()

    # Knopf "Neues Textfeld" und Reihenfolge der Zeilen: Liste, Knopf, Name, Position
    vorher_n = len(c.notes)
    win.new_note()
    win.new_note()
    pruef("Neues Textfeld legt je eines an", len(c.notes) == vorher_n + 2 and c.selected_note_id == c.notes[-1].id
          and win.note_name.text() == f"Textfeld {c.notes[-1].id}" and win.note_combo.currentData() == c.notes[-1].id,
          f"{len(c.notes)} {win.note_name.text()!r}")
    formular = win.note_name.parentWidget().layout()
    zeilen = [formular.getWidgetPosition(w)[0] for w in (win.note_combo, win.note_name, win.note_pos)]
    pruef("Zeilen: Liste, Knopf, Name, Position", zeilen[1] == zeilen[0] + 2 and zeilen[2] == zeilen[1] + 1, str(zeilen))
    c.notes.clear(); c.selected_note_id = None; win._refresh_note_list()

    # Berechnungsart einer berechneten Route aendern: rechnet an Ort und Stelle neu (ohne Netz, Antwort nachgestellt).
    import json as _json2
    class Antwort:
        def __init__(self, daten, eig):
            self._d, self._e = daten, eig
        def property(self, name):
            return self._e.get(name)
        def readAll(self):
            return self._d
        def error(self):
            return akg.QNetworkReply.NetworkError.NoError
        def errorString(self):
            return ""
        def deleteLater(self):
            pass
    route = c.add_route([(50.98, 11.33), (50.982, 11.34)], "Weg", "#ff0505", 6, calculated=True,
                        control_points=[(50.98, 11.33), (50.982, 11.34)])
    route.profile = "Fuß-Route"
    c.select_route_by_id(route.id)
    anfragen = []
    echt = win._request_route
    win._request_route = lambda coords, profile, attempt, replace_id=0: anfragen.append((coords, profile, attempt, replace_id))
    try:
        pruef("Route waehlen zeigt ihre Berechnungsart, ohne zu rechnen", win._combo_source(win.route_profile_combo) == "Fuß-Route" and not anfragen, str(anfragen))
        c.active_route_points.append((50.0, 11.0))
        win._set_combo_by_source(win.route_profile_combo, "PKW-Route")
        pruef("Neue Routenpunkte gesetzt: keine Neuberechnung", not anfragen, str(anfragen))
        c.active_route_points.clear()
        win._set_combo_by_source(win.route_profile_combo, "Fahrrad-Route")
        pruef("Berechnungsart geaendert: Anfrage fuer dieselbe Route", anfragen == [("11.3300000,50.9800000;11.3400000,50.9820000", "Fahrrad-Route", 0, route.id)], str(anfragen))
    finally:
        win._request_route = echt
    antwort = _json2.dumps({"routes": [{"geometry": {"coordinates": [[11.33, 50.98], [11.335, 50.981], [11.34, 50.982]]}, "distance": 1234.0, "duration": 300.0, "legs": []}]}).encode("utf-8")
    anzahl = len(c.routes)
    win._route_finished(Antwort(antwort, {"route_coords": "11.3300000,50.9800000;11.3400000,50.9820000", "route_profile": "Fahrrad-Route", "route_attempt": 0, "route_replace_id": route.id}))
    neu = c.selected_route()
    pruef("Neu berechnet an Ort und Stelle", len(c.routes) == anzahl and neu is not None and neu.id == route.id and neu.name == "Weg"
          and neu.profile == "Fahrrad-Route" and len(neu.points) == 3 and abs(neu.distance_m - 1234.0) < 1e-6,
          f"{len(c.routes)} {getattr(neu, 'profile', None)} {len(getattr(neu, 'points', []))}")
    stand = c.project_state()
    pruef("Berechnungsart im Projektstand", stand["routes"][-1].get("profile") == "Fahrrad-Route")
    win._undo()
    alt_r = next((r for r in c.routes if r.id == route.id), None)
    pruef("Rueckgaengig holt die alte Route", alt_r is not None and len(alt_r.points) == 2 and alt_r.profile == "Fuß-Route", str(alt_r and (len(alt_r.points), alt_r.profile)))
    c.routes.clear(); c.selected_route_id = None; win._refresh_route_list()

    # Meldungen in der gewaehlten Sprache
    win.language_combo.setCurrentIndex(1)
    pruef("Meldungstexte englisch", (win._tr("Bitte zuerst eine Zone auswählen."), win._tr("Projekt gespeichert:")) == ("Please select a zone first.", "Project saved:"))
    win.language_combo.setCurrentIndex(0)

    # Suchergebnis: Auswahl im Klappmenue springt direkt zum Ort.
    win.search_results = [
        {"name": "Ort A", "lat": 48.1372, "lon": 11.5756},
        {"name": "Ort B", "lat": 53.5511, "lon": 9.9937},
    ]
    win.search_result_combo.clear()
    win.search_result_combo.addItems(["Ort A", "Ort B"])
    vorher = (round(win.canvas.center_lat, 3), round(win.canvas.center_lon, 3))
    pruef("Liste fuellen springt nicht", (round(win.canvas.center_lat, 3), round(win.canvas.center_lon, 3)) == vorher)
    win.search_result_combo.setCurrentIndex(1)
    win.search_result_combo.activated.emit(1)
    warte(100)
    pruef("Auswahl springt zum Ort", abs(win.canvas.center_lat - 53.5511) < 0.01 and abs(win.canvas.center_lon - 9.9937) < 0.01,
          f"{win.canvas.center_lat:.3f} {win.canvas.center_lon:.3f}")
    pruef("Shortbread entfernt", "Shortbread" not in akg.MAP_LAYERS and "Shortbread" not in akg.MAPLIBRE_STYLES
          and win.map_layer_combo.findText("Shortbread") < 0)

    for sprache in (1, 0):
        win.language_combo.setCurrentIndex(sprache)
        warte(50)
    pruef("Sprachwechsel DE/EN/DE", win.map_mode_vector_btn.text() == "Vektor", win.map_mode_vector_btn.text())

    win.close()
    warte(200)
    print("\nErgebnis:", "alle gruen" if not FEHLER else "FEHLER: " + ", ".join(FEHLER), flush=True)
    return 1 if FEHLER else 0


if __name__ == "__main__":
    sys.exit(main())
