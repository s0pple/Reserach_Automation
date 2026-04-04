import json
import os
import sys

# Required fields for each canton research result
REQUIRED_FIELDS = [
    "canton_name",
    "capital",
    "joined_confederation",
    "head_of_government",
    "parliament_seats",
    "population_latest",
    "source_urls"
]

def clean_json_string(s):
    """Strips possible markdown code blocks from the string."""
    s = s.strip()
    if s.startswith("```"):
        # Remove starting ```json or ```
        if s.startswith("```json"):
            s = s[7:]
        else:
            s = s[3:]
        # Remove ending ```
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()

def validate_json_data(data, expected_task_id=None):
    """
    Validates the JSON structure and content.
    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Root is not a dictionary/object"
    
    # 1. Identity Check (Task-ID Match)
    if expected_task_id:
        found_id = data.get("task_id")
        if found_id != expected_task_id:
            return False, f"Identity Mismatch: Expected {expected_task_id}, found {found_id}"
    
    # 2. Schema Check (Required Fields)
    for field in REQUIRED_FIELDS:
        if field not in data:
            return False, f"Missing required field: '{field}'"
        
        value = data[field]
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, list) and not value):
            return False, f"Field '{field}' is empty or null"
            
    return True, "Valid"

def validate_file(file_path, expected_task_id=None):
    """
    Reads, cleans, and validates a JSON file.
    Returns (is_valid, error_message, cleaned_data).
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}", None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        
        cleaned_content = clean_json_string(raw_content)
        data = json.loads(cleaned_content)
        
        is_valid, msg = validate_json_data(data, expected_task_id=expected_task_id)
        return is_valid, msg, data
    except json.JSONDecodeError as e:
        return False, f"JSON Decode Error: {e}", None
    except Exception as e:
        return False, f"Unexpected Error: {e}", None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python output_validator.py <file_path>")
        sys.exit(1)
        
    target_file = sys.argv[1]
    valid, message, _ = validate_file(target_file)
    
    if valid:
        print(f"PASS: {target_file}")
        sys.exit(0)
    else:
        print(f"FAIL: {target_file} - {message}")
        sys.exit(1)
