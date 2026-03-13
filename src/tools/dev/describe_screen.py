import os
import asyncio
from PIL import Image
import io
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.core.secret import generate_content_with_key_rotation

async def main():
    load_dotenv()
    if not os.path.exists("debug_screen.png"):
        print("debug_screen.png not found")
        return

    pil_image = Image.open("debug_screen.png")
    prompt = "Describe this screenshot in detail. What website is open? Are there any popups, cookie banners, or error messages? Where is the main content?"
    
    print("Asking Gemini to describe the screen...")
    response = await asyncio.to_thread(
        generate_content_with_key_rotation,
        [prompt, pil_image]
    )
    print("\nDESCRIPTION:")
    print(response.text)

if __name__ == "__main__":
    asyncio.run(main())
