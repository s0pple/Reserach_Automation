import asyncio
import sys
import os
import re
import time
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# --- PROMPTS ---
MASTER_PROMPT_TEMPLATE = """
Du bist CLAWDBOT Brain – unser zentraler strategischer Research-Orchestrator und Langzeit-Gedächtnis.

Aktuelles Forschungsziel: "{goal}"
Branche: "{industry}"

Du leitest einen iterativen Research-Prozess mit vier festen Persönlichkeiten:
- Critic: extrem kritisch, schonungslos, sucht alle Widersprüche, Risiken, Schwächen und Halluzinationen
- Optimist: hochgradig chancenorientiert, sucht Potenziale, Vorteile und strategische Hebel
- Realist: pragmatisch, bewertet Machbarkeit, Kosten, Zeitaufwand und reale Barrieren
- Mediator: synthetisiert alle Meinungen und gibt klare nächste Schritte + Priorisierung

**Deine Arbeitsweise (immer exakt so strukturieren):**
1. Kurze Status-Zusammenfassung des aktuellen Wissensstands.
2. Nächste strategische Richtung oder klärende Frage.
3. Schreibe für genau ZWEI Personas jeweils einen spezifischen Prompt.
4. WICHTIG: Formatiere die Prompts für die Personas EXAKT so (in Code-Blöcken), damit mein Script sie auslesen kann:
```Critic
[Der genaue Such-Prompt]
```
```Optimist
[Der genaue Such-Prompt]
```

Starte jetzt den Prozess mit Phase 1 (Markt-Mapping & Akteure). Gib mir die ersten zwei Prompts.
"""

# --- HELPER FUNCTIONS ---
async def extract_ai_studio_response(page):
    """Extrahiert die letzte Antwort aus AI Studio mit robusten Locators."""
    console.print("[Brain] ⏳ Warte auf Antwort-Generierung...")
    
    # 1. Warte bis die Generierung abgeschlossen ist
    start_wait = time.time()
    while (time.time() - start_wait) < 180:
        # AI Studio zeigt oft einen Stop-Button während der Generierung
        stop_btn = page.locator('button:has-text("Stop"), ms-icon:has-text("stop"), .stop-button').first
        if not await stop_btn.is_visible(timeout=2000):
            # Prüfen ob die Nachricht fertig aussieht (ms-message-content ist vorhanden)
            last_msg = page.locator('ms-message-content').last
            if await last_msg.is_visible(timeout=2000):
                break
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(4)
    
    await asyncio.sleep(5) 
    
    # 2. Extraktion
    try:
        # Wir nutzen Playwright's last() Locator, der Shadow DOMs automatisch durchdringt
        last_msg = page.locator('ms-message-content').last
        text = await last_msg.inner_text()
        if len(text.strip()) > 50:
            return text
    except:
        pass
        
    # Fallback: JavaScript Extraktion
    return await page.evaluate("""
        () => {
            const messages = document.querySelectorAll('ms-message-content, .model-message, .message-content');
            return messages.length > 0 ? messages[messages.length - 1].innerText : document.body.innerText;
        }
    """)

async def run_google_search(page, prompt):
    """Führt eine Suche im AI Mode aus und extrahiert das Ergebnis."""
    encoded_prompt = prompt.replace(' ', '+')
    search_url = f"https://www.google.com/search?q={encoded_prompt}&sourceid=chrome&ie=UTF-8&udm=50&aep=48&cud=0"
    
    console.print(f"[Worker] 🌐 Navigiere zu Google AI Mode...")
    await page.goto(search_url, wait_until="domcontentloaded")

    # Cookie-Check
    try:
        consent = page.locator('button:has-text("Alle akzeptieren"), button:has-text("Alle ablehnen"), button:has-text("Ich stimme zu"), button:has-text("Agree")').first
        if await consent.is_visible(timeout=5000):
            await consent.click()
            await asyncio.sleep(2)
    except: pass

    console.print(f"[Worker] ⏳ Warte auf AI Overview (15s)...")
    await asyncio.sleep(15) 
    
    return await page.evaluate("""
        () => {
            const findByText = (text) => Array.from(document.querySelectorAll('div, span, b, p')).find(el => el.innerText && el.innerText.includes(text));
            let aiBlock = document.querySelector('div[data-md="61"]') || 
                           document.querySelector('div[jscontroller][jsname]') ||
                           findByText('Generative KI ist experimentell');
            return aiBlock ? aiBlock.innerText : document.body.innerText.substring(0, 3000);
        }
    """)

async def send_to_ai_studio(page, text):
    """Tippt Text in AI Studio ein und sendet ihn extrem robust."""
    try:
        # 1. Cookie-Banner
        try:
            consent_btn = page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Akzeptieren")').first
            if await consent_btn.is_visible(timeout=3000):
                await consent_btn.click()
                await asyncio.sleep(1)
        except: pass

        # 2. Feld finden und fokussieren
        input_selector = 'textarea, [contenteditable="true"]'
        input_el = page.locator(input_selector).first
        await input_el.wait_for(state="visible", timeout=30000)
        
        # Mehrfacher Klick um sicher zu gehen
        await input_el.click()
        await asyncio.sleep(0.5)
        await input_el.click()
        await asyncio.sleep(1)

        # Text eintippen (statt injizieren, um Permission Denied zu vermeiden)
        await page.keyboard.type(text, delay=2) # Etwas Verzögerung simuliert menschliche Eingabe
        
        await asyncio.sleep(2)
        
        # 3. Senden via Ctrl+Enter
        console.print("[Brain] ⚡ Sende Kommando...")
        await page.keyboard.down("Control")
        await page.keyboard.press("Enter")
        await page.keyboard.up("Control")
            
    except Exception as e:
        console.print(f"[Brain] ❌ Fehler beim Senden: {e}")
        await page.screenshot(path="brain_error.png")
        console.print("[System] 📸 Screenshot 'brain_error.png' erstellt.")

# --- MAIN LOOP ---
async def start_full_automation():
    console.rule("[bold cyan]CLAWDBOT FULL AUTO-RESEARCH[/bold cyan]")
    
    goal = Prompt.ask("[bold yellow]Forschungsziel?[/bold yellow]", default="analyze opportunities in vertical farming Switzerland")
    industry = Prompt.ask("[bold yellow]Branche?[/bold yellow]", default="Agritech")
    iterations = int(Prompt.ask("[bold yellow]Iterationen?[/bold yellow]", default="3"))

    user_data_dir = os.path.abspath("browser_session")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 900},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        brain_page = context.pages[0]
        await brain_page.goto("https://aistudio.google.com/app/prompts/new_chat")
        
        # Falls Login nötig
        if "accounts.google.com" in brain_page.url:
            console.print("[Brain] 🔑 Bitte logge dich ein!")
            await brain_page.wait_for_url("**/app/prompts**", timeout=300000)

        worker_pages = []
        for _ in range(2):
            p_worker = await context.new_page()
            await p_worker.goto("https://www.google.com")
            worker_pages.append(p_worker)

        # --- INITIALER START ---
        initial_prompt = MASTER_PROMPT_TEMPLATE.format(goal=goal, industry=industry)
        await send_to_ai_studio(brain_page, initial_prompt)
        
        for i in range(1, iterations + 1):
            console.rule(f"[bold magenta]Iteration {i}/{iterations}[/bold magenta]")
            
            brain_response = await extract_ai_studio_response(brain_page)
            
            # Prompts extrahieren
            tasks = re.findall(r"```([a-zA-Z]*)\n?(.*?)```", brain_response, re.DOTALL)
            
            if not tasks:
                console.print("[red]❌ Keine Prompts gefunden. Versuche es erneut...[/red]")
                await asyncio.sleep(10)
                brain_response = await extract_ai_studio_response(brain_page)
                tasks = re.findall(r"```([a-zA-Z]*)\n?(.*?)```", brain_response, re.DOTALL)

            if not tasks:
                console.print("[red]❌ Abbruch: Brain liefert keine formatierten Prompts.[/red]")
                await brain_page.screenshot(path=f"iteration_{i}_failed.png")
                break
            
            results = []
            for idx, (role_tag, prompt_content) in enumerate(tasks[:2]):
                role = role_tag.strip() or f"Worker {idx+1}"
                console.print(f"🚀 [Worker:{role}] Suche läuft...")
                res = await run_google_search(worker_pages[idx], prompt_content.strip())
                results.append(f"ERGEBNIS {role.upper()}:\n{res}")
            
            feedback = "Hier sind die Ergebnisse der Suchen:\n\n" + "\n\n".join(results) + "\n\nAnalysiere diese und gib mir die nächsten 2 Prompts im ```[Rolle]``` Format."
            await brain_page.bring_to_front()
            await send_to_ai_studio(brain_page, feedback)
            await asyncio.sleep(10)

        console.rule("[bold green]TOTAL-AUTOMATISIERUNG BEENDET[/bold green]")
        while True: await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(start_full_automation())
    except KeyboardInterrupt:
        sys.exit(0)
