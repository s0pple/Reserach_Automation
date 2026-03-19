import asyncio
from telegram import Bot

# Ersetze dies durch deinen tatsächlichen Bot Token und Chat ID!
TOKEN = "DEIN_BOT_TOKEN_HIER"
CHAT_ID = "DEINE_CHAT_ID_HIER"

async def test_telegram_message():
    print("🤖 Initialisiere Bot...")
    bot = Bot(token=TOKEN)
    
    print("📤 Sende Testnachricht...")
    try:
        await bot.send_message(chat_id=CHAT_ID, text="🚀 **Conveyor Belt Test-Ping!** Funktioniert die Verbindung?")
        print("✅ Nachricht erfolgreich gesendet!")
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    asyncio.run(test_telegram_message())
