"""Utils-Paket — Gemeinsame Hilfsfunktionen und Konstanten."""
from __future__ import annotations

from pathlib import Path

# Projekt-Root: src/../ (robust, unabhaengig von Datei-Tiefe)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
