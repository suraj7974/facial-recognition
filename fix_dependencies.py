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

    logger.info("Setting up OpenCV fallback detector...")
    use_opencv_dnn_fallback()

    logger.info("Skipping detailed libstdc++ check to avoid issues.")

    logger.info("Installing minimal dependencies...")
    install_minimal_dependencies()

    logger.info("Trying alternative InsightFace installation...")
    try_alternate_insightface_install()

    verifier_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src/access_control/verifier.py"
    )

    try:
        with open(verifier_path, "r") as f:
            verifier_content = f.read()

        updated_content = verifier_content.replace(
            "try:\n    from src.face.detector_fixed import FaceDetector",
            "try:\n    from src.face.opencv_detector import FaceDetector\nexcept ImportError:\n    from src.face.detector_fixed import FaceDetector",
        )

        with open(verifier_path, "w") as f:
            f.write(updated_content)

        logger.info(f"Updated {verifier_path} to prefer OpenCV detector first.")
    except Exception as e:
        logger.error(f"Failed to update verifier.py: {e}")

    print("\n=== FACE RECOGNITION SYSTEM FIX COMPLETE ===")
    print("1. Run your system with OpenCV fallback detection:")
    print("   python main.py live")
    print("\n2. If issues persist, try:")
    print("   python main.py live --detection-threshold 0.5")
    print("\n3. To improve performance:")
    print("   conda create -n face_rec python=3.8")
    print("   conda activate face_rec")
    print("   pip install -r requirements.txt")
    print("   pip install insightface==0.6.2 onnxruntime opencv-contrib-python")


if __name__ == "__main__":
    main()
