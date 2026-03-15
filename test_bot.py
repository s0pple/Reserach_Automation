import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder

async def main():
    try:
        app = ApplicationBuilder().token("8666206974:AAFP3Z2vLe6bDqZ1QnFlkb_XsnSQDvaQxVo").build()
        print("Application built.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
