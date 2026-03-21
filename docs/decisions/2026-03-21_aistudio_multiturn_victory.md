# Decision Record: AI Studio Multiturn & Stateful Playwright Strategy

## Context
During our implementation of the Google AI Studio controller, we faced major obstacles with dynamic UIs, Angular event suppression (e.g. locator.fill() not activating buttons), undocumented DOM shifts (<markdown-viewer> changed to <ms-text-chunk>), and Google account session drops.

## What Worked (The Winning Formulas)
We found the exact mechanics required to robustly automate Google AI Studio:
1. **Typing over Filling:** Instead of .fill(), we MUST use wait textarea.click(), wait textarea.clear(), and then wait page.keyboard.type(prompt). Only this triggers the internal Angular form validators that enable the "Run" button.
2. **Finding the Prompt Box:** The chat input is reliably found via page.locator("textarea").last.
3. **Triggering Generation:** Hitting the explicit Run button (page.locator("button").filter(has_text="Run").last.click()) works best. A fallback to page.keyboard.press("Control+Enter") serves as a safety net.
4. **Extracting Output:** Google changed the output DOM. We must strictly read the text from the _last_ inserted block: page.locator("ms-text-chunk").all()[-1].
5. **Session Architecture:** To simulate an API (Stateful), we reuse the SAME browser tab continuously. We loop send_prompt() and wait_for_response() without refreshing the page. This tricks the cloud LLM into retaining conversation history perfectly.
6. **VNC "Magic Touch":** A magic_touch_pause() function intercepts crashes, freezing the script for 15-30 seconds. This allows manual VNC intervention for simple fixes (like a random Cookie popup or login timeout) instead of hard failing.

## Outcome
The script 	est_multiturn.py fully validated this approach, running an uninterrupted 3-turn mathematical conversation where the LLM remembered variables from Turn 1 in Turn 3. 

## Moving Forward (MCP Structure)
We will consolidate this logic into **ONE** FastMCP server executable for AI Studio (src/mcp/server/main.py). The server will open a persistent tab upon startup and register two tools: start_new_chat() and send_message().
