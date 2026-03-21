# Decision Record: FastMCP Server, Worker Queue & Bot-Prevention

## Context & Challenge
Nachdem die grundlegenden Klick-Routinen im Playwright funktionieren, wurde der eigentliche **FastMCP Proxy Server** implementiert. Dabei traten zwei zentrale Fragen auf:
1. Wie verhindern wir System-Lockups bei gleichzeitigen Agenten-Anfragen (Maus-Chaos)?
2. Wie minimieren wir die Gefahr der Bot-Erkennung durch Google, wenn wir mehrere Tabs oder Accounts nutzen?

## Implementation: 3-Layer "Maus-Gott" Architektur
Der Server in src/mcp/server/main.py wurde etabliert und läuft erfolgreich im Docker-Container (Xvfb).
Er besteht aus drei Layern:
1. **Layer 1 (API & Queue):** Der *FastMCP Server* stellt das Tool sk_gemini als SSE-Endpoint bereit. Anfragen werden nicht direkt ausgeführt, sondern als BrowserTask in eine asynchrone Warteschlange (syncio.Queue) gelegt.
2. **Layer 2 (Single Worker):** Eine Background-Loop arbeitet die Tasks **streng sequenziell** ab. Dies verhindert Fokus-Probleme (Maus-Chaos in X11) und besitzt ein hartes Timeout-Limit von 90 Sekunden pro Task.
3. **Layer 3 (Tab Registry):** Verwaltet die Playwright BrowserContexts (die Tabs/Profile). Es existiert ein hartes RAM-Limit (max. 3 gleichzeitige Profil-Aufrufe pro Container).

## Strategy: Anti-Bot & Account Management
Um Bot-Sperren zuvorzukommen, gilt ab sofort folgende strikte Systemvorgabe:

**Regel:** *Ein virtueller Bildschirm (1 Docker Container) = Exakt 1 Google Account.*

*Grund:* Google (und andere Provider) überwachen TLS-Fingerprints, WebGL-Canvas und das Verhalten der Browser-Engine. Mehrere verschiedene Google-Sessions aus exakt demselben (Playwright)-Prozess zu feuern, erzeugt ein hohes Risiko für Shadow-Bans. 

**Skalierung:**
* Anstatt viele Google-Accounts in einem Container zu mischen, starten wir über docker-compose separate Container (z.B. mcp_gemini_1 für Account A, mcp_gemini_2 für Account B). 
* Innerhalb **eines** Containers können dennoch mehrere Tabs existieren, allerdings dienen diese dann dazu, **verschiedene parallele Chats des *selben* Google-Accounts** zu verwalten (z.B. Tab 1: Coding-Chat, Tab 2: Research-Chat).

## Status
* **Ready:** Multi-Turn (Zusammenhängender Chat) funktioniert stateful.
* **Ready:** Warteschlange für parallele Anfragen fängt Lastspitzen ab.
* **Ready:** Health-Checks und API sind von außen erreichbar.
