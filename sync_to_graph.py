import asyncio
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Select
from src.modules.browser.intake.importer import ResearchIntake
from src.schema.research_state import ResearchState
from src.core.persistence import PersistenceManager
from src.core.llm import MockLLMClient, OpenAIClient

console = Console()

async def sync_manual_input():
    console.rule("[bold cyan]CLAWDBOT - Sync to Research Graph[/bold cyan]")
    
    # 1. Choose Source Type / Persona
    source_type = Select.ask(
        "Welche Quelle oder Persona hat diese Daten geliefert?",
        choices=["Critic", "Optimist", "Realist", "Mediator", "AI_Overview", "Brain_Plan", "Other"]
    )
    
    console.print(Panel(
        f"[bold yellow]Eingabe bereit für Quelle: {source_type}[/bold yellow]\n"
        "Füge jetzt den vollständigen Text aus Google AI Mode oder AI Studio Brain ein.\n"
        "Beende die Eingabe mit [bold]Enter[/bold], dann [bold]Strg+Z[/bold] (Windows) oder [bold]Strg+D[/bold] (Linux/Mac) und nochmals [bold]Enter[/bold].",
        title="Anleitung",
        border_style="blue"
    ))

    # 2. Read input from stdin
    try:
        lines = sys.stdin.readlines()
        raw_text = "".join(lines)
    except EOFError:
        raw_text = ""
    
    if len(raw_text.strip()) < 10:
        console.print("[red]❌ Fehler: Zu wenig Text zum Importieren.[/red]")
        return

    # 3. Load or Create Research State
    state_file = "research_state.json"
    if os.path.exists(state_file):
        state = PersistenceManager.load(state_file)
        console.print(f"🔄 Lade bestehenden Graphen: [dim]{state.research_intent}[/dim]")
    else:
        intent = Prompt.ask("Kein bestehender Graph gefunden. Was ist das Haupt-Forschungsziel?", default="analyze opportunities in vertical farming Switzerland")
        state = ResearchState(research_intent=intent)

    # 4. Process with AI Importer
    # We prepend the source type to give the LLM context
    contextual_text = f"SOURCE TYPE: {source_type}\n\nCONTENT:\n{raw_text}"
    
    llm = OpenAIClient() if os.getenv("OPENAI_API_KEY") else MockLLMClient()
    importer = ResearchIntake(llm)
    
    console.print(f"\n[bold magenta]🕸️ [Importer][/bold magenta] Verarbeite {len(raw_text)} Zeichen als [bold]{source_type}[/bold]...")
    
    # Capture nodes before to see what's new
    existing_node_ids = set(state.nodes.keys())
    
    new_node_ids = await importer.import_from_markdown(contextual_text, state)
    
    if not new_node_ids:
        console.print("[red]⚠️ Keine neuen Knoten konnten extrahiert werden.[/red]")
        return

    # 5. Save State
    PersistenceManager.save(state, state_file)
    console.print(f"✅ [green]Erfolg![/green] {len(new_node_ids)} neue Knoten zum Graphen hinzugefügt.\n")

    # 6. Show Results Table
    table = Table(title=f"Neu erstellte Knoten ({source_type})", border_style="cyan")
    table.add_column("Topic", style="bold white")
    table.add_column("Type", style="magenta")
    table.add_column("Confidence", justify="right", style="green")
    table.add_column("Status", style="yellow")

    for node_id in new_node_ids:
        node = state.nodes.get(node_id)
        if node:
            table.add_row(
                node.topic,
                node.node_type.value,
                f"{node.confidence_factors.composite_score:.2f}",
                node.status.value
            )

    console.print(table)
    console.print(f"\n[dim]Graph gespeichert in {state_file}[/dim]")

if __name__ == "__main__":
    try:
        asyncio.run(sync_manual_input())
    except KeyboardInterrupt:
        console.print("\n[red]Import abgebrochen.[/red]")
        sys.exit(0)
