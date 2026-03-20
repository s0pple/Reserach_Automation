import cv2

img = cv2.imread("verify_session_cassie.png")
h, w, _ = img.shape
# Crop bottom 150px
crop = img[h-150:h, 0:w]
cv2.imwrite("debug_bottom_strip.png", crop)
