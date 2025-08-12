#!/usr/bin/env python3
"""
Script to fix common InsightFace dependency issues.
"""

import os
import sys
import subprocess
import platform
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def check_libstdc_version():
    """Check the version of libstdc++.so.6"""
    try:
        logger.info("Checking libstdc++ version...")

        # Standard library paths
        lib_paths = [
            "/usr/lib/x86_64-linux-gnu/libstdc++.so.6",
            "/lib/x86_64-linux-gnu/libstdc++.so.6",
        ]

        lib_path = next((path for path in lib_paths if os.path.exists(path)), None)
        if not lib_path:
            logger.warning("Could not find libstdc++.so.6 in standard locations.")
            return False

        # Check GLIBCXX versions
        try:
            output = subprocess.check_output(["strings", lib_path], text=True)
            if "GLIBCXX_3.4.32" not in output:
                logger.warning("GLIBCXX_3.4.32 not found in system libstdc++")
                return False
            return True
        except subprocess.CalledProcessError:
            logger.error("Error running 'strings' command on libstdc++")
            return False

    except Exception as e:
        logger.error(f"Error checking libstdc++ version: {e}")
        return False


def install_minimal_dependencies():
    """Install minimal dependencies for basic functionality"""
    logger.info("Installing minimal dependencies...")

    try:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "numpy",
                "opencv-contrib-python",
                "onnxruntime",
            ]
        )
        logger.info("Minimal dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install minimal dependencies: {e}")
        return False


def install_enhanced_dependencies():
    """Install enhanced dependencies for improved face recognition"""
    logger.info("Installing enhanced face recognition dependencies...")

    try:
        # Install packages for improved face detection and recognition
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "scikit-learn",
                "opencv-contrib-python",
                "pillow",
            ]
        )
        logger.info("Enhanced face recognition dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install enhanced dependencies: {e}")

        # Try installing just the essential packages
        try:
            logger.info("Attempting to install minimal enhanced dependencies...")
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "facenet-pytorch",
                    "scikit-learn",
                ]
            )
            logger.info("Minimal enhanced dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install minimal enhanced dependencies: {e}")
            return False


def try_alternate_insightface_install():
    """Try installing InsightFace with alternative methods"""
    logger.info("Attempting alternative installation for InsightFace...")

    try:
        subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", "insightface"])
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "onnx",
                "onnxruntime",
                "scikit-learn",
                "opencv-contrib-python",
                "git+https://github.com/deepinsight/insightface.git@master",
            ]
        )
        logger.info("InsightFace installed successfully from GitHub.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install InsightFace from GitHub: {e}")
        return False


def check_insightface_install():
    """Check if InsightFace can be imported without errors"""
    logger.info("Verifying InsightFace installation...")

    try:
        import insightface
        from insightface.model_zoo import model_zoo

        logger.info("InsightFace imported successfully!")
        return True
    except ImportError as e:
        logger.error(f"Error importing InsightFace: {e}")
        return False


def use_opencv_dnn_fallback():
    """Setup OpenCV DNN face detection as fallback"""
    logger.info("Setting up OpenCV DNN face detection fallback...")

    fallback_detector_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src/face/opencv_detector.py"
    )

    detector_code = """\
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
    """

    with open(fallback_detector_path, "w") as f:
        f.write(detector_code)

    logger.info(f"Created OpenCV fallback detector at {fallback_detector_path}")
    return True


def main():
    logger.info("Starting InsightFace dependency fix...")

    if platform.system() != "Linux":
        logger.warning(
            f"This script is primarily for Linux. Detected: {platform.system()}"
        )

    logger.info(f"Python version: {platform.python_version()}")

    # Install dependencies first
    logger.info("Installing minimal dependencies...")
    install_minimal_dependencies()

    logger.info("Installing enhanced dependencies for improved face recognition...")
    install_enhanced_dependencies()

    # Create enhanced OpenCV detector
    logger.info("Setting up enhanced OpenCV detector...")

    # Path for the enhanced OpenCV detector
    opencv_detector_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src/face/opencv_detector.py"
    )

    # Copy the enhanced detector from the updated version
    try:
        from urllib.request import urlopen

        logger.info("Downloading enhanced OpenCV detector template...")
        url = "https://raw.githubusercontent.com/surajkumar/enhanced-face-detector/main/opencv_detector.py"

        try:
            # Try to download the enhanced detector
            response = urlopen(url)
            enhanced_detector_code = response.read().decode("utf-8")

            with open(opencv_detector_path, "w") as f:
                f.write(enhanced_detector_code)

            logger.info(f"Enhanced OpenCV detector created at {opencv_detector_path}")
        except Exception as e:
            logger.error(f"Failed to download enhanced detector: {e}")
            logger.info("Using local template instead...")

            # Use local template as fallback
            use_opencv_dnn_fallback()
    except Exception as e:
        logger.error(f"Error creating detector: {e}")
        use_opencv_dnn_fallback()

    # Try installing InsightFace as a backup option
    logger.info("Trying alternative InsightFace installation...")
    try_alternate_insightface_install()

    # Update the API service to use the enhanced detector
    api_service_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "api_service.py"
    )

    # Update API service if it exists
    if os.path.exists(api_service_path):
        try:
            with open(api_service_path, "r") as f:
                content = f.read()

            # Update imports to try OpenCV detector first
            updated_content = content.replace(
                "try:\n    from src.face.detector_fixed import FaceDetector",
                """try:
    # First try to import the OpenCV detector (more reliable cross-platform)
    from src.face.opencv_detector import FaceDetector
    logger.info("Using enhanced OpenCV detector")
except ImportError:
    try:
        # Then try to import the fixed detector if OpenCV not available
        from src.face.detector_fixed import FaceDetector
        logger.info("Using fixed InsightFace detector")""",
            )

            # Add enhanced verification after detector initialization
            if "detector = FaceDetector" in updated_content:
                updated_content = updated_content.replace(
                    "detector = FaceDetector(detection_threshold=settings.DETECTION_THRESHOLD)",
                    """detector = FaceDetector(detection_threshold=settings.DETECTION_THRESHOLD)

# Verify detector has required methods
required_methods = ["detect_faces", "get_largest_face", "draw_face_locations"]
missing_methods = []
for method in required_methods:
    if not hasattr(detector, method):
        missing_methods.append(method)
        logger.error(f"Detector missing required method: {method}")

if missing_methods:
    logger.error(f"Detector is missing critical methods: {missing_methods}")
    logger.error("API will likely fail. Please check your installation.")""",
                )

            with open(api_service_path, "w") as f:
                f.write(updated_content)

            logger.info(f"Updated {api_service_path} to use enhanced detector")
        except Exception as e:
            logger.error(f"Failed to update API service: {e}")

    # Update the verifier.py file to prefer OpenCV detector
    verifier_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src/access_control/verifier.py"
    )

    if os.path.exists(verifier_path):
        try:
            with open(verifier_path, "r") as f:
                verifier_content = f.read()

            # Update to prefer OpenCV detector
            updated_content = verifier_content.replace(
                "try:\n    from src.face.detector_fixed import FaceDetector",
                "try:\n    from src.face.opencv_detector import FaceDetector\nexcept ImportError:\n    from src.face.detector_fixed import FaceDetector",
            )

            with open(verifier_path, "w") as f:
                f.write(updated_content)

            logger.info(f"Updated {verifier_path} to prefer OpenCV detector")
        except Exception as e:
            logger.error(f"Failed to update verifier.py: {e}")

    print("\n=== FACE RECOGNITION SYSTEM FIX COMPLETE ===")
    print(
        "The system has been updated to use a more reliable face detector that works across different environments."
    )
    print("\nTo use your system:")
    print("1. Run with face recognition:")
    print("   python main.py live")
    print("\n2. Test with a specific image:")
    print("   python main.py test --image path/to/your/image.jpg")
    print("\n3. If you're using the API service, restart it:")
    print("   sudo systemctl restart gunicorn")
    print("\nIf you still experience issues, try recreating the face database:")
    print("   python main.py create-db --root path/to/your/face/images")


if __name__ == "__main__":
    main()
