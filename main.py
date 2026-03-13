import argparse
import sys
import logging

# Configure basic logging for the root process
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("OrchestratorMain")

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
    # try:
    #     from src.interfaces.cli.main import main as cli_main
    #     cli_main()
    # except ImportError as e:
    #     logger.error(f"Failed to load CLI module: {e}")
    #     sys.exit(1)
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
    
    args = parser.parse_args()
    
    if args.mode == 'telegram':
        start_telegram_bot()
    elif args.mode == 'cli':
        start_cli()

if __name__ == "__main__":
    main()
