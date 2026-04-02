import os
import json
import time
import argparse
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PENDING_DIR = os.path.join(BASE_DIR, "tasks", "pending")
os.makedirs(PENDING_DIR, exist_ok=True)

CANTONS = [
    "Aargau", "Appenzell Ausserrhoden", "Appenzell Innerrhoden", "Basel-Landschaft", 
    "Basel-Stadt", "Bern", "Fribourg", "Genève", "Glarus", "Graubünden", "Jura", 
    "Lucerne", "Neuchâtel", "Nidwalden", "Obwalden", "Schaffhausen", "Schwyz", 
    "Solothurn", "St. Gallen", "Thurgau", "Ticino", "Uri", "Valais", "Vaud", "Zug", "Zürich"
]

def inject_cantons(mini=False):
    target_cantons = CANTONS[:5] if mini else CANTONS
    print(f"💉 Injecting {'MINI ' if mini else 'FULL '}Canton-Grand-Prix into {PENDING_DIR}...")
    
    for i, canton in enumerate(target_cantons):
        name_clean = canton.lower().replace("-", "_").replace(".", "").replace(" ", "_").replace("è", "e")
        task_id = f"canton_{name_clean}"
        
        prompt = (
            f"Research the Swiss Canton: {canton}. Provide a structured list:\n"
            "1. Hauptort (Capital)\n"
            "2. Einwohnerzahl (aktuell)\n"
            "3. Beitrittsjahr zur Eidgenossenschaft\n"
            "4. Amtssprachen\n"
            "5. Wirtschaftliche Stärken (Kurzbeschreibung, maximal 2 Sätze)\n"
            f"Save the structured data into /app/workspace/canton_{name_clean}.txt."
        )
        
        task_data = {
            "task_id": task_id,
            "prompt": prompt,
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
            "session_id": f"session_canton_{name_clean}",
            "attempts": 0
        }
        
        file_path = os.path.join(PENDING_DIR, f"{task_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=4)
        
        print(f"   🚀 Injected: {task_id}")
        time.sleep(0.1)

    print(f"✅ Injection complete. {len(target_cantons)} tasks ready.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mini", action="store_true", help="Only inject 5 cantons for initial testing")
    args = parser.parse_args()
    
    inject_cantons(mini=args.mini)
