import asyncio
from telegram import Bot
import os

async def main():
    bot = Bot("8666206974:AAFP3Z2vLe6bDqZ1QnFlkb_XsnSQDvaQxVo")
    try:
        with open("test_screenshot.png", "rb") as f:
            await bot.send_photo(chat_id="8505867777", photo=f, caption="Test Photo", parse_mode='Markdown')
        print("Success")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
