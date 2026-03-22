- Ogham ("OH-um") an open source MCP server that gives your AI agents persistent, shared memory. "https://www.youtube.com/watch?v=gY0lrAUjZsA" Ogham ("OH-um") is an open source MCP server that gives your AI agents shared, persistent memory. Store something in Claude Code, pull it up in Cursor or any MCP client. Same database, same knowledge graph.

What you'll see in this demo:
Storing memories with auto-tagging and duplicate detection
Searching by meaning, not just keywords, across sessions
Retrieving the same memories from different MCP clients
Automatic linking between related memories in the knowledge graph

Already running an "Open Brain" setup? Ogham plugs into the same Supabase database and adds semantic search plus a knowledge graph.

GitHub: https://github.com/ogham-mcp/ogham-mcp
Docs: https://ogham-mcp.dev
Install: uvx ogham-mcp && ogham init

MIT licensed. Bring your own Supabase or PostgreSQL + pgvector.

