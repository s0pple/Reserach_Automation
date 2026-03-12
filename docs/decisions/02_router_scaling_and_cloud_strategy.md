# Architektur-Entscheidung: Router Scaling & Cloud Strategie

**Datum:** 11. März 2026
**Vision des Product Owners:** Das System soll **absolut gratis** (oder so günstig wie möglich) und hochgradig modular bleiben. Die Architektur muss so aufgebaut sein, dass Komponenten schnell ausgetauscht werden können ("Vendor Lock-in" vermeiden). Langfristig wird eine Zero-Hardware-Strategie angestrebt, bei der auf teure lokale Rechner (Mac Mini, Custom PC) verzichtet wird.

---

## 1. Die Hardware-Entscheidung (Langfristige Strategie)

Obwohl ein **Mac Mini (M4, 16GB)** für lokales KI-Hosting extrem effizient (ca. 40 CHF Strom/Jahr) und leistungsstark ist, erfordert er ein Vorab-Investment von ca. 650-800 CHF.
Da die Vision auf "Gratis & Cloud" abzielt, wird folgende Strategie verfolgt:

*   **Phase 1 (Aktuell): Zero-Cost Prototyping.** Das System läuft lokal auf dem bestehenden Windows-Rechner des Nutzers. Es fallen keine Kosten für Hardware oder Cloud-Server an.
*   **Phase 2 (Zukunft): Cloud-Server ohne GPU.** Das System wird auf einen extrem günstigen Cloud-Server (z.B. Hetzner, Oracle Free Tier, AWS Free Tier) migriert.
*   **Der Trick dabei:** Da diese Server keine GPUs haben, wird der **Local Router (Ollama)** durch günstige oder gratis **Cloud-APIs (Gemini Flash, Groq, OpenRouter)** ersetzt. Das schwere Reasoning passiert ohnehin über externe APIs (Gemini).

## 2. Der Umgang mit Computer Vision (CV-Bot) in der Cloud
**Das Problem:** Ein Cloud-Server hat normalerweise kein Desktop-System (Headless Linux), weshalb `PyAutoGUI` (Maus/Tastatur) und klassische Web-Scraping-Tools oft scheitern.

**Die Lösung (Modularität):**
Sollte das System in die Cloud ziehen, wird der CV-Bot durch reine **API-gesteuerte Scraping-Dienste** (wie Firecrawl, Browserbase, Browserless) oder echte Headless-Browser-Frameworks (Playwright) ersetzt, die rein auf DOM/Text-Ebene operieren. Die "Sight & Touch" Architektur (Bildschirm klicken) wird in der Cloud obsolet und durch "Request & Parse" ersetzt.

## 3. Benennung & Entkopplung: Deep Research
**Entscheidung:** Das Gemini Deep Research Feature wurde aus der Venture-Analyst-Pipeline extrahiert und als eigenständiges Tool in der Registry verankert.
**Name:** `gemini_deep_research`
**Begründung:** Der Name ist für das LLM-Routing (Ollama/API) präzise genug, um bei Prompts wie "Mach einen Deep Research über X" direkt erkannt zu werden, ohne Verwechslungsgefahr mit anderen Tools zu provozieren.

---

## Nächste Schritte / Backlog für die Zukunft
*   [ ] **API-Router Evaluierung:** Teste (z.B. mit Groq oder Gemini Flash) wie gut und günstig das "Semantic Routing" via API funktioniert, um Ollama später ablösen zu können.
*   [ ] **Cloud-Deployment:** Evaluierung von Free-Tier Cloud-Anbietern für das 24/7 Hosting des Telegram-Bots und Orchestrators.
