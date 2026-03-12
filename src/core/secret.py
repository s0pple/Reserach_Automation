import google.generativeai as genai
import sys # For stderr
import threading # Added for locking
import time # Added for backoff
import re # To parse retry times

# --- User Configuration ---
# User should edit these values
LLM_MODEL_NAME = "gemini-2.5-flash" # The specific high-speed version you requested
FALLBACK_MODEL_NAME = "gemini-1.5-flash"

_RAW_API_KEY_ENTRIES = [
    {"key": "AIzaSyDaK80_65j_dNnxw6YrENNaBGkXo1hCzLQ", "owner_info": "thomas müller - ai.artisery@gmail.com"},
    {"key": "AIzaSyA50UZ1eFzGFK0tAz3vbdo3nRwP_QoFCc8", "owner_info": "oliver gwerder - oliver.gwerder@gmail.com"},
    {"key": "AIzaSyDi7Cn85cdMgXB52VD1vOud8-GKJYrUv10", "owner_info": "cassie - cassie.blackw0d@gmail.com"},
    {"key": "AIzaSyBYZYU1MFEiGIDood7oqA15ai--IF80NfM", "owner_info": "Booknuggets - booknuggets.work@gmail.com"},
    {"key": "AIzaSyAOgospO-E8mxhh-RDQuhLru7Qs77nB0wU", "owner_info": "BaldyBoy - baldy.b0yyy@gmail.com"},
    {"key": "AIzaSyCkow2IIKQE5rCa72scfHjAjkUYp_JWLo4", "owner_info": "Peter - peter.p1rty@gmail.com"},
]
# --- End User Configuration ---

API_KEY_CONFIGS = [
    entry for entry in _RAW_API_KEY_ENTRIES
    if isinstance(entry, dict) and \
       entry.get("key") and \
       "YOUR_" not in str(entry.get("key")).upper() and \
       str(entry.get("key")).strip() and \
       entry.get("owner_info")
]

if not API_KEY_CONFIGS:
    print("FATAL:[Secret.py] No valid API key configurations found after filtering.", file=sys.stderr)
    raise ValueError("No valid API key configurations in Secret.py.")

_current_key_index = 0
_managed_llm_model = None
_current_model_name = LLM_MODEL_NAME
_API_KEY_LOCK = threading.Lock()

def _configure_model_with_key(key_index_to_try, model_name=_current_model_name):
    global _managed_llm_model, _current_key_index
    if not (0 <= key_index_to_try < len(API_KEY_CONFIGS)): return False
    key_config = API_KEY_CONFIGS[key_index_to_try]
    try:
        # print(f"[Secret.py] Configuring Key Index: {key_index_to_try} ({key_config['owner_info']}) for model: {model_name}")
        genai.configure(api_key=key_config["key"])
        _managed_llm_model = genai.GenerativeModel(model_name)
        _current_key_index = key_index_to_try
        return True
    except Exception as e:
        print(f"[Secret.py] Error with key {key_index_to_try}: {e}", file=sys.stderr)
        _managed_llm_model = None
        return False

def _initialize_or_attempt_rotation(is_rotation: bool, index_of_key_that_failed: int = -1, model_name=_current_model_name):
    num_available_keys = len(API_KEY_CONFIGS)
    start_search_from_idx = (_current_key_index + 1) % num_available_keys if is_rotation else 0
    for i in range(num_available_keys):
        key_idx_to_attempt = (start_search_from_idx + i) % num_available_keys
        if is_rotation and key_idx_to_attempt == index_of_key_that_failed: continue 
        if _configure_model_with_key(key_idx_to_attempt, model_name): return True
    return False

def generate_content_with_key_rotation(prompt_parts, generation_config=None, safety_settings=None, stream=False):
    global _managed_llm_model, _current_model_name
    with _API_KEY_LOCK:
        if _managed_llm_model is None:
            if not _initialize_or_attempt_rotation(False, -1, _current_model_name):
                raise RuntimeError("LLM model could not be initialized.")
        
        # We retry infinitely if it's purely a rate limit, waiting as Google commands
        while True:
            max_wait_time_seen = 0
            
            for _ in range(len(API_KEY_CONFIGS)):
                try:
                    gen_params = {}
                    if generation_config: gen_params['generation_config'] = generation_config
                    if safety_settings: gen_params['safety_settings'] = safety_settings
                    if stream: gen_params['stream'] = stream
                    
                    time.sleep(1.0) 
                    return _managed_llm_model.generate_content(prompt_parts, **gen_params)
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    print(f"[Secret.py] ⚠️ Error with Key {_current_key_index}: {e}", file=sys.stderr)

                    if any(x in error_msg for x in ["quota", "exhausted", "429", "permission", "404", "too many requests", "rate limit"]):                        # Parse the required wait time from Google's error message (e.g. "Please retry in 49.6s")
                        wait_match = re.search(r"retry in (\d+\.?\d*)s", error_msg)
                        if wait_match:
                            wait_sec = float(wait_match.group(1))
                            max_wait_time_seen = max(max_wait_time_seen, wait_sec)
                        
                        print(f"[Secret.py] 🔄 Key {_current_key_index} blocked. Rotating...", file=sys.stderr)
                        _initialize_or_attempt_rotation(True, _current_key_index, _current_model_name)
                        continue
                    else:
                        print(f"[Secret.py] ❌ Unrecoverable API Error: {str(e)}", file=sys.stderr)
                        raise e
            
            # If we exhausted ALL keys in this loop, we MUST wait.
            wait_time = int(max_wait_time_seen) + 2 if max_wait_time_seen > 0 else 60
            print(f"\n[Secret.py] ⏳ All keys burned. Enforcing Google Rate Limit... Pausing pipeline for {wait_time} seconds. DO NOT CANCEL!", file=sys.stderr)
            time.sleep(wait_time)
            print(f"[Secret.py] 🚀 Resuming pipeline...", file=sys.stderr)

_initialize_or_attempt_rotation(False)
