#!/usr/bin/env python3
"""
Startskript für TaskCard Downloader GUI
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from taskcard_gui import main
    main()
except ImportError as e:
    print(f"Fehler beim Importieren: {e}")
    print("Stellen Sie sicher, dass alle erforderlichen Module installiert sind.")
    print("Führen Sie aus: pip install selenium requests")
    input("Drücken Sie Enter zum Beenden...")
except Exception as e:
    print(f"Fehler beim Starten der GUI: {e}")
    input("Drücken Sie Enter zum Beenden...")