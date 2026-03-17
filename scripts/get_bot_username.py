import os
import asyncio
from telegram import Bot

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: No bot token found.")
        return
    bot = Bot(token)
    me = await bot.get_me()
    print(f"@{me.username}")

if __name__ == "__main__":
    asyncio.run(main())
