'''
OpenCV DNN-based face detector fallback.
'''
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FaceDetector:
    def __init__(self, detection_threshold=0.5):
        self.detection_threshold = detection_threshold
        self._initialize_model()

    def _initialize_model(self):
        try:
            model_file = "models/res10_300x300_ssd_iter_140000.caffemodel"
            config_file = "models/deploy.prototxt.txt"
            if not all(map(os.path.exists, [model_file, config_file])):
                logger.warning("Model files not found. Fallback to basic detection.")
                self.net = None
                return
            self.net = cv2.dnn.readNetFromCaffe(config_file, model_file)
        except Exception as e:
            logger.error(f"Error initializing OpenCV face detector: {e}")
            self.net = None

    def detect_faces(self, img):
        if img is None or self.net is None:
            return []
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.net.setInput(blob)
        detections = self.net.forward()

        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > self.detection_threshold:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype("int")
                faces.append([x1, y1, x2, y2])
        return faces
    