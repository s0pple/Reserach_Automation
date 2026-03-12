import os
import json
import asyncio
import cv2
import numpy as np
import mss
from PIL import Image
import io
import google.generativeai as genai
from typing import Optional, Tuple, Dict, Any
from pydantic import Field
from ...core.tool_base import BaseTool, ToolArguments
from ...core.secret import generate_content_with_key_rotation

# Setup templates directory
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(TEMPLATE_DIR, exist_ok=True)

class CVBotArguments(ToolArguments):
    """Arguments for the CV Bot tool."""
    action: str = Field(..., description="Action to perform: 'find_vision', 'find_template'")
    target: str = Field(..., description="Target element description or name")

class CVBotTool(BaseTool):
    """
    CV Workflow Recorder: Uses Gemini 2.5 Flash for Vision-based UI detection,
    and OpenCV for hyper-fast local template matching (The Cache).
    """
    name: str = "cv_bot"
    description: str = "Interact with the screen using AI Vision (fallback) and OpenCV templates (fast-path)."
    args_schema: type[ToolArguments] = CVBotArguments

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Using the centralized key rotation from src.core.secret
        pass

    async def execute(self, args: CVBotArguments) -> Any:
        if args.action == "find_template":
            return self.find_element_via_template(args.target)
            
        elif args.action == "find_vision":
            with mss.mss() as sct:
                monitor = sct.monitors[0] # All monitors (Panorama)
                sct_img = sct.grab(monitor)
                img_bgra = np.array(sct_img)
                img_rgb = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2RGB)
                pil_img = Image.fromarray(img_rgb)
                
                img_byte_arr = io.BytesIO()
                pil_img.save(img_byte_arr, format='PNG')
                image_bytes = img_byte_arr.getvalue()
                
            return await self.find_element_via_vision(image_bytes, args.target, img_bgra)
            
        return {"error": "Unknown action"}

    async def find_element_via_vision(self, image_bytes: bytes, target_description: str, original_bgra: np.ndarray = None, offset_x: int = 0, offset_y: int = 0) -> Dict[str, Any]:
        print(f"[CV-Bot] 👁️ Asking Gemini to find '{target_description}'...")
        
        prompt = f"""
        Analyze this UI screenshot. Find the exact center coordinates (X and Y in pixels) of the '{target_description}'.
        Return ONLY a JSON block with exactly this format, no markdown formatting or backticks:
        {{"x": 123, "y": 456, "found": true}}
        If you absolutely cannot find it anywhere on the screen, return {{"x": 0, "y": 0, "found": false}}.
        """
        
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            # Run sync call in thread to not block async loop
            response = await asyncio.to_thread(
                generate_content_with_key_rotation,
                [prompt, pil_image]
            )
            
            text = response.text.strip()
            # Clean up potential markdown formatting if Gemini disobeys "no markdown" rule
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
                
            result = json.loads(text)
            
            if result.get("found"):
                x, y = result["x"], result["y"]
                print(f"[CV-Bot] ✅ Gemini found '{target_description}' at image coords X:{x}, Y:{y}")
                
                # Save the OpenCV Template Memory using relative coords
                if original_bgra is not None:
                    self._save_template(original_bgra, target_description, x, y)
                    
                # Convert to absolute screen coordinates for PyAutoGUI
                result["x"] = x + offset_x
                result["y"] = y + offset_y
                print(f"[CV-Bot] 🗺️ Absolute Screen Coordinates: X:{result['x']}, Y:{result['y']}")
                    
            return result

        except Exception as e:
            print(f"[CV-Bot] ❌ Error in Vision Locator: {e}")
            return {"x": 0, "y": 0, "found": False, "error": str(e)}

    def _save_template(self, image_bgra: np.ndarray, target_description: str, x: int, y: int):
        """Crops a 50x50 area around the coordinates and saves it."""
        half_size = 25
        height, width = image_bgra.shape[:2]
        
        y1 = max(0, y - half_size)
        y2 = min(height, y + half_size)
        x1 = max(0, x - half_size)
        x2 = min(width, x + half_size)
        
        template_crop = image_bgra[y1:y2, x1:x2]
        
        filename = f"{target_description.replace(' ', '_').lower()}.png"
        filepath = os.path.join(TEMPLATE_DIR, filename)
        
        # Convert BGRA to BGR for standard OpenCV saving
        template_bgr = cv2.cvtColor(template_crop, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(filepath, template_bgr)
        print(f"[CV-Bot] 📸 Saved 50x50 template memory to {filepath}")

    def find_element_via_template(self, target_description: str) -> Dict[str, Any]:
        """Fast-Path: Local OpenCV template matching."""
        filename = f"{target_description.replace(' ', '_').lower()}.png"
        filepath = os.path.join(TEMPLATE_DIR, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Template for '{target_description}' not found. Needs Vision Fallback.")
            
        print(f"[CV-Bot] ⚡ Fast-Path: Searching for '{target_description}' using local template...")
        
        template = cv2.imread(filepath)
        h, w = template.shape[:2]
        
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img_bgr = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            
        res = cv2.matchTemplate(img_bgr, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8  # 80% confidence required
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= threshold:
            # max_loc gives the top-left corner of the match
            center_x = max_loc[0] + w // 2 + monitor["left"]
            center_y = max_loc[1] + h // 2 + monitor["top"]
            print(f"[CV-Bot] 🎯 Found locally at absolute X:{center_x}, Y:{center_y} (Confidence: {max_val:.2f})")
            return {"x": center_x, "y": center_y, "found": True, "confidence": float(max_val)}
        else:
            raise ValueError(f"Template not found on screen with sufficient confidence (Max: {max_val:.2f}). Needs Vision Fallback.")
