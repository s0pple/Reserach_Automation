# Migration Plan: Gemini CLI Experiment -> MCP Architecture

**Ziel:** Umbau des `research_automation` Repositories zu einem sauberen **MCP-Server** (Model Context Protocol), der Cloud-LLMs (Gemini, Claude) via Browser-Automatisierung steuert.

**Status:** Branch `feat/MCP` erstellt.

## 1. Core Assets (Behalten & Refactoring)
Diese Dateien bilden das Fundament für den MCP-Server.

### Infrastructure
- `infra/docker/*` (Docker-Compose, Dockerfiles)
- `requirements.txt` (Muss bereinigt werden)
- `browser_sessions/` (WICHTIG: Login-Cookies)

### Browser Automation (The Engine)
- `scripts/aistudio_client.py` -> Wird zu `src/mcp/providers/gemini_browser.py`
- `scripts/crucible_loop.py` -> Logic wird portiert in den MCP Main Loop
- `scripts/make_template.py` & `templates/` -> Für visuelle Validierung

### Telegram Integration (Optional Control Plane)
- `scripts/telegram_ai_orchestrator.py` (oder die funktionierende Logic aus `crucible_loop`)

## 2. Legacy / Experimente (Archivieren oder Löschen)
Diese Dateien blähen das Repo auf und verwirren den Context.

- `test_*.py` (Alte Unit-Tests, die nicht mehr passen)
- `scripts/attempt_*.py` (Fehlgeschlagene Fix-Versuche)
- `scripts/debug_*.py` (Einweg-Debug-Skripte)
- `temp/` & `*.png` (Screenshots, Logs)
- `docs/plans/` (Veraltete Pläne, die nicht MCP betreffen)

## 3. Action Plan (Nächste Schritte)

1. **Struktur anlegen:** Ordner `src/mcp/` erstellen.
2. **Portierung:** `aistudio_client.py` in eine saubere Klasse im `src/mcp` Ordner umziehen.
3. **Server Setup:** `mcp-server-python` installieren und einen Entrypoint erstellen.
4. **Cleanup:** Löschen aller Files aus Sektion 2.
