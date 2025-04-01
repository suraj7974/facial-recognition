"""
Main entry point for the face recognition access control system.
This script provides a simple command-line interface to the system.
"""

import os
import sys
import logging
import argparse
import time
from datetime import datetime

from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(
                settings.LOG_DIR, f'main_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# Import from OpenCV detector directly to avoid InsightFace issues
try:
    from src.face.opencv_detector import FaceDetector

    logger.info("Using OpenCV detector")
except ImportError as e:
    logger.error(f"Error importing OpenCV detector: {e}")
    try:
        from src.face.detector_fixed import FaceDetector

        logger.info("Using fixed detector")
    except ImportError:
        logger.error(
            "Could not import any detector! Please run fix_dependencies.py first."
        )
        sys.exit(1)

# Modified imports to avoid direct dependency on problematic modules
from src.access_control.verifier import AccessVerifier
from src.face.embedder import FaceEmbedder
from src.database.embeddings_db import EmbeddingsDatabase
from src.database.faiss_db import FaissDatabase


# Import tool functions with workaround for detector
def create_database_from_folders(
    root_folder, db_path=None, use_faiss=False, min_faces_per_person=1
):
    """
    Create face embeddings database from folders of images.

    Args:
        root_folder: Root folder containing subfolders named after people
        db_path: Path to store the database (if None, use default)
        use_faiss: Whether to use FAISS for database
        min_faces_per_person: Minimum number of faces required per person

    Returns:
        Database instance
    """
    # Initialize components
    detector = FaceDetector(detection_threshold=settings.DETECTION_THRESHOLD)
    embedder = FaceEmbedder()

    # Initialize database
    if use_faiss:
        if db_path:
            db = FaissDatabase(db_path=db_path)
        else:
            db = FaissDatabase()
    else:
        if db_path:
            db = EmbeddingsDatabase(db_path=db_path)
        else:
            db = EmbeddingsDatabase()

    logger.info(f"Creating database from {root_folder}")
    logger.info(f"Using {'FAISS' if use_faiss else 'standard'} database")

    # Check if root folder exists
    if not os.path.isdir(root_folder):
        logger.error(f"Root folder does not exist: {root_folder}")
        return None

    # Get list of person folders
    person_folders = [
        f
        for f in os.listdir(root_folder)
        if os.path.isdir(os.path.join(root_folder, f))
    ]

    if not person_folders:
        logger.error(f"No person folders found in {root_folder}")
        return None

    logger.info(f"Found {len(person_folders)} person folders")

    # Import necessary modules here to avoid dependency issues
    from src.utils.image import is_image_file, read_image
    from tqdm import tqdm

    # Process each person folder
    for person_name in tqdm(person_folders, desc="Processing people"):
        person_folder = os.path.join(root_folder, person_name)

        logger.info(f"Processing {person_name}'s images...")

        # Get list of image files
        image_files = [
            f
            for f in os.listdir(person_folder)
            if is_image_file(os.path.join(person_folder, f))
        ]

        if not image_files:
            logger.warning(f"No images found for {person_name}")
            continue

        embeddings = []
        valid_images = 0

        # Process each image
        for img_name in tqdm(
            image_files, desc=f"Processing {person_name}'s images", leave=False
        ):
            img_path = os.path.join(person_folder, img_name)

            # Read image
            img = read_image(img_path)
            if img is None:
                continue

            # Detect face
            face = detector.get_largest_face(img)
            if face is None:
                logger.warning(f"No face detected in {img_path}")
                continue

            # Get embedding
            embedding = embedder.get_embedding(face)
            if embedding is None:
                logger.warning(f"Failed to get embedding for {img_path}")
                continue

            # Add embedding
            embeddings.append(embedding)
            valid_images += 1

        # Check if enough valid images
        if valid_images < min_faces_per_person:
            logger.warning(
                f"Too few valid images for {person_name}: {valid_images} < {min_faces_per_person}"
            )
            continue

        # Calculate average embedding
        avg_embedding = embedder.average_embeddings(embeddings)

        if avg_embedding is None:
            logger.warning(f"Failed to calculate average embedding for {person_name}")
            continue

        # Add to database
        db.add_identity(person_name, avg_embedding, valid_images)
        logger.info(f"Added {person_name} to database with {valid_images} images")

    # Save database
    db.save_database()

    # Log database info
    db_info = db.get_database_info()
    logger.info(f"Database created with {db_info['num_identities']} identities")
    logger.info(f"Identities: {', '.join(db_info['identities'])}")

    return db


def test_recognition(
    image_path,
    use_faiss=False,
    detection_threshold=None,
    recognition_threshold=None,
    display=True,
    save_path=None,
):
    """
    Test face recognition on a single image.

    Args:
        image_path: Path to test image
        use_faiss: Whether to use FAISS for database
        detection_threshold: Detection confidence threshold
        recognition_threshold: Recognition similarity threshold
        display: Whether to display the result
        save_path: Path to save the result image

    Returns:
        Recognition result (name, score)
    """
    # Set thresholds
    if detection_threshold is None:
        detection_threshold = settings.DETECTION_THRESHOLD

    if recognition_threshold is None:
        recognition_threshold = settings.RECOGNITION_THRESHOLD

    # Initialize verifier
    verifier = AccessVerifier(
        detection_threshold=detection_threshold,
        recognition_threshold=recognition_threshold,
        use_faiss=use_faiss,
    )

    # Import here to avoid dependency issues
    from src.utils.image import read_image

    # Read image
    img = read_image(image_path)
    if img is None:
        logger.error(f"Failed to read image: {image_path}")
        return None, 0

    # Start time
    start_time = time.time()

    # Verify face
    name, score, face, all_scores = verifier.verify_face(img, return_details=True)

    # Calculate processing time
    processing_time = time.time() - start_time

    # Log result
    if name:
        logger.info(
            f"Recognized as {name} with score {score:.4f} in {processing_time:.3f}s"
        )
    else:
        logger.info(f"Unknown face with score {score:.4f} in {processing_time:.3f}s")

    # Display top matches
    if all_scores:
        logger.info("Top matches:")
        for person, similarity in sorted(
            all_scores.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            logger.info(f"  {person}: {similarity:.4f}")

    # Create annotated image
    if display or save_path:
        result_img = verifier.verify_and_display(img)

        # Display result
        if display:
            try:
                import cv2

                cv2.imshow("Recognition Result", result_img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            except Exception as e:
                logger.warning(f"Could not display image: {e}")
                logger.info("GUI support not available in this OpenCV build.")
                # Save the image instead as fallback
                if save_path is None:
                    fallback_path = os.path.join(
                        settings.DATA_DIR,
                        "results",
                        f"result_{time.strftime('%Y%m%d_%H%M%S')}.jpg",
                    )
                    os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                    cv2.imwrite(fallback_path, result_img)
                    logger.info(f"Saved result to {fallback_path} instead")

        # Save result
        if save_path:
            import cv2

            cv2.imwrite(save_path, result_img)
            logger.info(f"Saved result to {save_path}")

    return name, score


def run_live_recognition(
    camera_id=0,
    use_faiss=False,
    detection_threshold=None,
    recognition_threshold=None,
    record=False,
    output_path=None,
):
    """
    Run live face recognition using webcam.

    Args:
        camera_id: Camera ID
        use_faiss: Whether to use FAISS for database
        detection_threshold: Detection confidence threshold
        recognition_threshold: Recognition similarity threshold
        record: Whether to record video
        output_path: Path to save recorded video
    """
    # Set thresholds
    if detection_threshold is None:
        detection_threshold = settings.DETECTION_THRESHOLD

    if recognition_threshold is None:
        recognition_threshold = settings.RECOGNITION_THRESHOLD

    # Initialize verifier
    verifier = AccessVerifier(
        detection_threshold=detection_threshold,
        recognition_threshold=recognition_threshold,
        use_faiss=use_faiss,
    )

    # Import here to avoid dependency issues
    import cv2

    # Open camera
    cap = cv2.VideoCapture(camera_id)

    if not cap.isOpened():
        logger.error(f"Error: Could not open camera {camera_id}")
        return

    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.FRAME_HEIGHT)

    # Create video writer if recording
    video_writer = None
    if record:
        if output_path is None:
            output_path = os.path.join(
                settings.DATA_DIR,
                "recordings",
                f"recording_{time.strftime('%Y%m%d_%H%M%S')}.mp4",
            )

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Get frame width and height
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(
            output_path, fourcc, 20.0, (frame_width, frame_height)
        )

        logger.info(f"Recording video to {output_path}")

    logger.info(f"Starting live recognition with camera {camera_id}")
    logger.info(f"Detection threshold: {detection_threshold}")
    logger.info(f"Recognition threshold: {recognition_threshold}")
    logger.info(f"Using {'FAISS' if use_faiss else 'standard'} database")
    logger.info("Press 'q' to quit, 's' to take screenshot")

    try:
        while True:
            # Read frame
            ret, frame = cap.read()

            if not ret:
                logger.warning("Error: Could not read frame")
                break

            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)

            # Verify face and create annotated image
            result = verifier.verify_and_display(frame)

            # Write frame if recording
            if video_writer is not None:
                video_writer.write(result)

            # Display frame
            try:
                cv2.imshow("Face Recognition", result)
            except cv2.error as e:
                logger.error(f"Could not display frame: {e}")
                logger.info("GUI support not available in this OpenCV build.")
                # Save some frames as fallback if recording is not enabled
                if not record and int(time.time()) % 5 == 0:  # Save every 5 seconds
                    fallback_path = os.path.join(
                        settings.DATA_DIR,
                        "frames",
                        f"frame_{time.strftime('%Y%m%d_%H%M%S')}.jpg",
                    )
                    os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                    cv2.imwrite(fallback_path, result)
                break  # Exit the loop as we can't display frames

            # Check for key press
            key = cv2.waitKey(1) & 0xFF

            # Quit if 'q' pressed
            if key == ord("q"):
                break

            # Take screenshot if 's' pressed
            elif key == ord("s"):
                screenshot_path = os.path.join(
                    settings.DATA_DIR,
                    "screenshots",
                    f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.jpg",
                )

                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

                # Save screenshot
                cv2.imwrite(screenshot_path, result)
                logger.info(f"Saved screenshot to {screenshot_path}")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected")

    finally:
        # Clean up
        cap.release()
        if video_writer is not None:
            video_writer.release()
        cv2.destroyAllWindows()

        # Log access attempts
        access_log = verifier.get_access_log()
        logger.info(f"Total access attempts: {len(access_log)}")

        # Count granted vs denied
        granted = sum(1 for entry in access_log if entry["access_granted"])
        denied = len(access_log) - granted

        logger.info(f"Access granted: {granted}, denied: {denied}")
        logger.info("Live recognition stopped")


def main():
    """Main entry point."""
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Face Recognition Access Control System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create database from folders
  python main.py create-db --root /path/to/face/data
  
  # Test recognition with an image
  python main.py test --image /path/to/test.jpg
  
  # Run live recognition
  python main.py live
  
  # Run live recognition with recording
  python main.py live --record
        """,
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create database parser
    create_parser = subparsers.add_parser(
        "create-db", help="Create face embeddings database"
    )
    create_parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="Root folder containing person subfolders",
    )
    create_parser.add_argument("--db-path", type=str, help="Path to store the database")
    create_parser.add_argument(
        "--use-faiss", action="store_true", help="Use FAISS for database"
    )
    create_parser.add_argument(
        "--min-faces",
        type=int,
        default=1,
        help="Minimum number of faces required per person",
    )

    # Test recognition parser
    test_parser = subparsers.add_parser(
        "test", help="Test face recognition on a single image"
    )
    test_parser.add_argument(
        "--image", type=str, required=True, help="Path to test image"
    )
    test_parser.add_argument(
        "--use-faiss", action="store_true", help="Use FAISS for database"
    )
    test_parser.add_argument(
        "--detection-threshold", type=float, help="Detection confidence threshold"
    )
    test_parser.add_argument(
        "--recognition-threshold", type=float, help="Recognition similarity threshold"
    )
    test_parser.add_argument(
        "--no-display", action="store_true", help="Do not display the result"
    )
    test_parser.add_argument("--save", type=str, help="Path to save the result image")

    # Live recognition parser
    live_parser = subparsers.add_parser("live", help="Run live face recognition")
    live_parser.add_argument("--camera", type=int, default=0, help="Camera ID")
    live_parser.add_argument(
        "--use-faiss", action="store_true", help="Use FAISS for database"
    )
    live_parser.add_argument(
        "--detection-threshold", type=float, help="Detection confidence threshold"
    )
    live_parser.add_argument(
        "--recognition-threshold", type=float, help="Recognition similarity threshold"
    )
    live_parser.add_argument("--record", action="store_true", help="Record video")
    live_parser.add_argument("--output", type=str, help="Path to save recorded video")

    # Parse arguments
    args = parser.parse_args()

    # Check if command is provided
    if args.command is None:
        parser.print_help()
        return

    # Execute command
    if args.command == "create-db":
        logger.info("Creating database...")
        create_database_from_folders(
            root_folder=args.root,
            db_path=args.db_path,
            use_faiss=args.use_faiss,
            min_faces_per_person=args.min_faces,
        )
        logger.info("Database creation completed")

    elif args.command == "test":
        logger.info("Testing recognition...")
        test_recognition(
            image_path=args.image,
            use_faiss=args.use_faiss,
            detection_threshold=args.detection_threshold,
            recognition_threshold=args.recognition_threshold,
            display=not args.no_display,
            save_path=args.save,
        )
        logger.info("Testing completed")

    elif args.command == "live":
        logger.info("Starting live recognition...")
        run_live_recognition(
            camera_id=args.camera,
            use_faiss=args.use_faiss,
            detection_threshold=args.detection_threshold,
            recognition_threshold=args.recognition_threshold,
            record=args.record,
            output_path=args.output,
        )
        logger.info("Live recognition completed")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Error in main: {e}")
        sys.exit(1)
