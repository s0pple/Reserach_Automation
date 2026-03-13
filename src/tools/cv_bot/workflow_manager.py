import os
import json
import asyncio
import pyautogui
import mss
import cv2
import numpy as np
import pyperclip
from PIL import Image
import io
from typing import List, Dict, Any, Union

from src.tools.cv_bot.cv_bot_tool import CVBotTool

WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "workflows")
os.makedirs(WORKFLOW_DIR, exist_ok=True)

class WorkflowManager:
    def __init__(self):
        self.cv_tool = CVBotTool()
        # Kurze Sicherheitspause für PyAutoGUI
        pyautogui.PAUSE = 0.5

    def _get_screenshot_bytes(self) -> tuple[bytes, np.ndarray, int, int]:
        with mss.mss() as sct:
            monitor = sct.monitors[0] # All monitors (Panorama)
            sct_img = sct.grab(monitor)
            img_bgra = np.array(sct_img)
            img_rgb = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue(), img_bgra, monitor["left"], monitor["top"]

    async def execute_workflow(self, workflow_name: str) -> Dict[str, Any]:
        filepath = os.path.join(WORKFLOW_DIR, f"{workflow_name}.json")
        if not os.path.exists(filepath):
            print(f"❌ Workflow file {filepath} not found.")
            return {"success": False, "error": "File not found"}

        with open(filepath, "r", encoding="utf-8") as f:
            steps = json.load(f)

        print(f"🚀 Starting workflow: '{workflow_name}' with {len(steps)} steps")
        
        extracted_text = None

        for step in steps:
            step_num = step.get("step", "?")
            action = step.get("action")
            target = step.get("target")
            text = step.get("text")
            keys = step.get("keys")
            duration = step.get("duration")
            command = step.get("command")

            x_coord = step.get("x")
            y_coord = step.get("y")

            print(f"\n▶️ [Step {step_num}] Action: {action}" + 
                  (f" | Target: '{target}'" if target else "") + 
                  (f" | Text: '{text}'" if text else "") +
                  (f" | Keys: {keys}" if keys else "") +
                  (f" | Duration: {duration}s" if duration else "") +
                  (f" | Command: '{command}'" if command else "") +
                  (f" | X:{x_coord} Y:{y_coord}" if x_coord is not None else ""))

            x, y = x_coord, y_coord

            if target:
                try:
                    # 1. ZUERST: Der OpenCV Fast-Path
                    result = self.cv_tool.find_element_via_template(target)
                    x, y = result["x"], result["y"]
                except Exception as e:
                    # 2. SELF-HEALING: OpenCV ist fehlgeschlagen. Wir rufen das Vision-LLM.
                    print(f"⚠️ Fast-Path failed for '{target}': {e}")
                    print(f"🔄 Triggering Vision Self-Healing for '{target}'...")
                    
                    image_bytes, img_bgra, offset_x, offset_y = self._get_screenshot_bytes()
                    
                    # Debug: Save screenshot to file
                    with open("debug_screen.png", "wb") as f:
                        f.write(image_bytes)
                    print("📸 Debug screenshot saved to 'debug_screen.png'")
                    
                    result = await self.cv_tool.find_element_via_vision(
                        image_bytes, target, original_bgra=img_bgra, 
                        offset_x=offset_x, offset_y=offset_y
                    )
                    
                    if not result.get("found"):
                        print(f"❌ Vision Self-Healing failed for '{target}'. Stopping workflow.")
                        return {"success": False, "error": "Self-Healing failed"}
                        
                    x, y = result["x"], result["y"]
                    print(f"✅ Self-Healing successful. New coordinates: X:{x}, Y:{y}")

            # 3. ACTION AUSFÜHREN (mit asyncio.to_thread)
            if action == "click":
                if x is not None and y is not None:
                    print(f"🖱️ Clicking at X:{x}, Y:{y} using xdotool")
                    # Move and click using xdotool for better Docker/Xvfb compatibility
                    os.system(f"xdotool mousemove {x} {y} click 1")
                else:
                    print("❌ Action 'click' requires a target with valid coordinates. Stopping.")
                    return {"success": False, "error": "Invalid coordinates for click"}
                    
            elif action == "type":
                if text:
                    t_lower = text.lower()
                    if t_lower in ["enter", "tab", "esc", "escape", "pagedown", "pageup"]:
                        key_map = {
                            "enter": "enter", "tab": "tab", "esc": "esc", "escape": "esc",
                            "pagedown": "pagedown", "pageup": "pageup"
                        }
                        key = key_map[t_lower]
                        print(f"⌨️ Pressing {key.upper()} key via xdotool")
                        if key == "enter":
                            key = "Return"
                        elif key == "esc":
                            key = "Escape"
                        elif key == "tab":
                            key = "Tab"
                        elif key == "pagedown":
                            key = "Page_Down"
                        elif key == "pageup":
                            key = "Page_Up"
                        await asyncio.to_thread(os.system, f"xdotool key {key}")
                    else:
                        print(f"⌨️ Typing: '{text}' via xdotool")
                        import subprocess
                        # Escape quotes for bash
                        safe_text = text.replace('"', '\\"')
                        # Force window focus first
                        os.system("xdotool windowactivate $(xdotool search --onlyvisible --class chromium | head -1) 2>/dev/null")
                        await asyncio.sleep(0.5)
                        await asyncio.to_thread(os.system, f'xdotool type --delay 50 "{safe_text}"')
                else:
                    print("❌ Action 'type' requires 'text'. Stopping.")
                    return {"success": False, "error": "Type requires text"}
            
            elif action == "hotkey":
                if keys and isinstance(keys, list):
                    print(f"⌨️ Pressing Hotkey: {' + '.join(keys)}")
                    await asyncio.to_thread(pyautogui.hotkey, *keys)
                else:
                    print("❌ Action 'hotkey' requires a list of 'keys'. Stopping.")
                    return {"success": False, "error": "Hotkey requires keys list"}
                    
            elif action == "wait":
                if duration is not None:
                    print(f"⏳ Waiting for {duration} seconds...")
                    await asyncio.sleep(duration)
                else:
                    print("❌ Action 'wait' requires a 'duration' (in seconds). Stopping.")
                    return {"success": False, "error": "Wait requires duration"}
                    
            elif action == "shell_command":
                if command:
                    print(f"💻 Executing Shell Command: {command}")
                    # Launch detached so it doesn't block the workflow
                    import subprocess
                    subprocess.Popen(command, shell=True)
                else:
                    print("❌ Action 'shell_command' requires a 'command'. Stopping.")
                    return {"success": False, "error": "Shell command requires command"}
                    
            elif action == "screenshot":
                filename = text if text else f"workflow_step_{step_num}.png"
                filepath = os.path.join("test", filename)
                print(f"📸 Taking screenshot: {filepath}")
                image_bytes, _, _, _ = self._get_screenshot_bytes()
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                    
            elif action == "extract_clipboard":
                print("📋 Extracting text from clipboard...")
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'a')
                await asyncio.sleep(0.5)
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'c')
                await asyncio.sleep(0.5)
                
                # Retrieve from clipboard - use xclip directly on Linux for reliability
                import subprocess
                try:
                    process = subprocess.Popen(['xclip', '-selection', 'clipboard', '-o'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    extracted_text = stdout.decode('utf-8', errors='ignore')
                    print(f"✂️ Copied {len(extracted_text)} characters from clipboard using xclip.")
                except Exception as e:
                    print(f"⚠️ xclip failed, trying pyperclip: {e}")
                    extracted_text = pyperclip.paste()
                    print(f"✂️ Copied {len(extracted_text)} characters from clipboard using pyperclip.")
                    
            else:
                print(f"❌ Unknown action: '{action}'. Stopping.")
                return {"success": False, "error": f"Unknown action: {action}"}
            
            # Kurze Pause nach jeder Aktion (außer wait), um der UI Zeit zu geben
            if action != "wait":
                await asyncio.sleep(0.5) 

        print(f"\n🎉 Workflow '{workflow_name}' completed successfully!")
        return {"success": True, "extracted_text": extracted_text}