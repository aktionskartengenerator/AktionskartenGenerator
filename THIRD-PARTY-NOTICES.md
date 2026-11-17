# Third-party notices / Hinweise zu Fremdanteilen

AktionskartenGenerator itself is licensed under GPL-3.0-or-later (see `LICENSE`).
The parts below belong to their respective authors and keep their own licenses.

AktionskartenGenerator selbst steht unter GPL-3.0-or-later (siehe `LICENSE`).
Die folgenden Teile gehören ihren jeweiligen Urheber*innen und behalten ihre eigenen Lizenzen.

Source code of AktionskartenGenerator / Quelltext von AktionskartenGenerator:
https://github.com/aktionskartengenerator/AktionskartenGenerator

## Included in this repository / In diesem Repository enthalten

| Component | Version | License | Where |
|---|---|---|---|
| MapLibre GL JS | 6.18.0 | BSD-3-Clause (plus the notices listed in the license file) | `App/maplibre/`, full text in `App/maplibre/LICENSE.txt` |

## Installed by pip, not included / Von pip installiert, nicht enthalten

| Component | Version | License | Source |
|---|---|---|---|
| PySide6 (Qt for Python), incl. Qt and Qt WebEngine | 6.12.0 | LGPL-3.0-only or GPL (Qt WebEngine contains Chromium with further open-source licenses) | https://pypi.org/project/PySide6/ |
| pypdf | 7.1.0 | BSD-3-Clause | https://pypi.org/project/pypdf/ |

The exact license texts ship inside the installed packages.
Die genauen Lizenztexte liegen in den installierten Paketen.

## Included in the installers / In den Installern enthalten

The installers (Windows setup, Linux `.deb`) bundle the following parts in unmodified form.
The license texts are in the folder `Lizenzen` of the installed program
(Windows: program folder; Linux: `/usr/share/doc/aktionskartengenerator/Lizenzen`).

Die Installer (Windows-Setup, Linux-`.deb`) enthalten die folgenden Teile unverändert.
Die Lizenztexte liegen im Ordner `Lizenzen` des installierten Programms
(Windows: Programmordner; Linux: `/usr/share/doc/aktionskartengenerator/Lizenzen`).

| Component | License | License text | Source |
|---|---|---|---|
| AktionskartenGenerator | GPL-3.0-or-later | `LICENSE.txt` | see above / siehe oben |
| Qt 6.12 and PySide6 / Shiboken6 6.12.0 (Qt for Python) | LGPL-3.0-only | `LGPL-3.0.txt`, `LICENSE.txt` (GPL-3.0) | https://code.qt.io/pyside/pyside-setup · https://download.qt.io/official_releases/QtForPython/pyside6/ · https://download.qt.io/official_releases/qt/ |
| Qt WebEngine (contains Chromium) | LGPL-3.0-only for the Qt parts; Chromium parts under various licenses, the most restrictive being LGPL-2.1 | `LGPL-3.0.txt`, `LGPL-2.1.txt`; full third-party list: https://doc.qt.io/qt-6/qtwebengine-licensing.html | as Qt / wie Qt |
| MapLibre GL JS 6.18.0 | BSD-3-Clause | `MapLibre-LICENSE.txt` | https://github.com/maplibre/maplibre-gl-js |
| pypdf 7.1.0 | BSD-3-Clause | `pypdf-LICENSE.txt` | https://pypi.org/project/pypdf/ |
| Python runtime | PSF-2.0 | `Python-LICENSE.txt` | https://www.python.org/ |

The Qt libraries are separate files inside the program folder (`_internal`) and can be replaced
by your own builds of the same version, as the LGPL requires.

Die Qt-Bibliotheken liegen als einzelne Dateien im Programmordner (`_internal`) und lassen sich
durch eigene Builds derselben Version ersetzen, wie es die LGPL verlangt.

## Online services and map data / Online-Dienste und Kartendaten

The program loads map data at runtime; nothing of it is part of this repository.
Das Programm lädt Kartendaten zur Laufzeit; nichts davon ist Teil dieses Repositories.

| Service | Used for | Host |
|---|---|---|
| OpenStreetMap Nominatim | place search / Ortssuche | nominatim.openstreetmap.org |
| OpenStreetMap tile server | raster tiles "Standard" | tile.openstreetmap.org |
| CyclOSM (OpenStreetMap France) | raster tiles "Fahrrad" | tile-cyclosm.openstreetmap.fr |
| Humanitarian style (OpenStreetMap France) | raster tiles "Humanitär" | tile.openstreetmap.fr |
| FOSSGIS routing | routes / Routen | routing.openstreetmap.de |
| OSRM demo server | routes, fallback / Ausweich | router.project-osrm.org |
| OpenFreeMap | vector view / Vektor-Ansicht | tiles.openfreemap.org |

Map data © OpenStreetMap contributors, available under the Open Database License (ODbL).
Each service has its own usage policy; please respect it.

Kartendaten © OpenStreetMap-Mitwirkende, verfügbar unter der Open Database License (ODbL).
Jeder Dienst hat eigene Nutzungsregeln; bitte halte sie ein.
