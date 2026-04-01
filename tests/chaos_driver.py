import asyncio
import re

class ChaosDriver:
    """The Chaos Driver: Injects controlled failure scenarios into a Playwright page."""
    
    def __init__(self, page):
        self.page = page

    async def inject_ghost_click(self, label: str = "Run"):
        """Intercepts clicks on a button and prevents any action (Ghost Click)."""
        print(f"💉 [Chaos] Injecting Ghost Click on '{label}'...")
        await self.page.evaluate(f"""(label) => {{
            const btns = Array.from(document.querySelectorAll('button, ms-run-button'));
            const target = btns.find(b => b.innerText.includes(label) || b.textContent.includes(label));
            if (target) {{
                target.addEventListener('click', (e) => {{
                    console.log('💉 [Chaos] Ghost Click Intercepted!');
                    e.stopImmediatePropagation();
                    e.preventDefault();
                }}, true);
            }}
        }}""", label)

    async def inject_latency(self, delay_ms: int = 10000):
        """Injects a delay before any DOM mutation occurs after clicking."""
        print(f"💉 [Chaos] Injecting {delay_ms}ms Latency...")
        await self.page.evaluate(f"""(delay) => {{
            const originalAppend = Element.prototype.appendChild;
            Element.prototype.appendChild = function() {{
                const args = arguments;
                const self = this;
                setTimeout(() => {{
                    originalAppend.apply(self, args);
                }}, delay);
            }};
        }}""", delay_ms)

    async def inject_modal_blindness(self, text: str = "System Update"):
        """Injects a modal that blocks interaction but might be 'camouflaged'."""
        print(f"💉 [Chaos] Injecting Modal: '{text}'...")
        await self.page.evaluate(f"""(msg) => {{
            const modal = document.createElement('div');
            modal.id = 'chaos-modal';
            modal.style.position = 'fixed';
            modal.style.top = '20%';
            modal.style.left = '30%';
            modal.style.width = '400px';
            modal.style.height = '200px';
            modal.style.background = 'white';
            modal.style.border = '5px solid red';
            modal.style.zIndex = '999999';
            modal.innerHTML = `<h1>${{msg}}</h1><button id='chaos-close'>Dismiss</button>`;
            document.body.appendChild(modal);
            
            // Background overlay to block clicks
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100vw';
            overlay.style.height = '100vh';
            overlay.style.background = 'rgba(0,0,0,0.5)';
            overlay.style.zIndex = '999998';
            document.body.appendChild(overlay);

            document.getElementById('chaos-close').onclick = () => {{
                modal.remove();
                overlay.remove();
            }};
        }}""", text)

    async def simulate_partial_success(self):
        """Simulates a case where a modal is closed but the target (Run) is disabled for a while."""
        await self.inject_modal_blindness("Loading Context...")
        await self.page.evaluate("""() => {
            const runBtn = document.querySelector('ms-run-button button');
            if (runBtn) {
                runBtn.disabled = true;
                setTimeout(() => { runBtn.disabled = false; }, 8000);
            }
        }""")

    async def simulate_slow_stream(self, target_text: str = "This is a slow response..."):
        """ARE Phase 2: Injects a slow stream of text to simulate high-latency generation."""
        print(f"💉 [Chaos] Starting Slow Stream Simulation...")
        await self.page.evaluate(f"""(text) => {{
            const output = document.querySelector('ms-prompt-box textarea, textarea'); 
            if (!output) return;
            let i = 0;
            const interval = setInterval(() => {{
                output.value += text[i];
                output.dispatchEvent(new Event('input', {{ bubbles: true }}));
                i++;
                if (i >= text.length) clearInterval(interval);
            }}, 2000); // 1 char every 2s
        }}""", target_text)

    async def simulate_half_open_modal(self):
        """ARE Phase 2: Injects a transparent blocking layer (z-index trap)."""
        print(f"💉 [Chaos] Injecting Invisible Blocking Layer (z-index: 99999)...")
        await self.page.evaluate("""() => {
            const trap = document.createElement('div');
            trap.style.position = 'fixed';
            trap.style.top = '0';
            trap.style.left = '0';
            trap.style.width = '100vw';
            trap.style.height = '100vh';
            trap.style.zIndex = '99999';
            trap.style.pointerEvents = 'all'; 
            trap.style.background = 'transparent'; // Completely invisible
            document.body.appendChild(trap);
        }""")
