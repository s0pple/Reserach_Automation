import os
from PIL import Image, ImageDraw, ImageFont

def draw_grid_on_image(input_path: str, output_path: str, grid_size: int = 10):
    """
    Zeichnet ein Raster über ein Bild, damit der User in Telegram Kacheln (z.B. C5) auswählen kann.
    """
    if not os.path.exists(input_path):
        return None
        
    try:
        with Image.open(input_path) as img:
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            # Berechne die Zellengröße
            cell_w = width / grid_size
            cell_h = height / grid_size
            
            # Vertikale Linien & Nummern (1-10)
            for i in range(grid_size + 1):
                x = i * cell_w
                draw.line([(x, 0), (x, height)], fill="red", width=2)
                if i < grid_size:
                    # Zeichne die Nummer oben
                    draw.text((x + (cell_w / 2) - 5, 5), str(i + 1), fill="red")
            
            # Horizontale Linien & Buchstaben (A-J)
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for j in range(grid_size + 1):
                y = j * cell_h
                draw.line([(0, y), (width, y)], fill="red", width=2)
                if j < grid_size:
                    # Zeichne den Buchstaben links
                    draw.text((5, y + (cell_h / 2) - 5), letters[j], fill="red")
                    
            img.save(output_path)
            return output_path
    except Exception as e:
        print(f"Fehler beim Zeichnen des Grids: {e}")
        return None

def get_coordinates_from_grid(tile: str, image_width: int, image_height: int, grid_size: int = 10):
    """
    Wandelt eine Kachel (z.B. 'C5') in X/Y Pixel um (Zentrum der Kachel).
    """
    tile = tile.strip().upper()
    if len(tile) < 2:
        return None
        
    letter = tile[0]
    number_str = tile[1:]
    
    if not letter.isalpha() or not number_str.isdigit():
        return None
        
    row_idx = ord(letter) - 65 # A=0, B=1, C=2...
    col_idx = int(number_str) - 1 # 1=0, 2=1, 3=2...
    
    if row_idx < 0 or row_idx >= grid_size or col_idx < 0 or col_idx >= grid_size:
        return None
        
    cell_w = image_width / grid_size
    cell_h = image_height / grid_size
    
    # Berechne das Zentrum der Kachel
    center_x = (col_idx * cell_w) + (cell_w / 2)
    center_y = (row_idx * cell_h) + (cell_h / 2)
    
    return int(center_x), int(center_y)
