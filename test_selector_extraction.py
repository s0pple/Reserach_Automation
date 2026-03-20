from bs4 import BeautifulSoup

with open("aistudio_dump.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Try to find the run button
# Based on grep: <button ... class="run-button ..."> Run Ctrl </button>
# It seems the text is "Run Ctrl <arrow>" inside.

buttons = soup.find_all("button")
print(f"Found {len(buttons)} buttons.")

for i, btn in enumerate(buttons):
    text = btn.get_text(strip=True)
    if "Run" in text:
        print(f"\n--- Candidate {i} ---")
        print(f"Text: '{text}'")
        print(f"Attributes: {btn.attrs}")
        print(f"HTML: {btn.prettify()[:200]}...")
