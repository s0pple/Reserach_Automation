import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import argparse
import sys
from rich.console import Console
from src.modules.browser.google_ai_provider import GoogleAIProvider

console = Console()

async def run_single_persona_step(role: str, prompt: str, visible: bool = True):
    console.rule(f"[bold cyan]Clawdbot Worker: {role}[/bold cyan]")
    
    # Wir nutzen für jede Rolle einen eigenen Browser-Persona (isolierte Sessions)
    persona_name = f"research_{role.lower()}"
    browser = GoogleAIProvider(headless=not visible, persona=persona_name)
    
    console.print(f"🚀 [bold]Rolle:[/bold] {role}")
    console.print(f"✍️ [bold]Input Prompt:[/bold] {prompt[:100]}...")
    
    # Ausführung in Google AI Mode
    result = await browser.search_and_extract(prompt)
    
    console.rule("[bold green]Ergebnis extrahiert[/bold green]")
    console.print(result)
    console.print("\n[dim]Kopiere diesen Text zurück in dein AI Studio Brain.[/dim]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", type=str, required=True, help="Z.B. Critic, Optimist, Realist")
    parser.add_argument("--prompt", type=str, required=True, help="Der volle Prompt vom Brain")
    parser.add_argument("--visible", action="store_true", default=True)
    
    args = parser.parse_args()
    asyncio.run(run_single_persona_step(args.role, args.prompt, args.visible))
