# Contributing / Mitmachen

[Deutsch](#deutsch) · [English](#english)

## Deutsch

Schön, dass du mitmachen willst. Jede Hilfe ist willkommen – Fehlermeldungen, Wünsche, Texte, Code.

### Fehler melden und Wünsche äußern

- Lege ein Issue an und nutze das passende Formular („Fehler melden“ oder „Wunsch“).
- Schau vorher kurz, ob es das Issue schon gibt.
- Nenne Version, Betriebssystem und die Schritte, mit denen sich der Fehler nachstellen lässt.
- Achte darauf, keine sensiblen Orte, Routen oder Projektdateien zu veröffentlichen. Das Debug-Log
  des Quelltext-Betriebs enthält Suchbegriffe und Koordinaten – vor dem Anhängen durchsehen.
- Sicherheitslücken bitte nicht als Issue, sondern wie in `SECURITY.md` beschrieben melden.

### Code beitragen

1. Repository forken und einen eigenen Branch anlegen.
2. Programm aus dem Quelltext starten (siehe `README.md`).
3. Änderung klein und auf ein Thema begrenzt halten.
4. Tests laufen lassen: die Skripte in `Build/Tests/` (`smoke_start.py`, `smoke_poi.py`).
5. Pull Request öffnen und kurz beschreiben, was sich ändert und warum.

Bitte beachte:

- Die Oberfläche bleibt dunkel; Farben kommen aus `App/theme.py`.
- Texte der Oberfläche gibt es in Deutsch und Englisch – beide Sprachen zusammen ändern.
- MapLibre wird nur aus lokalen Dateien geladen, kein CDN.
- Keine neuen Online-Dienste ohne vorherige Absprache in einem Issue; jeder Dienst gehört in die
  Info-Dateien und in `THIRD-PARTY-NOTICES.md`.
- Neue Abhängigkeiten brauchen eine Lizenz, die zu GPL-3.0-or-later passt.

### Lizenz der Beiträge

Mit deinem Beitrag stimmst du zu, dass er unter GPL-3.0-or-later steht, wie das gesamte Projekt.

## English

Thanks for wanting to help. Every contribution is welcome – bug reports, requests, texts, code.

### Reporting bugs and requesting features

- Open an issue and use the matching form (“Report a bug” or “Request”).
- Check briefly whether the issue already exists.
- State the version, the operating system and the steps to reproduce the bug.
- Take care not to publish sensitive places, routes or project files. The debug log written when
  running from source contains search terms and coordinates – review it before attaching.
- Please do not report security vulnerabilities as an issue; follow `SECURITY.md` instead.

### Contributing code

1. Fork the repository and create your own branch.
2. Run the program from source (see `README.md`).
3. Keep the change small and limited to one topic.
4. Run the tests: the scripts in `Build/Tests/` (`smoke_start.py`, `smoke_poi.py`).
5. Open a pull request and describe briefly what changes and why.

Please note:

- The interface stays dark; colours come from `App/theme.py`.
- Interface texts exist in German and English – change both languages together.
- MapLibre is loaded from local files only, no CDN.
- No new online services without prior discussion in an issue; every service must be listed in
  the info files and in `THIRD-PARTY-NOTICES.md`.
- New dependencies need a license compatible with GPL-3.0-or-later.

### License of contributions

By contributing you agree that your contribution is licensed under GPL-3.0-or-later, like the
whole project.
