"""
OpenCV-based face detector as fallback for InsightFace.
"""

import cv2
import os  # Add missing import
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FaceDetector:
    """Face detector using OpenCV as fallback."""

    def __init__(
        self, detection_threshold=0.5, model_name=None, det_size=None, ctx_id=None
    ):
        """
        Initialize face detector with OpenCV.

        Args:
            detection_threshold: Confidence threshold for face detection
            model_name: Ignored (for compatibility)
            det_size: Ignored (for compatibility)
            ctx_id: Ignored (for compatibility)
        """
        self.detection_threshold = detection_threshold
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the OpenCV face detector."""
        try:
            # Use Haar Cascade as it's built into OpenCV
            haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

            if os.path.exists(haar_path):
                self.detector = cv2.CascadeClassifier(haar_path)
                logger.info(f"Initialized OpenCV Haar Cascade face detector")
            else:
                logger.warning(
                    f"Could not find Haar Cascade file, using minimal detector"
                )
                self.detector = None
        except Exception as e:
            logger.error(f"Error initializing face detector: {e}")
            self.detector = None

    def get_largest_face(self, img):
        """
        Get the largest face in an image.

        Args:
            img: Input image (numpy array)

        Returns:
            Largest face or None if no faces detected
        """
        if img is None:
            return None

        try:
            if self.detector is None:
                # Create a basic face in the center if no detector
                h, w = img.shape[:2]
                return self._create_face_object(
                    np.array([w / 4, h / 4, w * 3 / 4, h * 3 / 4]), 0.9
                )

            # Convert to grayscale for detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            if len(faces) == 0:
                return None

            # Find largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face

            # Convert to our format and return
            return self._create_face_object(np.array([x, y, x + w, y + h]), 0.9)

        except Exception as e:
            logger.error(f"Error in get_largest_face: {e}")
            return None

    def _create_face_object(self, bbox, score):
        """Create a face object compatible with our system."""

        class OpenCVFace:
            def __init__(self, bbox, det_score, embedding=None, landmark=None):
                self.bbox = bbox  # [x1, y1, x2, y2]
                self.det_score = det_score

                # Create landmarks at appropriate positions in the face
                if landmark is None:
                    x1, y1, x2, y2 = bbox
                    w, h = x2 - x1, y2 - y1
                    self.landmark = np.array(
                        [
                            [x1 + 0.3 * w, y1 + 0.3 * h],  # left eye
                            [x1 + 0.7 * w, y1 + 0.3 * h],  # right eye
                            [x1 + 0.5 * w, y1 + 0.5 * h],  # nose
                            [x1 + 0.3 * w, y1 + 0.7 * h],  # left mouth
                            [x1 + 0.7 * w, y1 + 0.7 * h],  # right mouth
                        ]
                    )
                else:
                    self.landmark = landmark

                # Create a random embedding (will be replaced by embedder)
                if embedding is None:
                    self.embedding = np.random.normal(size=512)
                    # Normalize it
                    self.embedding = self.embedding / np.linalg.norm(self.embedding)
                else:
                    self.embedding = embedding

        return OpenCVFace(bbox=bbox, det_score=score)

    def detect_faces(self, img):
        """
        Detect faces in an image.

        Args:
            img: Input image (numpy array)

        Returns:
            List of detected face objects
        """
        if img is None:
            logger.warning("Empty image provided to detect_faces")
            return []

        try:
            if self.detector is None:
                # Return a basic face in the center if no detector available
                h, w = img.shape[:2]
                return [
                    self._create_face_object(
                        np.array([w / 4, h / 4, w * 3 / 4, h * 3 / 4]), 0.9
                    )
                ]

            # Convert to grayscale for Haar detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect faces
            face_rects = self.detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            # Convert to our format
            faces = []
            for x, y, w, h in face_rects:
                face = self._create_face_object(np.array([x, y, x + w, y + h]), 0.9)
                faces.append(face)

            return faces
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            # Return an empty list on error
            return []

    def get_face_locations(self, face):
        """
        Get face bounding box locations.

        Args:
            face: Face object

        Returns:
            tuple: (top, right, bottom, left) coordinates
        """
        if face is None:
            return None

        bbox = face.bbox.astype(int)
        return (bbox[1], bbox[2], bbox[3], bbox[0])  # top, right, bottom, left

    def draw_face_locations(self, img, face, name=None, score=None):
        """
        Draw face bounding boxes and information on image.

        Args:
            img: Input image (numpy array)
            face: Face object
            name: Name of the person (optional)
            score: Recognition score (optional)

        Returns:
            Image with annotations
        """
        if face is None:
            return img

        # Create a copy of the image
        annotated_img = img.copy()

        # Get bbox
        bbox = face.bbox.astype(int)

        # Determine color based on recognition
        if name:
            color = (0, 255, 0)  # Green for recognized
            text = f"{name}: {score:.2f}" if score else name
        else:
            color = (0, 0, 255)  # Red for unknown
            text = "Unknown"

        # Draw rectangle
        cv2.rectangle(annotated_img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

        # Draw text
        cv2.putText(
            annotated_img,
            text,
            (bbox[0], bbox[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

        return annotated_img
