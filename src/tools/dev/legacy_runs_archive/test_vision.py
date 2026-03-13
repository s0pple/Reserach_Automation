import sys
import os
import asyncio
import cv2
import numpy as np
import mss
from dotenv import load_dotenv
from PIL import Image
import io

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.cv_bot.cv_bot_tool import CVBotTool

async def main():
    print("🚀 Starting CV-Bot Vision & Template Test...")
    load_dotenv()
    
    # Initialize the tool
    tool = CVBotTool()
    
    # The target we want to find. Change this to something visible on your screen!
    target = "Windows Start Button"
    
    print(f"\n📸 Taking full screenshot...")
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        sct_img = sct.grab(monitor)
        img_bgra = np.array(sct_img)
        img_rgb = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        img_byte_arr = io.BytesIO()
        pil_img.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
    print(f"\n🧠 Sending to Gemini 2.5 Flash: Where is the '{target}'?")
    # 1. The Vision Locator (Fallback/Learning Phase)
    vision_result = await tool.find_element_via_vision(image_bytes, target, img_bgra)
    
    if not vision_result.get("found"):
        print("❌ Gemini could not find the element. Try a different target description.")
        return
        
    print(f"✅ Vision Step Complete. Coordinates: X:{vision_result['x']}, Y:{vision_result['y']}")
    
    # 2. The Cache (Fast-Path / Memory)
    print(f"\n⚡ Testing OpenCV Fast-Path for '{target}'...")
    try:
        template_result = tool.find_element_via_template(target)
        print(f"✅ OpenCV Step Complete! Found locally at: X:{template_result['x']}, Y:{template_result['y']}")
    except Exception as e:
        print(f"❌ OpenCV Step Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())