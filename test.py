"""
This script resolves directory issues on Linux.
Run this before using the face recognition system.
"""

import os
import sys
import logging
import argparse
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def ensure_directory(path):
    """Ensure directory exists and is writable."""
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created directory: {path}")
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    # Check if directory is writable
    if not os.access(path, os.W_OK):
        logger.warning(f"Directory {path} is not writable")
        return False

    return True


def fix_permissions(path):
    """Fix permissions on directory."""
    try:
        os.chmod(path, 0o755)  # rwxr-xr-x
        logger.info(f"Fixed permissions on {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to fix permissions on {path}: {e}")
        return False


def check_opencv_installation():
    """Check OpenCV installation."""
    try:
        import cv2

        logger.info(f"OpenCV installed: version {cv2.__version__}")

        # Check cascade file
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(cascade_path):
            logger.info(f"Cascade file found at: {cascade_path}")
        else:
            logger.warning(f"Cascade file not found at: {cascade_path}")

            # Check alternative locations
            alt_paths = [
                "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
                "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
                "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
            ]

            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    logger.info(
                        f"Found cascade file at alternative location: {alt_path}"
                    )
                    # Create symlink to the default location
                    os.makedirs(os.path.dirname(cascade_path), exist_ok=True)
                    try:
                        os.symlink(alt_path, cascade_path)
                        logger.info(
                            f"Created symlink from {alt_path} to {cascade_path}"
                        )
                        break
                    except Exception as e:
                        logger.error(f"Failed to create symlink: {e}")
            else:
                logger.error("Could not find cascade file in any location")

        return True
    except ImportError:
        logger.error("OpenCV not installed")
        return False
    except Exception as e:
        logger.error(f"Error checking OpenCV: {e}")
        return False


def check_insightface_installation():
    """Check InsightFace installation."""
    try:
        import insightface

        logger.info("InsightFace installed")

        # Check model directory
        home_dir = os.path.expanduser("~")
        model_dir = os.path.join(home_dir, ".insightface", "models", "buffalo_l")

        if os.path.exists(model_dir):
            logger.info(f"InsightFace model directory exists: {model_dir}")
            # Check if models exist
            model_files = [f for f in os.listdir(model_dir) if f.endswith(".onnx")]
            if model_files:
                logger.info(
                    f"Found {len(model_files)} model files: {', '.join(model_files)}"
                )
            else:
                logger.warning(f"No model files found in {model_dir}")
        else:
            logger.warning(f"InsightFace model directory does not exist: {model_dir}")
            # Create directory
            os.makedirs(model_dir, exist_ok=True)
            logger.info(f"Created model directory: {model_dir}")
            logger.info(f"Models will be downloaded automatically on first use")

        return True
    except ImportError:
        logger.error("InsightFace not installed")
        return False
    except Exception as e:
        logger.error(f"Error checking InsightFace: {e}")
        return False


def check_camera_access():
    """Check camera access."""
    try:
        import cv2

        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                logger.info("Camera access: OK")
                cap.release()
                return True
            else:
                logger.warning("Camera opened but frame read failed")
        else:
            logger.warning("Failed to open camera")

        cap.release()

        # Check video devices
        video_devices = [f for f in os.listdir("/dev") if f.startswith("video")]
        if video_devices:
            logger.info(f"Found video devices: {', '.join(video_devices)}")
        else:
            logger.warning("No video devices found in /dev")

        return False
    except Exception as e:
        logger.error(f"Error checking camera: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Fix common issues with face recognition system on Linux"
    )
    parser.add_argument(
        "--check-only", action="store_true", help="Only check for issues without fixing"
    )
    args = parser.parse_args()

    logger.info("Starting system check...")

    # Check and create required directories
    required_dirs = ["face_data", "data", "logs"]
    for directory in required_dirs:
        exists = ensure_directory(directory)
        if exists and not args.check_only:
            fix_permissions(directory)

    # Check OpenCV installation
    check_opencv_installation()

    # Check InsightFace installation
    check_insightface_installation()

    # Check camera access
    check_camera_access()

    logger.info("System check completed")

    # Print guidance
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("1. Create face database:")
    print("   python main.py create-db --root face_data")
    print("2. Test recognition:")
    print("   python main.py test --image /path/to/image.jpg")
    print("3. Run live recognition:")
    print("   python main.py live")
    print("=" * 80)


if __name__ == "__main__":
    main()
