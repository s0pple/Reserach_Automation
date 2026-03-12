import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import argparse
import re
import sys
from rich.console import Console
from src.modules.browser.aistudio_provider import AIStudioProvider
from src.modules.browser.google_ai_provider import GoogleAIProvider

console = Console()

MASTER_PROMPT = """
Rolle: Du bist das zentrale "Research Brain" für das Clawdbot-Projekt.
Dein Ziel: Du koordinierst eine komplexe Recherche über "{goal}".
Dein Team: Du arbeitest mit mehreren Google-Suche (AI Mode) Instanzen, die unterschiedliche Rollen einnehmen (Critic, Optimist, Realist, Mediator).

Deine Aufgabe in jeder Iteration:
1. Analysiere den aktuellen Stand.
2. Definiere die nächste strategische Richtung.
3. Schreibe für genau ZWEI Personas jeweils einen spezifischen Prompt, den diese in der Google Suche ausführen sollen.
4. WICHTIG: Formatiere die Prompts für die Personas EXAKT so, damit mein Script sie maschinell auslesen kann:
```[Rolle]
[Der genaue Such-Prompt, der die Rollenanweisung und die Suchanfrage enthält]
```
Beispiel:
```Critic
Du bist ein extremer Kritiker. Suche nach: Risiken von Vertical Farming in der Schweiz.
```

Wenn du das verstanden hast, starte jetzt mit der ersten Analyse und gib mir die ersten zwei Prompts in dem verlangten Code-Block Format.
"""

async def run_ultimate_auto(goal: str, iterations: int, visible: bool):
    console.rule("[bold cyan]ULTIMATE ZERO-COST AUTO-RESEARCH[/bold cyan]")
    
    # 1. Start AI Studio (The Brain)
    brain = AIStudioProvider(headless=not visible, persona="brain")
    console.print("[dim]Starte Google AI Studio als zentrales Gehirn...[/dim]")
    await brain.start_session()
    
    # Send Master Prompt
    brain_prompt = MASTER_PROMPT.replace("{goal}", goal)
    brain_response = await brain.chat(brain_prompt)
    
    for i in range(1, iterations + 1):
        console.rule(f"[bold magenta]ITERATION {i}/{iterations}[/bold magenta]")
        console.print(f"[bold cyan]Brain sagt:[/bold cyan]\n{brain_response}\n")
        
        # Parse the prompts from the Brain's response
        # Matches ```Role\nPrompt\n```
        tasks = re.findall(r"```([a-zA-Z]+)\n(.*?)```", brain_response, re.DOTALL)
        
        if not tasks:
            console.print("[red]⚠️ Konnte keine formatierten Prompts vom Brain auslesen. Breche ab oder versuche manuell fortzufahren.[/red]")
            break
            
        feedback_for_brain = f"--- ERGEBNISSE AUS ITERATION {i} ---\n\n"
        
        # 2. Execute each prompt with Google AI Workers
        for role, prompt in tasks:
            role = role.strip()
            prompt = prompt.strip()
            
            console.print(f"🚀 [bold yellow]Starte Worker für Rolle:[/bold yellow] {role}")
            console.print(f"✍️ [dim]Prompt: {prompt[:100]}...[/dim]")
            
            worker = GoogleAIProvider(headless=not visible, persona=f"research_{role.lower()}")
            try:
                result = await worker.search_and_extract(prompt)
                console.print(f"✅ [green]Ergebnis extrahiert ({len(result)} Zeichen)[/green]")
                feedback_for_brain += f"ERGEBNIS VON PERSONA [{role}]:\n{result}\n\n"
            except Exception as e:
                console.print(f"❌ [red]Fehler beim Worker {role}: {e}[/red]")
                feedback_for_brain += f"ERGEBNIS VON PERSONA [{role}]:\nFehler bei der Suche.\n\n"
                
        # 3. Feed results back to Brain
        console.print("🧠 [dim]Füttere die Ergebnisse zurück ins Brain...[/dim]")
        feedback_prompt = (
            f"Hier sind die Ergebnisse der Google Suchen:\n\n{feedback_for_brain}\n\n"
            "Bitte analysiere diese, integriere sie in den Forschungsplan und gib mir die nächsten "
            "zwei Prompts im exakt gleichen ```[Rolle]...``` Format."
        )
        
        brain_response = await brain.chat(feedback_prompt)

    console.rule("[bold green]Forschung abgeschlossen![/bold green]")
    await brain.close()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("goal", type=str, help="Das Forschungsziel")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--visible", action="store_true", default=True, help="Browser sichtbar machen")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_ultimate_auto(args.goal, args.iterations, args.visible))
    except KeyboardInterrupt:
        console.print("\n[red]Abgebrochen vom User.[/red]")
        sys.exit(0)
