import cv2

img = cv2.imread("verify_session_cassie.png")
h, w, _ = img.shape
print(f"Dimensions: {w}x{h}")

# Crop bottom right area where Run button usually is
# Adjust these based on the screenshot visual
# The screenshot shows it at the bottom right of the "Start building" card area? 
# No, it's in the prompt bar at the very bottom.
# Let's crop the bottom 100px and rightmost 200px
crop = img[h-100:h-20, w-200:w-20] 

cv2.imwrite("debug_run_crop.png", crop)
