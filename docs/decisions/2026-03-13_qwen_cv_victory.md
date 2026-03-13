# ADR: Visual Dominance over Qwen Victory
            
Datum: 13. März 2026

## Entscheidung
Der visuelle Weg (CV-Bot + Gemini Vision + xdotool) wurde erfolgreich zur Überwindung von Qwen.ai genutzt.

## Warum war das erfolgreicher als der DOM-Weg?
1. **Anti-Bot Umgehung:** Qwen reagiert extrem empfindlich auf Playwright/Selenium Hooks. xdotool sendet reale OS-Level Mouse-Events, die ununterscheidbar von menschlichen Eingaben sind.
2. **Banner-Management:** DOM-basierte Banner-Entfernung (JavaScript) triggert oft 'Re-Renders' oder neue Security-Layer. Der visuelle Klick auf das 'X' (lokalisiert durch Vision) wird als legitime Nutzerinteraktion gewertet.
3. **Fokus-Unabhängigkeit:** Durch xdotool windowactivate und koordinatenbasierte Klicks (statt DOM-Referenzen) ist das System immun gegen Shadow DOM oder komplexe Iframe-Strukturen.
            