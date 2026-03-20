import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Literal

STATUS_FILE = "account_status.json"

AccountStatus = Literal["active", "limited", "cooldown"]

class StatusManager:
    """
    Manages the status of Google accounts (active vs. limited).
    Persists state to a JSON file to survive restarts.
    """
    
    def __init__(self, storage_path: str = STATUS_FILE):
        self.storage_path = storage_path
        self._data = self._load()

    def _load(self) -> Dict:
        if not os.path.exists(self.storage_path):
            return {}
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        with open(self.storage_path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get_status(self, account_id: str) -> AccountStatus:
        """Checks status and auto-resets if cooldown expired."""
        info = self._data.get(account_id, {})
        status = info.get("status", "active")
        reset_at = info.get("reset_at")

        if status in ["limited", "cooldown"] and reset_at:
            if datetime.now().isoformat() > reset_at:
                print(f"[StatusManager] Cooldown expired for {account_id}. Resetting to active.")
                self.set_status(account_id, "active")
                return "active"
        
        return status

    def set_status(self, account_id: str, status: AccountStatus, cooldown_hours: int = 1):
        """Updates status. If 'limited', sets a reset timestamp."""
        reset_time = None
        if status in ["limited", "cooldown"]:
            reset_time = (datetime.now() + timedelta(hours=cooldown_hours)).isoformat()
            
        self._data[account_id] = {
            "status": status,
            "reset_at": reset_time,
            "last_updated": datetime.now().isoformat()
        }
        self._save()
        print(f"[StatusManager] Account {account_id} set to {status} (Reset: {reset_time})")

    def get_next_available_account(self, accounts: list[str]) -> Optional[str]:
        """Finds the first account that is 'active'."""
        for acc in accounts:
            if self.get_status(acc) == "active":
                return acc
        return None
