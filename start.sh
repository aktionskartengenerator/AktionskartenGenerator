#!/usr/bin/env bash
# Startet AktionskartenGenerator aus dem Quellordner. Aufruf: bash start.sh
cd "$(dirname "$0")" || exit 1
HIER="$(pwd)"
VENV="$HIER/.venv"
MARK="$VENV/.folder"

# Verschobenes oder von Windows kopiertes Projekt: .venv passt nicht und wird neu angelegt.
if [ -d "$VENV" ] && { [ ! -x "$VENV/bin/python" ] || [ ! -f "$MARK" ] || [ "$(cat "$MARK")" != "$HIER" ]; }; then
    echo "[AktionskartenGenerator] .venv gehoert zu einem anderen Ordner - wird neu angelegt ..."
    rm -rf "$VENV"
fi

if [ ! -d "$VENV" ]; then
    echo "[AktionskartenGenerator] Erste Einrichtung: virtuelle Umgebung wird angelegt ..."
    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 nicht gefunden. Bitte Python 3.10 oder neuer installieren."
        exit 1
    fi
    if ! python3 -m venv "$VENV"; then
        echo "Virtuelle Umgebung konnte nicht angelegt werden. Unter Mint/Ubuntu fehlt meist: sudo apt install python3-venv"
        rm -rf "$VENV"
        exit 1
    fi
    "$VENV/bin/python" -m pip install --upgrade pip
    if ! "$VENV/bin/python" -m pip install -r "$HIER/App/requirements.txt"; then
        echo "Installation der Pakete fehlgeschlagen."
        rm -rf "$VENV"
        exit 1
    fi
    printf '%s\n' "$HIER" > "$MARK"
fi

nohup "$VENV/bin/python" "$HIER/App/AktionskartenGenerator.py" >/dev/null 2>&1 &
