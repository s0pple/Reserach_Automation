import os
import json
import time
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PENDING_DIR = os.path.join(BASE_DIR, "tasks", "pending")
os.makedirs(PENDING_DIR, exist_ok=True)

def inject_dozen():
    print(f"💉 Starting 'Dirty Dozen' injection into {PENDING_DIR}...")
    
    cities = ["Zurich", "Geneva", "Basel", "Lausanne", "Bern", "Winterthur", "Lucerne", "St. Gallen", "Lugano", "Biel/Bienne", "Thun", "Koniz"]
    
    for i, city in enumerate(cities):
        task_id = f"stresstest_{i+1:03d}"
        task_data = {
            "task_id": task_id,
            "prompt": f"What is the current population of {city}, Switzerland? Save only the number into /app/workspace/{city.lower()}.txt",
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
            "session_id": f"session_stress_{task_id}"
        }
        
        file_path = os.path.join(PENDING_DIR, f"{task_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=4)
        
        print(f"   🚀 Injected: {task_id} ({city})")
        # Micro-sleep to ensure varying mtimes
        time.sleep(0.1)

    print("✅ Injection complete. 12 tasks ready for the 'Dirty Dozen' stresstest.")

if __name__ == "__main__":
    inject_dozen()
