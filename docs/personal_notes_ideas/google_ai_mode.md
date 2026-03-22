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


22.03.2026;
Gemini hat gesagt
Ein fertiges "OneCLI", das alle Tools nahtlos in einem Programm vereint, gibt es nicht. Die verschiedenen Kommandozeilen-Tools sind in unterschiedlichen Sprachen geschrieben und haben komplett andere Architekturen.

OpenClaw kann aber exakt diese "Instanz davor" sein. Stell dir OpenClaw als den Bauleiter vor. Der Bauleiter mauert nicht selbst. Er ruft den Baggerfahrer (Aider) für die harten Code-Eingriffe und den Architekten (Gemini CLI) für die Analyse des riesigen Bauplans.

OpenClaw weiss das allerdings von Haus aus nicht. Du musst dem System dieses Verhalten explizit beibringen.

Warum das Sinn macht
Es ist keineswegs unnötig, sondern aktuell der cleverste Weg für Power-User. Du kombinierst die kostenlosen Stärken der jeweiligen Tools und sparst dir manuelle Terminal-Wechsel. Du baust dir effektiv einen Router-Agenten.

Der Ablauf ist dann simpel:

Dein Befehl: "Analysiere das komplette Repository und schreibe einen Test für das neue Modul."

Die Entscheidung: OpenClaw erkennt die Dateimenge und entscheidet: "Zu gross für Aider. Ich nutze zuerst das Gemini CLI, da der Kontext dort gratis ist."

Die Ausführung: OpenClaw lässt Gemini den Architektur-Plan erstellen. Danach feuert OpenClaw den Befehl an Aider ab, um den Code präzise in deine Dateien zu schreiben und über Git zu committen.

Die technische Hürde
Das grösste Problem bei dieser Kette ist der Kontext-Verlust. Aider weiss nicht, was das Gemini CLI eine Sekunde vorher analysiert hat, da beide Befehle isoliert im Terminal laufen. Die Lösung ist eine geteilte Zwischenablage: OpenClaw muss gezwungen werden, das Analyse-Ergebnis von Gemini in eine Datei (z.B. MEMORY.md) zu schreiben und Aider anschliessend anzuweisen, diese Datei als Basis zu lesen.

Soll ich dir einen konkreten System-Prompt entwerfe, der OpenClaw genau dieses Router-Verhalten inklusive der Datei-Übergabe beibringt?

https://www.google.com/search?q=unterscheiden+sich+bis+auf+die+Modelle+CLI%27s+eigenltich%3F+z.B%3A+claudecode%2C+gemini+cli%2C+codex+oder+auch+im+vergleich+zu+opensoruce+alternativen+wie+opencode%2C+aider%3F&sca_esv=7339b5109d39e750&sxsrf=ANbL-n41zvIFXW981FIm0UvPFWSP1JLltQ%3A1774170074426&fbs=ADc_l-YGrpJMQtvjQ6h14rj-dfIrbPkd_Upq68wJVnEIgo2Pw_tl1m5mugok-qdTIdvYWwf0At6Jcd4yGVh0Pc2zLEb_eCMWInYf4At52tjMPtYrPM_0JoR336L21HX4CjFXAOAST7DrDgLw-J0fgvtJbpNZPO9m_tazsn5xXrGKH3L5k5EUEhq7qSkuPSsWRjfJ-FcEXZENG8UNpTMVBwa_JP2H45B_0g&aep=1&ntc=1&sa=X&ved=2ahUKEwi7rrrIkrOTAxXsgP0HHf_dALcQ2J8OegQIDBAE&biw=1920&bih=945&dpr=1&mstk=AUtExfBSp6HURDQZqTiXv03-hiVQo-vVRLnVAvAVAkrRewyygRQ_tqd6pSoV64xCy0HsZikq5p96Zej7FHgjPIaUDJPnYncnIvmK1lDez7g_quI8iqTSxJtwdrpj98GkVkoH_RanSRuzLw_hJ-99FhVcl2U_2Nbeh6DZoF3f984MZIKCEcuppuDO77mSSp_KZYT27wuiy5GCPQ8mqbsGA6jWhTriODQKIk0_Wu_VulbujFEahvsMzk0KjZBj6GmcLC8nfuMY7irQ208ORgNFq8Gnkelw1ocT2l95TsUtFWAI-HAH0qaUv4i9WqNc7jQ5f7BnkEP1dZvEV4rpbw&csuir=1&mtid=3K-_adHsNpOM9u8Pt9TzuAo&udm=50
