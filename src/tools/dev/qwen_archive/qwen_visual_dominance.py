import asyncio
import os
import time
import subprocess
from src.tools.cv_bot.workflow_manager import WorkflowManager
from src.tools.cv_bot.cv_bot_tool import CVBotTool

async def main():
    os.environ["DISPLAY"] = ":99"
    manager = WorkflowManager()
    cv_tool = CVBotTool()
    
    # 1. Chromium im sichtbaren Modus starten (App-Modus für Fokus)
    print("🌐 Launching Chromium (Visual Mode)...")
    subprocess.Popen("chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1280,1024 --force-device-scale-factor=1 --incognito --app='https://chat.qwen.ai/'", shell=True)
    time.sleep(12)
    
    # 2. Fenster fokussieren (Erzwingen)
    print("🎯 Forcing Window Focus...")
    os.system("xdotool windowactivate $(xdotool search --onlyvisible --class chromium | head -1)")
    time.sleep(2)
    
    # 3. Screenshot & Vision: Finde das 'X'
    print("👁️ Visual Search for Banner 'X'...")
    image_bytes, img_bgra, ox, oy = manager._get_screenshot_bytes()
    # Debug
    with open("test/qwen_recon_01.png", "wb") as f: f.write(image_bytes)
    
    res_x = await cv_tool.find_element_via_vision(image_bytes, "the small close x icon of the image banner located in the lower half of the screen", original_bgra=img_bgra, offset_x=ox, offset_y=oy)
    
    if res_x.get("found"):
        print(f"🖱️ Hitting the 'X' at {res_x['x']}, {res_x['y']}...")
        os.system(f"xdotool mousemove {res_x['x']} {res_x['y']} click 1")
    else:
        print("⚠️ 'X' not found via Vision. Trying 'Esc' key as backup...")
        os.system("xdotool key escape")
    time.sleep(2)
    
    # 4. Screenshot & Vision: Finde das Eingabefeld
    print("👁️ Visual Search for Search Bar...")
    image_bytes, img_bgra, ox, oy = manager._get_screenshot_bytes()
    with open("test/qwen_recon_02.png", "wb") as f: f.write(image_bytes)
    
    res_input = await cv_tool.find_element_via_vision(image_bytes, "the central search input bar where it says 'How can I help'", original_bgra=img_bgra, offset_x=ox, offset_y=oy)
    
    if res_input.get("found"):
        print(f"🖱️ Clicking into Input at {res_input['x']}, {res_input['y']}...")
        os.system(f"xdotool mousemove {res_input['x']} {res_input['y']} click 1")
        time.sleep(1)
        
        prompt = "Führe eine Marktanalyse zur KI-Infrastruktur 2030 durch. Sei extrem detailliert."
        print(f"⌨️ Typing prompt: {prompt}")
        # xdotool type is human-like and bypasses most DOM-based protections
        os.system(f"xdotool type --delay 80 '{prompt}'")
        time.sleep(1)
        os.system("xdotool key Return")
        print("🚀 Sent! Waiting 60s for full generation...")
        time.sleep(60)
        
        # 5. Finale Sichtprüfung
        print("📸 Final Visual Check...")
        image_bytes, _, _, _ = manager._get_screenshot_bytes()
        with open("test/qwen_victory_visual.png", "wb") as f: f.write(image_bytes)
        
        # 6. Extraktion (Der 'Vorschlaghammer' Kopier-Befehl)
        print("📋 Final Extraction (Ctrl+A, Ctrl+C)...")
        # Scroll a bit down to capture more
        os.system("xdotool key Page_Down")
        time.sleep(1)
        os.system("xdotool key ctrl+a")
        time.sleep(1)
        os.system("xdotool key ctrl+c")
        time.sleep(2)
        
        try:
            result = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o']).decode('utf-8', errors='ignore')
            with open("test/qwen_victory_report.md", "w", encoding="utf-8") as f:
                f.write(f"# Qwen Victory Report (Visual Mode)\n\n{result}")
            print(f"✅ Mission Accomplished! Report saved. Size: {len(result)} chars.")
            
            # Entscheidung dokumentieren
            doc_content = f"""# ADR: Visual Dominance over Qwen Victory
            
Datum: 13. März 2026

## Entscheidung
Der visuelle Weg (CV-Bot + Gemini Vision + xdotool) wurde erfolgreich zur Überwindung von Qwen.ai genutzt.

## Warum war das erfolgreicher als der DOM-Weg?
1. **Anti-Bot Umgehung:** Qwen reagiert extrem empfindlich auf Playwright/Selenium Hooks. xdotool sendet reale OS-Level Mouse-Events, die ununterscheidbar von menschlichen Eingaben sind.
2. **Banner-Management:** DOM-basierte Banner-Entfernung (JavaScript) triggert oft 'Re-Renders' oder neue Security-Layer. Der visuelle Klick auf das 'X' (lokalisiert durch Vision) wird als legitime Nutzerinteraktion gewertet.
3. **Fokus-Unabhängigkeit:** Durch xdotool windowactivate und koordinatenbasierte Klicks (statt DOM-Referenzen) ist das System immun gegen Shadow DOM oder komplexe Iframe-Strukturen.
            """
            with open("docs/decisions/2026-03-13_qwen_cv_victory.md", "w", encoding="utf-8") as f:
                f.write(doc_content)
                
        except Exception as e:
            print(f"❌ Final copy failed: {e}")
            
    else:
        print("❌ Could not find search bar. Qwen might be in a different state.")

if __name__ == "__main__":
    asyncio.run(main())
