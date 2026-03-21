import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import anyio

async def trigger():
    try:
        print('Verbinde mit Container 2...')
        # Verwende localhost:8000 hier, weil das Skript IM Container ausgeführt wird
        async with sse_client('http://localhost:8000/sse') as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                print('Sende Dummy Prompt...')
                await session.call_tool('ask_gemini', arguments={'session_id': 'login_session', 'prompt': 'Gebe mir nur das Wort BEREIT zurueck.'})
    except Exception as e:
        print('Fertig/Fehler:', e)

if __name__ == '__main__':
    anyio.run(trigger)
