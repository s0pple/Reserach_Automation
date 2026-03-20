# How to Run Automatic Deep Research (Windows)

This module allows the system to automatically trigger "Deep Research" tools (Gemini AI Studio / Perplexity) and import the results into the structured knowledge graph.

### 1. Prerequisites
Open PowerShell in the project root:
```powershell
# Create venv if not done
python -m venv venv
.\venv\Scripts\activate

# Install Playwright
pip install playwright
playwright install chromium
```

### 2. First-Time Setup (Login)
To log in to Google or Perplexity, you need to run the browser in **visible mode** once to save your session:
1. Open `src/modules/browser/provider.py`.
2. Temporarily set `headless=False` in the `BrowserSearchProvider` constructor.
3. Run a test script that calls `trigger_deep_research`.
4. When the browser opens, **manually log in** to your account.
5. Close the browser. Your session is now saved in the `browser_session/` folder.

### 3. Hands-Free Execution
From now on, you can set `headless=True` and the system will log in automatically using your saved cookies.

### 4. Running the Loop
The `Collector` agent will now use the browser whenever it needs deep exploration. You can also manually import reports:
```python
from src.modules.browser.provider import BrowserSearchProvider
from src.modules.browser.intake.importer import ResearchIntake

# 1. Trigger Automation
browser = BrowserSearchProvider(headless=True)
report = await browser.trigger_deep_research("Deep Research Prompt", tool="gemini")

# 2. Extract into Graph
importer = ResearchIntake(llm)
await importer.import_from_markdown(report, state)
```
