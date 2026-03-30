import cv2
import numpy as np
import mediapipe as mp

try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print("Tasks API found!")
    
    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2)
    detector = vision.HandLandmarker.create_from_options(options)
    print("Detector created successfully!")
    
    # Create a dummy image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
    detection_result = detector.detect(mp_image)
    print("Detection tested:", type(detection_result))

except Exception as e:
    print("Error:", e)
#This is a sample for testing mediapipe
