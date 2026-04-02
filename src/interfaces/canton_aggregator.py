import os
import json
import csv
import re
import glob

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMPLETED_DIR = os.path.join(BASE_DIR, "tasks", "completed")
OUTPUT_CSV = os.path.join(BASE_DIR, "workspace", "swiss_cantons_summary.csv")

def parse_canton_data(text):
    """
    Parses the structured list from the agent's output.
    Expecting:
    1. Hauptort: ...
    2. Einwohnerzahl: ...
    3. Beitrittsjahr: ...
    4. Amtssprachen: ...
    5. Wirtschaftliche Stärken: ...
    """
    data = {
        "hauptort": "MISSING",
        "einwohner": "MISSING",
        "beitrittsjahr": "MISSING",
        "amtssprachen": "MISSING",
        "wirtschaft": "MISSING"
    }
    
    # Regex patterns for the 5 points
    patterns = {
        "hauptort": r"(?:1\.|Hauptort)[:\s]+([^\n]+)",
        "einwohner": r"(?:2\.|Einwohnerzahl)[:\s]+([^\n]+)",
        "beitrittsjahr": r"(?:3\.|Beitrittsjahr)[:\s]+([^\n]+)",
        "amtssprachen": r"(?:4\.|Amtssprachen)[:\s]+([^\n]+)",
        "wirtschaft": r"(?:5\.|Wirtschaftliche Stärken)[:\s]+([^\n]+)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()
            
    return data

def validate_year(year_str):
    """Sanity check for the Swiss Confederation entry year."""
    try:
        # Extract the first 4-digit number
        match = re.search(r"\d{4}", str(year_str))
        if match:
            year = int(match.group(0))
            if 1291 <= year <= 1848:
                return True
    except: pass
    return False

def extract_number(text):
    """Extracts and normalizes numbers like 700'000, 700k, 1.2M, etc.
    Always takes the FIRST match found in the text.
    """
    if not text or text == "MISSING": return None
    
    # 1. Handle common suffixes before stripping separators
    text_lower = text.lower()
    multiplier = 1
    if "mio" in text_lower or " m" in text_lower: multiplier = 1000000
    elif " k" in text_lower or "tsd" in text_lower: multiplier = 1000
    
    # 2. Clean Swiss separators (' . )
    clean = re.sub(r"['\s\.]", "", text)
    
    # 3. Find first digit sequence
    match = re.search(r"\d+", clean)
    if not match: return None
    
    val = int(match.group(0)) * multiplier
    return val

def validate_population(pop_v):
    """Plausibility check for Swiss Canton population (15k - 1.6M)."""
    if pop_v is None: return False
    return 15000 <= pop_v <= 1700000

def aggregate():
    print(f" Starting aggregation from {COMPLETED_DIR}...")
    files = glob.glob(os.path.join(COMPLETED_DIR, "canton_*.json"))
    
    rows = []
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                task = json.load(f)
            
            task_id = task.get("task_id")
            log_full = task.get("log_output", "")
            parsed = parse_canton_data(log_full)
            
            # Sanity Checks
            year_v = extract_number(parsed["beitrittsjahr"])
            pop_v = extract_number(parsed["einwohner"])
            
            year_ok = validate_year(year_v)
            pop_ok = validate_population(pop_v)
            
            alerts = []
            if not year_ok: alerts.append("YEAR_HAL")
            if not pop_ok: alerts.append("POP_HAL")
            if parsed["hauptort"] == "MISSING": alerts.append("MISSING_DATA")
            
            status_audit = "OK" if not alerts else f"ALERT: {', '.join(alerts)}"
            
            # Formatting
            wirtschaft_clean = parsed["wirtschaft"].replace("\n", " ")
            if len(wirtschaft_clean) > 500:
                wirtschaft_clean = wirtschaft_clean[:497] + "..."

            row = {
                "Canton_ID": task_id,
                "Status": task.get("status"),
                "Audit": status_audit,
                "Hauptort": parsed["hauptort"],
                "Einwohner": parsed["einwohner"],
                "Beitrittsjahr": parsed["beitrittsjahr"],
                "Amtssprachen": parsed["amtssprachen"],
                "Wirtschaft": wirtschaft_clean,
                "Attempts": task.get("attempts", 1),
                "Duration": task.get("duration_sec"),
                "Log_File": f"{task_id}.log"
            }
            rows.append(row)
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")

    # Write CSV
    if rows:
        keys = rows[0].keys()
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(rows)
        print(f"✅ Aggregation complete. {len(rows)} rows written to {OUTPUT_CSV}")
    else:
        print("⚠️ No canton tasks found in completed folder.")

if __name__ == "__main__":
    aggregate()
