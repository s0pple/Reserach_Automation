import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import argparse
import sys
from rich.console import Console

from src.core.llm import MockLLMClient, OpenAIClient
from src.modules.browser.google_ai_provider import GoogleAIProvider

console = Console()

async def iterative_research_loop(goal: str, persona: str, max_iterations: int = 3, headless: bool = False):
    console.rule(f"[bold cyan]Starting Iterative AI Research Loop[/bold cyan]")
    console.print(f"🎯 [bold]Goal:[/bold] {goal}")
    console.print(f"🎭 [bold]Persona:[/bold] {persona}")
    
    # Check if OpenAI API key is available, else use Mock (for testing)
    import os
    if os.getenv("OPENAI_API_KEY"):
        console.print("[green]Using OpenAI API for logic.[/green]")
        llm = OpenAIClient(model="gpt-4o-mini")
    else:
        console.print("[yellow]Using MockLLM (Set OPENAI_API_KEY for real intelligence).[/yellow]")
        llm = MockLLMClient()

    browser_ai = GoogleAIProvider(headless=headless, persona="google_searcher")
    
    # The accumulated memory of the research
    context_memory = f"Initial Goal: {goal}\n\n"
    
    # Define the system prompt for the Persona
    persona_prompt = f"""
    You are an AI autonomous agent with the following persona: {persona}.
    Your task is to reach the 'Initial Goal' by performing iterative Google searches.
    
    Instructions:
    1. Read the Context Memory (which contains past searches and their results).
    2. Analyze if the Goal has been reached. 
    3. If the Goal is reached, respond with the exact string: "DONE: [Summary of final answer]"
    4. If the Goal is NOT reached, formulate the NEXT best Google search query to find the missing information. 
       Respond with the exact string: "SEARCH: [your search query]"
    """

    for iteration in range(1, max_iterations + 1):
        console.print(f"\n[bold magenta]--- Iteration {iteration}/{max_iterations} ---[/bold magenta]")
        
        # 1. Ask the Persona LLM what to do next based on memory
        prompt = f"Context Memory:\n{context_memory}\n\nWhat is your next action?"
        
        console.print("[dim]🧠 Persona is thinking...[/dim]")
        llm_response = await llm.generate(prompt, system_prompt=persona_prompt)
        
        if "DONE:" in llm_response:
            console.print("[bold green]🏁 Goal Reached![/bold green]")
            final_answer = llm_response.split("DONE:")[-1].strip()
            console.print(f"\n[bold]Final Synthesis:[/bold]\n{final_answer}")
            break
            
        elif "SEARCH:" in llm_response:
            # Extract the search query
            next_query = llm_response.split("SEARCH:")[-1].strip()
            console.print(f"🔍 [bold yellow]Persona decided to search:[/bold yellow] {next_query}")
            
            # 2. Execute the Search via Google AI Overview
            search_result = await browser_ai.search_and_extract(next_query)
            
            # Print a snippet of the result
            snippet = search_result[:300].replace('\n', ' ') + "..."
            console.print(f"📄 [dim]Result Snippet: {snippet}[/dim]")
            
            # 3. Add to memory for the next loop
            context_memory += f"\n--- Iteration {iteration} ---\n"
            context_memory += f"Query: {next_query}\n"
            context_memory += f"Result: {search_result}\n"
            
        else:
            console.print(f"[red]⚠️ LLM returned unexpected format:[/red] {llm_response}")
            # Force a fallback search
            next_query = f"{goal} more details"
            search_result = await browser_ai.search_and_extract(next_query)
            context_memory += f"\nQuery: {next_query}\nResult: {search_result}\n"

    console.rule("[bold cyan]Research Complete[/bold cyan]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iterative Google AI Mode Research")
    parser.add_argument("goal", type=str, help="The research goal")
    parser.add_argument("--persona", type=str, default="A highly critical fact-checker who always looks for contradictions.", help="The persona of the driving LLM")
    parser.add_argument("--iterations", type=int, default=3, help="Max loops")
    parser.add_argument("--visible", action="store_true", help="Run browser visibly")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(iterative_research_loop(
            goal=args.goal, 
            persona=args.persona, 
            max_iterations=args.iterations,
            headless=not args.visible
        ))
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
