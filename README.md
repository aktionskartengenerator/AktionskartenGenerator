# AktionskartenGenerator

[Deutsch](#deutsch) · [English](#english)

## Deutsch

AktionskartenGenerator ist ein Programm für Windows und Linux, mit dem du Aktionskarten erstellst:
Kartenausschnitt wählen, eigene Inhalte darauflegen, als JPG oder PDF ausgeben.

### Funktionen

- Kartenansicht als Raster oder Vektor, mehrere Kartenebenen
- Ortssuche
- Symbol-Punkte, Routen (mit Wegbeschreibung), Zonen, Bilddateien
- Titel, Legende und Textfelder
- Gitter, Rand und Maßstab
- Projekt speichern und laden
- Export als JPG oder PDF in A3, A4, A5, Hoch- und Querformat
- Oberfläche in Deutsch und Englisch

### Start aus dem Quelltext

Voraussetzung: Python 3.10 oder neuer (64 Bit) und Internet für die erste Einrichtung.

- **Windows:** `Start.bat` doppelklicken.
- **Linux:** `bash start.sh` im Projektordner. Unter Mint/Ubuntu vorher `sudo apt install python3-venv`.

Beim ersten Start entsteht im Projektordner die virtuelle Umgebung `.venv`, und die Pakete aus
`App/requirements.txt` werden installiert. Das dauert einige Minuten. Danach startet das Programm direkt.

Erscheint das Programm nicht, zeigt dieser Aufruf die Fehlermeldung:

- Windows: `.venv\Scripts\python.exe App\AktionskartenGenerator.py`
- Linux: `.venv/bin/python App/AktionskartenGenerator.py`

### Online-Dienste und Datenschutz

Ortssuche, Kartenkacheln, Routenberechnung und die Vektor-Ansicht brauchen Internet. Dabei gehen
der Suchtext, die betrachteten Kartenausschnitte sowie Start-, Ziel- und Zwischenpunkte von Routen
an die Dienste, die in `THIRD-PARTY-NOTICES.md` aufgelistet sind – zusammen mit deiner IP-Adresse.
Das Programm startet in der Vektor-Ansicht und spricht OpenFreeMap deshalb ab Programmstart an.

Bei sensiblen Orten nutze ein VPN oder Tor: dann sehen die Dienste nicht deine eigene IP-Adresse;
die Anfragen selbst (Orte, Ausschnitte, Routen) sehen sie weiterhin.

Projekt-, JPG- und PDF-Dateien liegen nur dort, wo du sie speicherst. Der Kachel-Cache wird beim
Beenden und beim Programmstart geleert.

### Installer selbst bauen

- Linux-Paket (`.deb`): `bash Build/build_deb.sh` auf Ubuntu 24.04 / Linux Mint 22 mit Python 3.12.
- Windows-Setup: `bash Build/build_wine.sh <python-laufzeit.zip>` unter Linux mit Wine und NSIS.
  Die Kopfzeilen des Skripts beschreiben die Voraussetzungen.

Tests liegen in `Build/Tests/`.

Fertige Installer für Windows und Linux findest du unter „Releases“. `Info_Win.txt` und
`Info_Linux.txt` sind die Begleittexte dieser Installer.

### Lizenz

GPL-3.0-or-later, siehe `LICENSE`. Fremdanteile und ihre Lizenzen stehen in `THIRD-PARTY-NOTICES.md`.

Copyright © AktionskartenGenerator contributors

## English

AktionskartenGenerator is a program for Windows and Linux for creating action maps:
choose a map section, place your own content on it, export as JPG or PDF.

### Features

- Map view as raster or vector, several map layers
- Place search
- Symbol points, routes (with directions), zones, image files
- Title, legend and text boxes
- Grid, border and scale
- Save and load projects
- Export as JPG or PDF in A3, A4, A5, portrait and landscape
- Interface in German and English

### Running from source

Requirements: Python 3.10 or newer (64-bit) and internet access for the first setup.

- **Windows:** double-click `Start.bat`.
- **Linux:** run `bash start.sh` in the project folder. On Mint/Ubuntu install `python3-venv` first:
  `sudo apt install python3-venv`.

The first start creates the virtual environment `.venv` in the project folder and installs the
packages from `App/requirements.txt`. This takes a few minutes. After that the program starts directly.

If the program does not appear, this call shows the error message:

- Windows: `.venv\Scripts\python.exe App\AktionskartenGenerator.py`
- Linux: `.venv/bin/python App/AktionskartenGenerator.py`

### Online services and privacy

Place search, map tiles, routing and the vector view need internet access. The search text, the map
sections you look at and the start, end and via points of routes are sent to the services listed in
`THIRD-PARTY-NOTICES.md` – together with your IP address. The program starts in the vector view and
therefore contacts OpenFreeMap as soon as it starts.

For sensitive places use a VPN or Tor: the services then do not see your own IP address; they still
see the requests themselves (places, map sections, routes).

Project, JPG and PDF files are stored only where you save them. The tile cache is cleared when the
program exits and when it starts.

### Building the installers

- Linux package (`.deb`): `bash Build/build_deb.sh` on Ubuntu 24.04 / Linux Mint 22 with Python 3.12.
- Windows setup: `bash Build/build_wine.sh <python-runtime.zip>` on Linux with Wine and NSIS.
  The header of the script describes the requirements.

Tests are in `Build/Tests/`.

Ready-made installers for Windows and Linux are available under “Releases”. `Info_Win.txt` and
`Info_Linux.txt` are the texts that accompany these installers (German).

### License

GPL-3.0-or-later, see `LICENSE`. Third-party parts and their licenses are listed in
`THIRD-PARTY-NOTICES.md`.

Copyright © AktionskartenGenerator contributors
