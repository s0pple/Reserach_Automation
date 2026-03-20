import argparse
import sys
import logging
import asyncio

# Configure basic logging for the root process
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("OrchestratorMain")

async def run_automated_research(topic: str, job_id: str, profile: str):
    """
    Executes a research task directly (e.g., when launched via job_launcher.py).
    """
    logger.info(f"🚀 Starting Automated Research for Job: {job_id}")
    logger.info(f"🔍 Topic: {topic}")
    logger.info(f"📁 Profile: {profile}")
    
    try:
        from src.tools.web.qwen_researcher import qwen_research_tool
        result = await qwen_research_tool(topic=topic, wait_minutes=2)
        
        if result.get("success"):
            logger.info(f"✅ Research completed for {job_id}.")
        else:
            logger.error(f"❌ Research failed for {job_id}: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Error during automated research: {e}")
        sys.exit(1)

def start_telegram_bot():
    """Starts the Telegram Command Center."""
    logger.info("Starting Telegram Interface...")
    try:
        from src.interfaces.telegram.bot import main as bot_main
        bot_main()
    except ImportError as e:
        logger.error(f"Failed to load Telegram bot module: {e}")
        sys.exit(1)

def start_cli():
    """Starts the Command Line Interface (Placeholder)."""
    logger.info("Starting CLI Interface...")
    print("CLI Interface is currently under construction in V2 Architecture.")

def main():
    parser = argparse.ArgumentParser(description="Research Automation Orchestrator (God-Container Edition)")
    parser.add_argument(
        '--mode', 
        type=str, 
        choices=['telegram', 'cli'], 
        default='cli',
        help='The interface mode to start (default: cli)'
    )
    
    # Phalanx 2.0 flags
    parser.add_argument('--topic', type=str, help='Topic for automated research')
    parser.add_argument('--job-id', type=str, help='Unique ID for this background job')
    parser.add_argument('--profile', type=str, help='Path to the browser profile to use')
    
    args = parser.parse_args()
    
    if args.topic and args.job_id:
        # If topic and job-id are provided, we run in automated background mode
        asyncio.run(run_automated_research(args.topic, args.job_id, args.profile))
    elif args.mode == 'telegram':
        start_telegram_bot()
    elif args.mode == 'cli':
        start_cli()

if __name__ == "__main__":
    main()
