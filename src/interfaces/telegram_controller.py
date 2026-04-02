import os
import time
import json
import requests
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PENDING_DIR = os.path.join(BASE_DIR, "tasks", "pending")
os.makedirs(PENDING_DIR, exist_ok=True)

# Configuration (To be filled by user)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_USER_ID = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "") 

def poll_updates(last_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id + 1}&timeout=30"
    try:
        r = requests.get(url, timeout=40)
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception as e:
        print(f"📡 [Telegram] Polling error: {e}")
    return []

def queue_task(prompt, user_id):
    task_id = f"tg_{int(time.time())}"
    task_data = {
        "task_id": task_id,
        "prompt": prompt,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "session_id": f"tg_session_{task_id}",
        "metadata": {
            "source": "telegram",
            "user_id": user_id
        }
    }
    
    file_path = os.path.join(PENDING_DIR, f"{task_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=4)
    print(f"📥 [Telegram] Queued task: {task_id}")
    return task_id

def main():
    print("🤖 [Telegram] Controller started. Listening for research commands...")
    last_id = 0
    while True:
        updates = poll_updates(last_id)
        for update in updates:
            last_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "")
            user_id = str(message.get("from", {}).get("id", ""))
            
            # Security Check
            if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
                print(f"🚫 [Telegram] Unauthorized access from {user_id}")
                continue
                
            if text:
                print(f"✨ [Telegram] Received: {text} from {user_id}")
                tid = queue_task(text, user_id)
                # Confirmation (Optional: Send message back)
                # requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={user_id}&text=Task {tid} queued.")
                
        time.sleep(2)

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ [Telegram] Please set TELEGRAM_BOT_TOKEN environment variable.")
    else:
        try:
            main()
        except KeyboardInterrupt:
            print("\n🛑 [Telegram] Stopped.")
