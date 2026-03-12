import mss
import cv2
import numpy as np
import os

def take_screenshot():
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        img = np.array(sct_img)
        cv2.imwrite("test_screen.png", img)
        print(f"Screenshot saved to test_screen.png, size: {img.shape}")

if __name__ == "__main__":
    take_screenshot()
