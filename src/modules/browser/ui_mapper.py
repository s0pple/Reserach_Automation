import json
import logging
from PIL import Image
import io
import asyncio
from src.core.secret import generate_content_with_key_rotation

logger = logging.getLogger(__name__)

async def get_ui_map(image_bytes: bytes) -> list:
    """
    Uses Gemini Vision to perform high-fidelity OCR and UI element mapping.
    Returns a list of dictionaries: [{"text": "...", "x": ..., "y": ..., "type": "..."}]
    """
    prompt = """
    You are a high-precision computer vision engine for web interfaces.
    Analyze the provided screenshot of Google AI Studio.
    Goal: Create a 'Ground Truth' coordinate map of ALL interactive elements.
    
    Instructions:
    1. Identify every visible button, input field, tab, and menu item.
    2. For each element, find its EXACT center (X, Y) coordinates in pixels relative to the image size.
    3. Capture the literal text/label displayed on the element.
    4. Categorize the element type.
    
    Return ONLY a raw JSON list of objects:
    [
      {"text": "Submit", "x": 450, "y": 800, "type": "button"},
      {"text": "Prompt Input", "x": 640, "y": 600, "type": "textarea"},
      {"text": "Gemini 1.5 Pro", "x": 200, "y": 150, "type": "dropdown"}
    ]
    
    Precision is CRITICAL. If you are unsure, provide your best estimate but prioritize clarity.
    Do NOT include markdown block markers (e.g., ```json). Return raw text.
    """
    
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        width, height = pil_image.size
        logger.info(f"Analyzing UI screenshot ({width}x{height})...")
        
        # Call Gemini
        response = await asyncio.to_thread(
            generate_content_with_key_rotation,
            [prompt, pil_image],
            generation_config={"response_mime_type": "application/json"}
        )
        
        raw_text = response.text.strip()
        # Fallback: remove markdown block markers if Gemini ignored the instruction
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        
        ui_map = json.loads(raw_text)
        
        # Basic validation: ensure X/Y are within bounds
        for el in ui_map:
            el["x"] = max(0, min(width, el.get("x", 0)))
            el["y"] = max(0, min(height, el.get("y", 0)))
            
        logger.info(f"UI Map generated: {len(ui_map)} elements found.")
        return ui_map
        
    except Exception as e:
        logger.error(f"UI Mapper failed: {e}")
        return []

def find_in_map(ui_map: list, target_text: str):
    """
    Search for target_text in the UI map using fuzzy matching.
    """
    import difflib
    
    best_match = None
    highest_ratio = 0.0
    
    for element in ui_map:
        text = element.get("text", "").lower()
        ratio = difflib.SequenceMatcher(None, target_text.lower(), text).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = element
            
    if highest_ratio > 0.7: # 70% match threshold
        return best_match
    return None
