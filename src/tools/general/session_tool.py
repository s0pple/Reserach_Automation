import asyncio
import logging
import uuid
import re
import libtmux
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class TmuxSessionManager:
    def __init__(self):
        self.server = libtmux.Server()
        self.watchers: Dict[str, asyncio.Task] = {}

    def get_session(self, session_id: str):
        try:
            return self.server.sessions.get(session_name=session_id)
        except Exception:
            return None

    def _clean_output(self, lines):
        """Cleans ansi codes and formats the output."""
        text = "\n".join(lines)
        ansi_escape = re.compile(r"(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    async def _watch_session(self, session_id: str, telegram_callback: Callable):
        """
        Periodically captures the pane to check if the bottom lines changed
        or if it looks like it is waiting for input.
        Reports termination with a summary.
        """
        logger.info(f"Starting watcher for tmux session {session_id}")
        last_content = ""
        last_captured_lines = []
        try:
            while True:
                session = self.get_session(session_id)
                if not session:
                    # Session finished - try to find if it left a trace or just say it's done
                    summary = "\n".join(last_captured_lines[-10:]) if last_captured_lines else "Keine Daten erfasst."
                    await telegram_callback(f"🏁 **Session `{session_id}` beendet.**\n\n**Zusammenfassung (letzte Zeilen):**\n```text\n{summary}\n```")
                    break
                
                try:
                    pane = session.active_window.active_pane
                    lines = pane.cmd("capture-pane", "-p", "-S", "-20").stdout
                    last_captured_lines = lines # Keep track for summary
                    current_content = self._clean_output(lines).strip()
                    
                    if current_content != last_content:
                        # Report if it looks like it's waiting for input
                        # Check last non-empty line
                        if current_content.endswith(("?", ">", "$", "]", ":")) or " [y/N]" in current_content:
                             await telegram_callback(f"🖥️ **Session `{session_id}` (Wartet auf Input):**\n```text\n{current_content[-1500:]}\n```")
                             last_content = current_content
                        else:
                            # Just update last_content to avoid spam, but keep last_captured_lines fresh
                            last_content = current_content
                except Exception as pane_err:
                    logger.warning(f"Error capturing pane for {session_id}: {pane_err}")

                await asyncio.sleep(3.0) # Check every 3 seconds
        except asyncio.CancelledError:
            logger.info(f"Watcher for {session_id} cancelled.")
        except Exception as e:
            logger.error(f"Error watching session {session_id}: {e}")
        finally:
            if session_id in self.watchers:
                del self.watchers[session_id]

    async def execute(self, params: Dict[str, Any], telegram_callback: Callable = None) -> Dict[str, Any]:
        action = params.get("action")
        session_id = params.get("session_id")

        if action == "start":
            command = params.get("command")
            if not command:
                return {"success": False, "error": "Command is required to start a session."}
                
            if not session_id:
                session_id = f"cli_{uuid.uuid4().hex[:6]}"
                
            logger.info(f"Starting tmux session {session_id} with command: {command}")
            
            try:
                session = self.server.new_session(session_name=session_id, window_command=command, detach=True)
                
                if telegram_callback:
                    if session_id in self.watchers:
                        self.watchers[session_id].cancel()
                    self.watchers[session_id] = asyncio.create_task(self._watch_session(session_id, telegram_callback))
                
                return {
                    "success": True, 
                    "session_id": session_id, 
                    "message": f"🚀 Tmux-Session `{session_id}` im Hintergrund gestartet."
                }
            except Exception as e:
                return {"success": False, "error": f"Failed to start tmux session: {e}"}

        elif action == "input":
            if not session_id:
                return {"success": False, "error": "session_id is required."}
                
            session = self.get_session(session_id)
            if not session:
                return {"success": False, "error": f"Session {session_id} not found."}
                
            input_text = params.get("input_text")
            if not input_text:
                return {"success": False, "error": "input_text is required."}
                
            try:
                pane = session.active_window.active_pane
                pane.send_keys(input_text)
                return {"success": True, "message": f"⌨️ Eingabe an `{session_id}` gesendet."}
            except Exception as e:
                return {"success": False, "error": f"Failed to send input: {e}"}

        elif action == "read":
             if not session_id:
                return {"success": False, "error": "session_id is required."}
             
             session = self.get_session(session_id)
             if not session:
                 return {"success": False, "error": f"Session {session_id} not found."}
             
             try:
                 pane = session.active_window.active_pane
                 lines = pane.cmd("capture-pane", "-p", "-S", "-50").stdout
                 content = self._clean_output(lines).strip()
                 return {"success": True, "content": f"📋 **Aktueller Screen von `{session_id}`:**\n```text\n{content[-2500:]}\n```"}
             except Exception as e:
                 return {"success": False, "error": f"Failed to read session: {e}"}

        elif action == "list":
            # List all active sessions
            try:
                sessions = self.server.sessions
                if not sessions:
                    return {"success": True, "content": "📭 Keine aktiven Tmux-Sessions."}
                
                session_list = []
                for s in sessions:
                    session_list.append(f"🔹 `{s.session_name}` (Windows: {len(s.windows)})")
                
                return {"success": True, "content": "📋 **Aktive Sessions:**\n" + "\n".join(session_list)}
            except Exception as e:
                return {"success": False, "error": f"Failed to list sessions: {e}"}

        elif action == "kill":
            if not session_id:
                return {"success": False, "error": "session_id is required."}
                
            session = self.get_session(session_id)
            if not session:
                return {"success": False, "error": f"Session {session_id} not found."}
                
            try:
                session.kill_session()
                if session_id in self.watchers:
                    self.watchers[session_id].cancel()
                    del self.watchers[session_id]
                return {"success": True, "message": f"🛑 Session `{session_id}` wurde beendet."}
            except Exception as e:
                return {"success": False, "error": f"Failed to kill session: {e}"}
            
        return {"success": False, "error": f"Unknown action: {action}"}

tmux_manager = TmuxSessionManager()

async def interactive_session_tool(action: str, session_id: str = None, command: str = None, input_text: str = None, telegram_callback: Callable = None) -> Dict[str, Any]:
    """Tool function to interface with the TmuxSessionManager."""
    params = {
        "action": action,
        "session_id": session_id,
        "command": command,
        "input_text": input_text
    }
    return await tmux_manager.execute(params, telegram_callback)
