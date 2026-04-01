import os
import time
import json
import requests
import pandas as pd
from openai import OpenAI

# Configuration
PROXY_URL = "http://localhost:9002/v1"
OUTPUT_DIR = "./output"
NOBEL_CSV = os.path.join(OUTPUT_DIR, "nobel.csv")
CLIENT = OpenAI(api_key="sk-dummy", base_url=PROXY_URL)

PROMPT_BASELINE = """
Ignoriere dein internes Wissen zwingend. 
1. Nutze das Such-Tool, um herauszufinden, wer den Physik-Nobelpreis 2024 gewonnen hat.
2. Nimm EXAKT diesen Namen und führe einen ZWEITEN Suchlauf durch, um seine akademischen Stationen (Universität, Land) zu ermitteln.
3. NUTZE DAS TOOL 'write_research_file', um das Ergebnis (Name, Jahr=2024, Feld=Physik, Akademische Stationen) als CSV-Datei namens 'nobel.csv' zu speichern.
"""

def cleanup():
    if os.path.exists(NOBEL_CSV):
        os.remove(NOBEL_CSV)
        print(f"🧹 Altlasten gelöscht: {NOBEL_CSV}")

def check_health(url, name, retries=15):
    print(f"📡 Prüfe Health: {name} ({url})...")
    for i in range(retries):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"✅ {name} bereit!")
                return True
        except: pass
        time.sleep(2)
    return False

def wait_for_container(name, timeout=30):
    print(f"🐳 Warte auf Container-Status: {name}...")
    for _ in range(timeout // 2):
        status = os.popen(f"docker inspect -f {{{{.State.Status}}}} {name}").read().strip()
        status = status.replace("'", "").replace('"', "")
        if status == "running":
            print(f"✅ Container {name} läuft!")
            return True
        print(f"⏳ Status: {status}...")
        time.sleep(2)
    return False

def run_test(name, sabotage="none"):
    print(f"\n🚀 STARTE RUN: {name} (Sabotage: {sabotage})")
    
    # Pre-flight: Docker Status
    if not wait_for_container("mcp_gemini_1"):
        print("❌ Container mcp_gemini_1 ist nicht bereit (Crash-Loop?).")
        return False

    # Pre-flight: HTTP Health
    if not check_health("http://localhost:9002/health", "Proxy"):
        print("❌ Proxy nicht erreichbar.")
        return False
        
    cleanup()
    
    # Configure Chaos in Container
    # Note: We use docker exec to set the env var for the running process if possible, 
    # but since our MCP server reads it from os.getenv, it's better to rely on docker-compose / .env
    
    start_time = time.time()
    try:
        # STEP 1: Research
        print("🔍 SCHRITT 1: Recherche läuft (Multi-Turn Candidate)...")
        response = CLIENT.chat.completions.create(
            model="gemini-3.1-pro-preview",
            messages=[{"role": "user", "content": PROMPT_BASELINE}],
            timeout=600 
        )
        raw_answer = response.choices[0].message.content
        
        # V15 Fix: Extract content if double-wrapped by accident
        try:
            if raw_answer.strip().startswith("{"):
                data = json.loads(raw_answer)
                answer = data.get("response", raw_answer)
            else:
                answer = raw_answer
        except:
            answer = raw_answer
            
        print(f"📅 Recherche beendet. Antwort-Länge: {len(answer)} Zeichen.")

        # STEP 2: Persistence
        print("💾 SCHRITT 2: Speichere Ergebnis via write_research_file Tool...")
        save_prompt = f"SAVE_FILE:nobel.csv\n{answer}"
        save_response = CLIENT.chat.completions.create(
            model="browser-agent-gemini",
            messages=[{"role": "user", "content": save_prompt}],
            timeout=120
        )
        print(f"✅ Speicher-Bestätigung: {save_response.choices[0].message.content}")

        duration = time.time() - start_time
        print(f"🏁 GESAMT-DAUER: {duration:.1f}s")
        
    except Exception as e:
        print(f"❌ Run gescheitert: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verification
    if os.path.exists(NOBEL_CSV):
        print(f"✅ CSV gefunden auf Host: {NOBEL_CSV}")
        try:
            df = pd.read_csv(NOBEL_CSV)
            print("📄 CSV Inhalt (Vorschau):")
            print(df.head(5).to_string())
        except Exception as e:
            print(f"⚠️ CSV lesbar, aber Parser-Fehler: {e}")
    else:
        print(f"❌ CSV FEHLT auf Host: {NOBEL_CSV}")
        return False

    # Extract Causality Log from Container
    print("\n🕵️ CAUSALITY LOG (Container Snapshot):")
    os.system('docker logs mcp_gemini_1 --tail 50 | grep -E "EVENT|RECOVERY|ORACLE|PLAN_D"')
    
    return True

if __name__ == "__main__":
    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    success = run_test("GRAND_PRIX_BASELINE", sabotage="none")
    
    if success:
        print("\n🏆 GRAND PRIX PHASE A ERFOLGREICH!")
    else:
        print("\n💀 GRAND PRIX PHASE A GESCHEITERT.")
        exit(1)
