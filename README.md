# TaskCard Downloader

Dieses Script lädt alle Inhalte und Dateien von einer TaskCard-Board herunter.

## Installation

1. Installieren Sie die benötigten Pakete:
```bash
pip install -r requirements.txt
```

2. Stellen Sie sicher, dass Chrome Browser installiert ist.

## Verwendung

```bash
python taskcard_downloader.py
```

Das Script lädt automatisch alle Inhalte von der konfigurierten TaskCard-URL herunter.

## Ausgabe

Das Script erstellt einen `taskcard_download` Ordner mit folgender Struktur:
- `cards/` - Textdateien mit Karteninhalten
- `images/` - Heruntergeladene Bilder
- `documents/` - Heruntergeladene Dokumente  
- `metadata/` - JSON-Dateien mit strukturierten Kartendaten
- `download_summary.json` - Zusammenfassung des Downloads
- `page_screenshot.png` - Screenshot der Seite
- `page_source.html` - HTML-Quellcode der Seite

## Hinweise

- Das Script verwendet Selenium mit Chrome im Headless-Modus
- JavaScript-basierte Inhalte werden automatisch geladen
- Bei Problemen können Sie die gespeicherten Screenshots und HTML-Quellen zur Analyse verwenden