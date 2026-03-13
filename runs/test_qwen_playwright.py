import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🌐 Starte Qwen Playwright Workflow...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = await browser.new_page()
        
        print("➡️ Gehe zu chat.qwen.ai...")
        await page.goto("https://chat.qwen.ai/", timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        print("➡️ Suche Eingabefeld und tippe...")
        # Warte auf das Eingabefeld (meist textarea oder ein contenteditable div)
        input_locator = page.locator("textarea, [contenteditable='true']").first
        await input_locator.wait_for(state="visible")
        
        # Text direkt ins DOM injizieren/tippen
        prompt = "Wie aktiviere ich hier den Deep Research oder Deep Search Modus? Erkläre es kurz."
        await input_locator.fill(prompt)
        await page.wait_for_timeout(1000)
        
        print("➡️ Sende Anfrage ab...")
        await input_locator.press("Enter")
        
        # Check for the login modal
        print("➡️ Prüfe auf Login-Modal...")
        try:
            stay_logged_out_btn = page.get_by_text("Stay logged out")
            await stay_logged_out_btn.wait_for(state="visible", timeout=3000)
            print("➡️ Klicke 'Stay logged out'...")
            await stay_logged_out_btn.click()
            await page.wait_for_timeout(1000)
            # Maybe we need to press enter again? Let's check.
            await input_locator.press("Enter")
        except Exception:
            print("Kein Login-Modal gefunden, fahre fort.")
        
        print("⏳ Warte auf Antwort (bis zu 45 Sekunden)...")
        # Wir warten darauf, dass eine Antwortbox erscheint (meist .markdown-body oder ähnliches)
        # Und dann warten wir, bis der generierte Text nicht mehr wächst (Netzwerk idle)
        try:
            await page.wait_for_selector(".markdown-body, .message-content, [class*='message']", timeout=45000)
            await page.wait_for_timeout(10000) # Gib Qwen Zeit zum Generieren
        except Exception as e:
            print(f"⚠️ Timeout beim Warten auf Antwort-Element: {e}")
            
        print("📋 Extrahiere sichtbaren Text...")
        # Den gesamten Text der Seite (oder der Nachrichten) abgreifen
        content = await page.evaluate("document.body.innerText")
        
        with open("qwen_playwright_output.txt", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("\n" + "="*50)
        print("📊 EXTRACTION RESULT")
        print("="*50)
        print(f"Länge: {len(content)} Zeichen")
        print("Vorschau:")
        print(content[:1000])
        print("="*50)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
