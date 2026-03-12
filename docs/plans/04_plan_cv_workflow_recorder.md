# Plan: CV Workflow Recorder (Self-Healing UI Automation)

## Ziel
Der CV-Bot soll nicht mehr nur "blind" klicken oder starre Skripte benötigen. Er soll ähnlich wie das `Gemini_Deepreserach`-Modul komplexe Abläufe (Workflows) durchführen können. 
**Kern-Feature:** Wenn er eine Aufgabe zum ersten Mal macht, nutzt er Screenshots und ein Vision-LLM (Gemini), um die Objekte (Buttons, Felder) zu finden. Hat er sie gefunden und die Aktion erfolgreich ausgeführt, speichert er diesen Ablauf als wiederverwendbares Skript. Beim nächsten Mal führt er das Skript extrem schnell lokal (ohne Cloud-LLM-Kosten) aus.

## Architektur (Die 3 Phasen)

### Phase 1: Der "Vision Locator" (Das Auge)
- Wenn ein Befehl kommt (z.B. "Klicke auf den Warenkorb"), macht der Bot mit `mss` oder `pyautogui` einen Screenshot.
- Der Screenshot und der Befehl werden an ein Vision-LLM gesendet.
- Das LLM analysiert das Bild und gibt exakte `(X, Y)` Koordinaten zurück.

### Phase 2: Action & Feedback (Die Hand)
- Der CV-Bot führt die Aktion (Klick, Tippen) an den ermittelten Koordinaten mittels `pyautogui` aus.

### Phase 3: The Recorder (Das Gedächtnis)
- Nach erfolgreicher Ausführung wird der Schritt in einer Datei (z.B. `workflows/my_task.json`) gespeichert. 
- Das Skript speichert: Target-Name ("Warenkorb"), gefundene (X,Y)-Koordinaten und die Aktion ("click").
- **Self-Healing-Aspekt:** Wenn das lokale Skript beim nächsten Mal fehlschlägt (weil sich die UI geändert hat), triggert der Bot automatisch wieder Phase 1 (Screenshot -> LLM), um die neuen Koordinaten zu finden und aktualisiert das Skript.

## Implementierungs-Schritte (Worker-Tasks)

1. **`src/tools/cv_bot/cv_bot_tool.py` überarbeiten:**
   - Einbauen von `mss` für schnelle Screenshots.
   - Eine Methode `find_element_via_vision(image, target)` hinzufügen.
2. **Workflow-Manager bauen (`src/tools/cv_bot/workflow_manager.py`):**
   - Logik zum Speichern und Laden von JSON-Ablaufsplänen.
3. **Integration & Test:**
   - Ein Test-Skript schreiben (`runs/test_cv_recorder.py`), das einen simplen Workflow ("Öffne Taschenrechner und tippe 5+5") einmal mit Vision lernt und dann blitzschnell aus dem Cache abspielt.

## Offene Fragen an den Manager (User)
- Sollen wir als Vision-Modell direkt die **Gemini API** nutzen oder gibt es ein lokales Modell, das wir bevorzugen (z.B. LLaVA über Ollama)?
- Ist das JSON-Format für die Skripte gut oder bevorzugst du generierte Python-Playwright/PyAutoGUI-Skripte?