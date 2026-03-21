20.03.2026; 
Das Kernziel
Du baust ein lokales, komplett kostenloses KI-CLI-System. Anstatt für teure API-Tokens zu zahlen, zapfst du Cloud-LLMs wie Claude oder Gemini direkt über deren Web-Oberfläche an und integrierst das nahtlos in Tools wie OpenClaw.

Die technische Lösung: MCP statt API-Proxy
Ein simulierter API-Server scheitert oft an HTTP-Timeouts, weil Browser-Automatisierung Zeit braucht. Die stabile Architektur baut auf das Model Context Protocol (MCP).

Der Orchestrator: OpenClaw läuft lokal mit einem Gratis-Modell (z.B. Llama 3 via Ollama).

Der Vermittler: Ein eigens geschriebener MCP-Server in Python. OpenClaw nutzt diesen Server als asynchrones Werkzeug, das sich beliebig viel Zeit nehmen darf.

Die Ausführung: Isolierte Docker-Container simulieren über Xvfb virtuelle Bildschirme. Darin steuert Playwright den Browser nach harten, programmierten Regeln (Feld anklicken, Text einfügen, Ergebnis kopieren). Das ist deutlich schneller und stabiler als KI-basierte Bilderkennung.

Das Setup: Du baust das aktuell auf Windows in Docker auf und nimmst die exakt gleiche Linux-Container-Struktur später einfach auf den Mac Mini M4 mit. Browser-Cookies sicherst du über Volume-Mounts, damit die Logins erhalten bleiben.

Das Flotten-Management
Um Rate Limits der Anbieter zu umgehen, richtest du ein Rotationssystem ein. Eine simple lokale Status-Datei trackt verschiedene Google- oder Anthropic-Accounts. Sperrt ein Cloud-LLM einen Account temporär, setzt dein Skript ihn auf "Cooldown" und leitet die nächste Anfrage automatisch an den nächsten freien Container weiter.

Dein konkreter Fahrplan

Proof of Concept: Ein einfaches Dockerfile mit Playwright und Xvfb bauen. Ein lokales Skript loggt sich ein, schickt einen Prompt und kopiert die Antwort.

Die Brücke bauen: Das Python-Skript um das MCP-SDK erweitern, damit OpenClaw es als Werkzeug erkennt und ansteuern kann.

Rotation einbauen: Die Cooldown-Logik und Account-Verwaltung integrieren.

Skalierung: Das Setup via Docker-Compose so konfigurieren, dass mehrere Agenten-Container parallel laufen.

https://www.google.com/search?sca_esv=9e177e2ff790fc0e&sxsrf=ANbL-n6FBoQmG5eNXaqLpdtORpEb33xswQ%3A1774034223518&aep=26&ntc=1&sa=X&ved=2ahUKEwi8obG7sK-TAxVFgf0HHXY0AsEQoo4PegYIAQgAEAE&biw=1920&bih=945&dpr=1&mtid=MZ29aeG1Cev87_UP7Izw6Qs&udm=50&mstk=AUtExfAksBxuL3GBHdPt-uXDct_rFOy1Hbg9o6BDDHYlCXyhXagRadXQmtJWutIq39LwYR_xHFEshlc3OgNGmZSUQumKwl79B9OhoIzll_U4UGQwxvtdXHN02B7E8q8K6cmOVLgxFqhZymI48mIAkgkb4vybwBAg97H9aJxVZbIOVipW1vQUar8CvjOZpd92Ka8PKKHEq-a5qPDW8esw6jpxdCJRsK8HuHpEj77HzDOsjSEtn2Jx6fzS84JJB2t1G2abSwmYyaQ-c-ZuJ6mCJpep3aRcy5PE_JOvCP3TXPzM121IvCEXU2_-FiTJk8dBoHj-b1mMj_lPlZ3_t8z759l0mTOPpwFD_CBg8Q&csuir=1&q=how+expensive+are+the+different+CLI+Tools%3F&atvm=2

