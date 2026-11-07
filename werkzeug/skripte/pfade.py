"""Gemeinsame Pfade. Alles relativ zum Repo – funktioniert unter Windows und Linux."""
from pathlib import Path
WERK = Path(__file__).resolve().parent.parent      # werkzeug/
SEITE = WERK.parent                                 # Repo-Wurzel = die Webseite
DATEN = WERK / 'daten'                              # öffentliche Stammdaten (im Repo)
PRIVAT = WERK / 'privat'                            # NICHT im Repo (.gitignore): Chat-Exporte, links.json, ergebnis.json, Rohdaten
PRIVAT.mkdir(exist_ok=True)
