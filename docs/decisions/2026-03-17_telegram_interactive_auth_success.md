# 📝 Decision Log: Telegram Interactive Auth & Remote Control

**Date:** 2026-03-17
**Status:** ✅ Validated / 🚧 In Progress (Remote Control)
**Context:** Authentication with Google AI Studio via Headless Browser controlled by Telegram.

## 1. The Breakthrough: Interactive Auth via Telegram
We successfully implemented a "Human-in-the-loop" authentication flow that solves the "Captcha/2FA" problem for headless bots.

### The Flow:
1.  **Trigger:** User starts session via Telegram (`/cli start python3 scripts/setup_cassie.py`).
2.  **Execution:** The bot launches a `tmux` session executing a Playwright script.
3.  **Feedback:** The script sends screenshots to the Telegram Chat (`send_photo`).
4.  **Interaction:** The script halts at critical points (2FA, Password) and waits for `input()`.
5.  **Control:** The user replies in Telegram (which is piped to the script's `stdin`).
6.  **Success:** The browser session (cookies/storage) is persisted to `/app/browser_sessions/account_cassie`.

### Evidence (User Feedback):
> "Mein Orchestrator: 🖼 🔒 Login Required ... 🖼 🔑 Password Submitted ... er hat mir immer bilder geschickt und so..."

## 2. Next Step: "Live Remote Control"
The user now wants to control the active session *after* login (e.g., "Create new chat", "Switch to Gemini 1.5 Pro").

### The Solution: `live_aistudio.py`
We are moving from a linear "Setup Script" to a persistent "Controller Loop".

**Architecture:**
- **Persistent Context:** Loads the authenticated `account_cassie` profile.
- **Command Loop:** A `while True` loop that listens for natural language commands.
- **Action Mapping:**
    - `new` / `neu` -> Triggers "Create New" UI flow.
    - `model <name>` -> Opens Model Selector and selects model.
    - `prompt <text>` -> Types into the prompt box.
- **Feedback:** Sends a screenshot after every action to confirm state.

This effectively turns Telegram into a "Remote Terminal" for the GUI-based AI Studio, bypassing API limitations by using the actual web interface.
