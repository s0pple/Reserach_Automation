import json
import os

# Configuration
TASKS_DIR = "tasks_v2/pending"
CANTONS = [
    ("Zürich", "ZH"), ("Bern", "BE"), ("Luzern", "LU"), ("Uri", "UR"),
    ("Schwyz", "SZ"), ("Obwalden", "OW"), ("Nidwalden", "NW"), ("Glarus", "GL"),
    ("Zug", "ZG"), ("Fribourg", "FR"), ("Solothurn", "SO"), ("Basel-Stadt", "BS"),
    ("Basel-Landschaft", "BL"), ("Schaffhausen", "SH"), ("Appenzell Ausserrhoden", "AR"),
    ("Appenzell Innerrhoden", "AI"), ("St. Gallen", "SG"), ("Graubünden", "GR"),
    ("Aargau", "AG"), ("Thurgau", "TG"), ("Ticino", "TI"), ("Vaud", "VD"),
    ("Valais", "VS"), ("Neuchâtel", "NE"), ("Genève", "GE"), ("Jura", "JU")
]

FIELDS = [
    "canton_name", "capital", "joined_confederation", 
    "head_of_government", "parliament_seats", 
    "population_latest", "source_urls"
]

def generate_tasks():
    if not os.path.exists(TASKS_DIR):
        os.makedirs(TASKS_DIR)
        print(f"Created directory: {TASKS_DIR}")

    for name, code in CANTONS:
        task_id = f"research_{code.lower()}"
        filename = f"{task_id}.json"
        filepath = os.path.join(TASKS_DIR, filename)
        
        # Construct the specialized prompt
        prompt = (
            f"Research the following structural data for Canton {name}: {', '.join(FIELDS)}. "
            f"Save the results EXACTLY as a raw JSON object in 'workspace/result_{code.lower()}.json'. "
            "CRITICAL: Do NOT use markdown code blocks (no ```json). Output ONLY the raw JSON string. "
            "The JSON must be valid and contain all requested fields. "
            "Ensure you verify the data against official sources."
        )

        task_data = {
            "task_id": task_id,
            "prompt": prompt,
            "status": "pending",
            "attempts": 0,
            "retry_limit": 3,
            "expected_file": f"workspace/result_{code.lower()}.json"
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=4, ensure_ascii=False)
        print(f"Generated: {filename}")
    
    print(f"Successfully generated {len(CANTONS)} tasks in {TASKS_DIR}.")

if __name__ == "__main__":
    generate_tasks()
