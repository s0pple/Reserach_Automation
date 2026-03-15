# Session Log: 2026-03-14 - The Watchtower Fix & The Stop-Motion Stream

## 1. Was war das Ziel?
- **Primärziel:** Reparatur des "Watchtower" (`/watch` Befehl in Telegram). Bisher lieferte der Befehl nur einen schwarzen Bildschirm, was visuelle Kontrolle des God-Containers unmöglich machte.
- **Sekundärziel:** Strategische Ausrichtung klären (bauen wir ein OpenClaw-Klon oder etwas anderes?) und den Grundstein für den autonomen "Hunter-Gatherer" (Allgemeinen Web-Agenten) legen.

## 2. Was hat NICHT funktioniert und Warum? (Die Fehleranalyse)
- **Der schwarze Bildschirm:** Xvfb (der virtuelle Monitor) lief zwar, aber es gab keinen Window Manager. Playwright öffnete Fenster im absoluten "Nichts".
- **Der Zombie-Prozess:** Ein erster Versuch, `fluxbox` zu starten, endete in einem `<defunct>` (Zombie) Prozess. **Warum?** Weil das Timing im Start-Skript falsch war. `fluxbox` versuchte zu starten, bevor Xvfb vollständig initialisiert war, und crashte sofort. Zudem hielt der Prozess nicht im Hintergrund.
- **Flüchtige Prozesse:** Das Testskript für Playwright hatte anfangs nur `sleep(30)`. Bis der Telegram-Befehl ankam, war das Skript oft schon beendet. **Learning:** Ein Screenshot kann nur greifen, was *in genau diesem Moment* aktiv im RAM/Xvfb gerendert wird.
- **Docker-Illusion:** Eine Änderung am `Dockerfile` bringt nichts im laufenden Betrieb, solange der Container nicht via `docker compose build` neu gebaut wird. Wir mussten die Tools (`fluxbox`, `x11-xserver-utils`) im laufenden Container manuell via `apt-get` nachinstallieren, um sofort testen zu können.

## 3. Was hat SEHR GUT funktioniert? (Die Durchbrüche)
- **Die Reparatur des Xvfb-Stacks:** 
  - Einbau von `sleep 2` nach dem Xvfb-Start.
  - Nutzung von `nohup fluxbox -display :99 > /dev/null 2>&1 &` verhinderte das Zombie-Problem.
  - `xsetroot -solid "#2E3440"` sorgte für einen sauberen, grauen Desktop-Hintergrund, auf dem sich Browser-Fenster abheben.
- **Der Stop-Motion Livestream (Innovation):** 
  - Anstatt echtes Video zu streamen (was Telegram überlastet), haben wir die Befehle `/live` und `/stop` gebaut. 
  - Der Bot schickt ein Foto und nutzt `edit_message_media`, um dieses **eine** Foto alle 3 Sekunden zu überschreiben. 
  - **Warum ist das genial?** Es erzeugt einen perfekten, ressourcenschonenden Live-Feed direkt im Messenger. Der "Human-in-the-Loop" kann dem Agenten jetzt live beim Klicken und Tippen zusehen.
- **Strategische Klarheit ("Depth over Breadth"):** Wir haben in `docs/decisions/2026-03-14_strategy_depth_over_breadth.md` hart verankert, dass wir kein zweites "OpenClaw" für Terminbuchungen bauen, sondern eine spezialisierte, resiliente "Research Weapon".

## 4. Architektonische Entscheidungen & Neue Pläne
- **Plan 07 (The General Agent):** Dokumentiert unter `docs/plans/07_plan_general_agent_architecture.md`. 
- **Zero-Cost Reasoning:** Um API-Kosten zu sparen, soll der zukünftige Planungs-Agent komplexe Logik nicht über Tokens abwickeln, sondern indem er Playwright nutzt, um kostenlose Web-UIs (wie Google AI Studio) aufzurufen, dort den Prompt einzutippen und die Antwort als Plan zu scrapen.
- **Hybride Navigation:** Der Agent darf nicht dogmatisch sein. Er muss fließend zwischen schnellem DOM-Scraping (für einfache Seiten) und Vision + OS-Klicks (für komplexe Bot-Walls) wechseln können.

## 5. NEXT STEP (Der Übergabepunkt für den nächsten Lauf)
- **Der Code-Zustand:** Der God-Container läuft. Xvfb und Fluxbox sind stabil. Der Telegram-Bot läuft (mit `/watch` und `/live`).
- **Was als Nächstes zu tun ist:** 
  1. Den `Router` (`src/agents/local_router/router.py`) erweitern, damit er generische Anfragen ("Finde den Preis von Bananen bei Migros") erkennt.
  2. Den **Planungs-Agenten (ReAct-Loop)** bauen, der eine Aufgabe in Einzelschritte zerlegt, *bevor* er anfängt zu klicken.
  3. Sicherstellen, dass das Dockerfile beim nächsten kompletten Host-Neustart sauber durchbaut (die Änderungen sind im Dockerfile hinterlegt, müssen aber auf Host-Ebene noch kompiliert werden).