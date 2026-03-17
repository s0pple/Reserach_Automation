import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from src.interfaces.telegram.bot import handle_universal, analyze_intent, ToolRegistry, gemini_web_nav_tool, WebNavArguments, interactive_session_tool, SessionParams, general_agent_tool, GeneralAgentParams, get_project_status, ProjectParams, run_cli_command, CLIParams, take_watch, WatchParams, ai_studio_controller, AIStudioParams, developer_reasoning_tool, DeveloperArguments, trigger_job, ResearchParams

logging.basicConfig(level=logging.INFO)

async def test_simulate_telegram_message():
    print("🧪 Simulating 'handle_universal' with mock update...")

    # Mock Update and Context
    update = MagicMock()
    update.effective_user.id = 123456789
    update.effective_chat.id = 123456789
    update.message.text = "Check den Bitcoin Preis auf CoinMarketCap"
    update.message.reply_text = AsyncMock()
    
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.delete_message = AsyncMock()
    context.bot.send_photo = AsyncMock()

    # Mock analyze_intent (Router)
    # We want to see what happens when the router returns a valid tool
    # But wait, analyze_intent uses the REAL LLM if we don't mock it.
    # To reproduce the exact flow, let's allow it to use the real router if possible, 
    # OR mock the router return value to check if the tool invocation works.
    
    # Let's first test the tool invocation directly with params the router SHOULD return.
    params = {"goal": "Check Bitcoin Price on CoinMarketCap"}
    tool_name = "web_nav_tool"
    
    print(f"Testing tool invocation: {tool_name} with {params}")
    
    # Manually invoke tool like handle_universal does
    ToolRegistry.register_tool("web_nav_tool", "Autonomous web agent", gemini_web_nav_tool, WebNavArguments)
    
    tool_info = ToolRegistry.get_tool(tool_name)
    if not tool_info:
        print("❌ Tool not found in registry!")
        return

    # Add callback
    async def telegram_callback(msg):
        print(f"Callback received: {msg}")
    
    params["telegram_callback"] = telegram_callback
    
    try:
        # This is where it crashes in production
        result = await tool_info.func(**params)
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"💥 Exception in tool execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure allowed IDs includes our mock ID
    import os
    os.environ["ALLOWED_TELEGRAM_USER_IDS"] = "123456789"
    asyncio.run(test_simulate_telegram_message())
