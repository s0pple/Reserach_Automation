"""
Debug-Skript: Ruft debug_page über den MCP Container direkt ab.
Damit sehen wir URL und Selector-Counts der aktuellen Browser-Seite.
"""
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack

async def main():
    url = "http://localhost:8001/sse"
    async with AsyncExitStack() as stack:
        sse_obj = await stack.enter_async_context(sse_client(url))
        session = await stack.enter_async_context(ClientSession(sse_obj[0], sse_obj[1]))
        await session.initialize()

        result = await session.call_tool("debug_page", {"session_id": "diag_001"})
        if result.content:
            print(result.content[0].text)
        else:
            print("Kein Result zurückgekommen.")

asyncio.run(main())
