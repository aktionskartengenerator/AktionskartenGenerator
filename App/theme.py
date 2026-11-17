# -*- coding: utf-8 -*-
"""
Palette und Stylesheet der Oberflaeche.

Einzige Stelle fuer Farben der Bedienoberflaeche. Farben, die Karteninhalt sind
(Symbole, Routen, Zonen, Titel, Legende), gehoeren nicht hierher.
"""

GRUND = "#16181d"
FLAECHE = "#1b1e24"
RAHMEN = "#262a32"
TEXT = "#d7dae0"
NEBENTEXT = "#aab2bf"
AKZENT = "#8ab4f8"
AUSWAHL = "#2b3a55"

OK = "#98c379"
WARN = "#d19a66"
ERR = "#e06c75"
IDLE = "#6b7280"

QSS = f"""
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog, QMessageBox, QColorDialog {{ background: {GRUND}; }}

QToolBar {{ background: {FLAECHE}; border: 0; border-bottom: 1px solid {RAHMEN}; spacing: 8px; padding: 5px; }}
QToolButton {{ color: {TEXT}; background: {FLAECHE}; border: 1px solid {RAHMEN}; border-radius: 4px; padding: 3px 10px; min-height: 18px; }}
QToolButton:hover {{ border-color: {AKZENT}; }}
QToolButton:pressed {{ background: {AUSWAHL}; }}
QToolButton:disabled {{ color: {IDLE}; border-color: {GRUND}; }}

QStatusBar {{ background: {FLAECHE}; color: {NEBENTEXT}; border-top: 1px solid {RAHMEN}; min-height: 22px; }}
QStatusBar QLabel {{ color: {NEBENTEXT}; }}

QDockWidget {{ background: {GRUND}; color: {TEXT}; titlebar-close-icon: none; titlebar-normal-icon: none; }}
QWidget#toolsRoot {{ background: {GRUND}; }}

QToolBox {{ background: {GRUND}; border: 0; }}
QToolBox > QWidget {{ background: {GRUND}; }}
QToolBox::tab {{
    background: {FLAECHE};
    color: {TEXT};
    border: 1px solid {RAHMEN};
    border-radius: 4px;
    padding: 0 12px;
    min-height: 42px;
    height: 42px;
    font-weight: bold;
}}
QToolBox::tab:hover {{ border-color: {AKZENT}; }}
QToolBox::tab:selected {{ background: {AUSWAHL}; color: {AKZENT}; border-color: {AKZENT}; }}

QScrollArea {{ background: {GRUND}; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: {GRUND}; }}

QGroupBox {{
    background: {FLAECHE};
    border: 1px solid {RAHMEN};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 14px;
    font-weight: bold;
    color: {AKZENT};
}}
QGroupBox#ohneTitel {{ margin-top: 0px; padding-top: 4px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; top: 0px; padding: 0 4px; }}

QLabel {{ background: transparent; color: {TEXT}; min-height: 18px; }}
QLabel[hint="true"] {{ color: {NEBENTEXT}; font-size: 12px; font-weight: bold; margin: 0px; padding: 0px; }}
QCheckBox {{ background: transparent; color: {TEXT}; min-height: 22px; }}
QCheckBox:disabled {{ color: {IDLE}; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {NEBENTEXT}; border-radius: 3px; background: {FLAECHE}; }}
QCheckBox::indicator:hover {{ border-color: {AKZENT}; }}
QCheckBox::indicator:checked {{ background: {AKZENT}; border-color: {AKZENT}; }}
QCheckBox::indicator:disabled {{ border-color: {IDLE}; }}
QCheckBox::indicator:checked:disabled {{ background: {IDLE}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background: {FLAECHE};
    color: {TEXT};
    border: 1px solid {RAHMEN};
    border-radius: 4px;
    padding: 3px 6px;
    min-height: 18px;
    selection-background-color: {AUSWAHL};
    selection-color: {TEXT};
}}
QGroupBox QLineEdit, QGroupBox QTextEdit, QGroupBox QComboBox, QGroupBox QSpinBox {{ border-color: {IDLE}; }}
QTextEdit, QPlainTextEdit {{ padding: 6px; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {AKZENT}; }}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: {IDLE}; border-color: {GRUND}; }}

QComboBox QAbstractItemView {{
    background: {FLAECHE};
    color: {TEXT};
    border: 1px solid {RAHMEN};
    selection-background-color: {AUSWAHL};
    selection-color: {TEXT};
    outline: 0;
}}

QSpinBox {{ padding-right: 48px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {GRUND};
    border: 1px solid {RAHMEN};
    width: 42px;
    subcontrol-origin: border;
}}
QSpinBox::up-button {{ subcontrol-position: top right; height: 50%; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; height: 50%; }}
QSpinBox::up-arrow, QSpinBox::down-arrow {{ width: 14px; height: 10px; }}

QPushButton {{
    background: {FLAECHE};
    color: {TEXT};
    border: 1px solid {RAHMEN};
    border-radius: 4px;
    padding: 3px 8px;
    min-height: 18px;
}}
QGroupBox QPushButton {{ background: {GRUND}; }}
QPushButton:hover {{ border-color: {AKZENT}; }}
QPushButton:pressed {{ background: {AUSWAHL}; }}
QPushButton:checked {{ background: {AUSWAHL}; color: {AKZENT}; border-color: {AKZENT}; }}
QPushButton:disabled {{ color: {IDLE}; border-color: {GRUND}; }}

QSlider {{ background: transparent; min-height: 22px; }}
QSlider::groove:horizontal {{ height: 4px; background: {RAHMEN}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {AKZENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 14px; margin: -6px 0; border-radius: 7px; background: {NEBENTEXT}; }}
QSlider::handle:horizontal:hover {{ background: {AKZENT}; }}
QSlider::handle:horizontal:disabled {{ background: {IDLE}; }}

QListWidget, QListView, QTreeView, QTableView {{
    background: {FLAECHE};
    color: {TEXT};
    border: 1px solid {RAHMEN};
    selection-background-color: {AUSWAHL};
    selection-color: {TEXT};
    outline: 0;
}}

QMenu {{ background: {FLAECHE}; color: {TEXT}; border: 1px solid {RAHMEN}; }}
QMenu::item:selected {{ background: {AUSWAHL}; }}
QToolTip {{ background: {FLAECHE}; color: {TEXT}; border: 1px solid {RAHMEN}; }}

QScrollBar:vertical {{ background: {GRUND}; width: 12px; margin: 0; }}
QScrollBar:horizontal {{ background: {GRUND}; height: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {RAHMEN}; min-height: 28px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {RAHMEN}; min-width: 28px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {IDLE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
