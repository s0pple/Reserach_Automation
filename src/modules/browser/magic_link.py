import asyncio
import logging
from aiohttp import web
import time
import subprocess
import re

logger = logging.getLogger("MagicLink")

async def start_ssh_tunnel(port):
    """Startet einen SSH Tunnel zu serveo.net und gibt die URL zurück."""
    proc = await asyncio.create_subprocess_exec(
        "ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:localhost:{port}", "serveo.net",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Lese die erste Zeile, um die URL zu extrahieren
    for _ in range(10):
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
            line = line.decode('utf-8').strip()
            if "Forwarding HTTP traffic from" in line:
                url = line.split("from ")[-1].strip()
                return url, proc
        except asyncio.TimeoutError:
            continue
    return None, proc

async def get_user_click_via_magic_link(image_path: str, bot_app, chat_id: str, action_verb: str = "klicken"):
    """
    Spins up a temporary web server, exposes it via serveo, and sends the link to the user.
    Waits until the user clicks on the image, then returns (x, y).
    """
    click_event = asyncio.Event()
    click_coords = None
    server_port = 8080

    routes = web.RouteTableDef()

    @routes.get('/')
    async def index(request):
        # We bust the cache by appending a timestamp to the image url
        ts = int(time.time())
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Magic {action_verb.capitalize()}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <style>
                body {{ margin: 0; padding: 0; background: #111; display: flex; flex-direction: column; align-items: center; }}
                #info {{ background: #007bff; color: white; padding: 15px; width: 100%; text-align: center; font-family: sans-serif; font-size: 16px; font-weight: bold; position: sticky; top: 0; z-index: 10; }}
                img {{ max-width: 100%; cursor: crosshair; display: block; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div id="info">Tippe auf die Stelle, wo der Bot {action_verb} soll.</div>
            <img src="/image?t={ts}" id="screen" />
            <script>
                document.getElementById('screen').addEventListener('click', function(e) {{
                    var info = document.getElementById('info');
                    info.innerHTML = "⏳ Sende Koordinaten...";
                    info.style.background = "#ffc107";
                    info.style.color = "black";
                    
                    var rect = e.target.getBoundingClientRect();
                    var scaleX = e.target.naturalWidth / rect.width;
                    var scaleY = e.target.naturalHeight / rect.height;
                    
                    var x = Math.round((e.clientX - rect.left) * scaleX);
                    var y = Math.round((e.clientY - rect.top) * scaleY);
                    
                    fetch('/click', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{x: x, y: y}})
                    }}).then(() => {{
                        info.innerHTML = "✅ Erfolgreich! Gehe zurück zu Telegram.";
                        info.style.background = "#28a745";
                        info.style.color = "white";
                    }}).catch(err => {{
                        info.innerHTML = "❌ Fehler aufgetreten.";
                        info.style.background = "#dc3545";
                    }});
                }});
            </script>
        </body>
        </html>
        '''
        return web.Response(text=html, content_type='text/html')

    @routes.get('/image')
    async def get_image(request):
        return web.FileResponse(image_path)

    @routes.post('/click')
    async def receive_click(request):
        nonlocal click_coords
        data = await request.json()
        click_coords = (data['x'], data['y'])
        click_event.set()
        return web.Response(text="OK")

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Run server
    site = web.TCPSite(runner, '0.0.0.0', server_port)
    await site.start()

    tunnel_proc = None
    try:
        # Start SSH Tunnel
        public_url, tunnel_proc = await start_ssh_tunnel(server_port)
        
        if not public_url:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Tunnel konnte nicht aufgebaut werden.")
            return None

        logger.info(f"Magic Link live at {public_url}")

        # Send to Telegram
        msg = await bot_app.bot.send_message(
            chat_id=chat_id, 
            text=f"✨ **Magic Link generiert!** ✨\n\nKlicke auf den Link und tippe direkt auf dem Bildschirm, wohin ich **{action_verb}** soll:\n\n👉 {public_url}\n\n*(Der Link schließt sich danach automatisch)*",
            parse_mode="Markdown"
        )

        # Wait for user to click on the web page
        await click_event.wait()
        
        await bot_app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text=f"✅ Magic Link erfolgreich genutzt! Koordinaten: `X:{click_coords[0]}, Y:{click_coords[1]}`",
            parse_mode="Markdown"
        )
        
    finally:
        # Cleanup everything instantly
        if tunnel_proc:
            tunnel_proc.terminate()
        await runner.cleanup()

    return click_coords
