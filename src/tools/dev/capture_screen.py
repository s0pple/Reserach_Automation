import mss
import os
from PIL import Image

def capture():
    try:
        with mss.mss() as sct:
            sct.shot(output="current_view.png")
            print(f"DEBUG: Screenshot erfolgreich gespeichert unter {os.path.abspath('current_view.png')}")
    except Exception as e:
        print(f"ERROR: Screenshot fehlgeschlagen: {e}")

if __name__ == "__main__":
    capture()
