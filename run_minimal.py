"""
Minimal script to run the face recognition system without dependencies.
This bypasses the problematic InsightFace dependencies.
"""

import os
import sys
import logging
import cv2
import numpy as np
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def setup_minimal_detector():
    """Setup minimal face detector using OpenCV."""

    class MinimalFaceDetector:
        def __init__(self):
            # Try to use Haar Cascade from OpenCV
            haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(haar_path):
                self.detector = cv2.CascadeClassifier(haar_path)
                logger.info(f"Using OpenCV Haar Cascade")
            else:
                self.detector = None
                logger.warning("No face detector available, will simulate detections")

        def detect_faces(self, img):
            if self.detector is None:
                # Return a simulated face in the center of the image
                h, w = img.shape[:2]
                return [(int(w / 4), int(h / 4), int(w / 2), int(h / 2))]

            # Use Haar Cascade for detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            return faces

        def draw_face(self, img, face, text="Unknown"):
            # Draw rectangle around the face
            x, y, w, h = face
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

            # Draw text
            cv2.putText(
                img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2
            )

            return img

    return MinimalFaceDetector()


def run_minimal_live():
    """Run minimal live recognition."""
    # Setup detector
    detector = setup_minimal_detector()

    # Open webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        logger.error("Could not open webcam")
        return

    logger.info("Starting minimal face recognition (press 'q' to quit)")

    try:
        while True:
            # Read frame
            ret, frame = cap.read()

            if not ret:
                logger.warning("Could not read frame")
                break

            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)

            # Detect faces
            faces = detector.detect_faces(frame)

            # Draw each face
            for face in faces:
                frame = detector.draw_face(frame, face)

            # Show frame
            cv2.imshow("Minimal Face Recognition", frame)

            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except Exception as e:
        logger.exception(f"Error in minimal recognition: {e}")
    finally:
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Minimal recognition stopped")


if __name__ == "__main__":
    print("Starting minimal face recognition system...")
    print("This script avoids problematic dependencies.")
    print("Press 'q' to quit.")

    try:
        run_minimal_live()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
