"""
Tool to create face embeddings database from folders of images.
"""

import os
import sys
import logging
import argparse
import cv2
import numpy as np
from tqdm import tqdm

# Add project root to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from config import settings
from src.face.detector import FaceDetector
from src.face.embedder import FaceEmbedder
from src.database.embeddings_db import EmbeddingsDatabase
from src.database.faiss_db import FaissDatabase
from src.utils.image import is_image_file, read_image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(settings.LOG_DIR, "create_database.log")),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def create_database_from_folders(
    root_folder, db_path=None, use_faiss=False, min_faces_per_person=1
):
    """
    Create face embeddings database from folders of images.
    This creates a FRESH database - it does NOT append to existing data.

    Args:
        root_folder: Root folder containing subfolders named after people
        db_path: Path to store the database (if None, use default)
        use_faiss: Whether to use FAISS for database
        min_faces_per_person: Minimum number of faces required per person

    Returns:
        Database instance
    """
    # Initialize components
    detector = FaceDetector()
    embedder = FaceEmbedder()

    # Initialize database with a FRESH/EMPTY state
    # We create the database object but immediately clear it to ensure
    # we're building from scratch (not appending to existing data)
    if use_faiss:
        if db_path:
            db = FaissDatabase(db_path=db_path)
        else:
            db = FaissDatabase()
        # Clear existing data for fresh rebuild
        db.clear_database()
    else:
        if db_path:
            db = EmbeddingsDatabase(db_path=db_path)
        else:
            db = EmbeddingsDatabase()
        # Clear existing data for fresh rebuild
        db.database = {}

    logger.info(f"Creating FRESH database from {root_folder}")
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

    # Process each person folder
    for person_name in tqdm(person_folders, desc="Processing people"):
        person_folder = os.path.join(root_folder, person_name)

        logger.info(f"Processing {person_name}'s images...")

        # Read description file if it exists
        description = None
        info_txt_path = os.path.join(person_folder, "info.txt")
        info_json_path = os.path.join(person_folder, "info.json")

        if os.path.exists(info_txt_path):
            try:
                with open(info_txt_path, "r", encoding="utf-8") as f:
                    description = f.read().strip()
                logger.info(f"Found description file for {person_name}")
            except Exception as e:
                logger.warning(
                    f"Failed to read description file for {person_name}: {e}"
                )
        elif os.path.exists(info_json_path):
            try:
                import json

                with open(info_json_path, "r", encoding="utf-8") as f:
                    info_data = json.load(f)
                # Format JSON data as a readable string
                description_parts = []
                for key, value in info_data.items():
                    if key.lower() != "name":  # Skip name field
                        description_parts.append(f"{key.title()}: {value}")
                description = "\n".join(description_parts)
                logger.info(f"Found JSON description file for {person_name}")
            except Exception as e:
                logger.warning(
                    f"Failed to read JSON description file for {person_name}: {e}"
                )

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
        db.add_identity(person_name, avg_embedding, valid_images, description)
        logger.info(f"Added {person_name} to database with {valid_images} images")

    # Save database
    db.save_database()

    # Log database info
    db_info = db.get_database_info()
    logger.info(f"Database created with {db_info['num_identities']} identities")
    logger.info(f"Identities: {', '.join(db_info['identities'])}")

    return db


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Create face embeddings database")
    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="Root folder containing person subfolders",
    )
    parser.add_argument("--db-path", type=str, help="Path to store the database")
    parser.add_argument(
        "--use-faiss", action="store_true", help="Use FAISS for database"
    )
    parser.add_argument(
        "--min-faces",
        type=int,
        default=1,
        help="Minimum number of faces required per person",
    )

    args = parser.parse_args()

    # Create database
    create_database_from_folders(
        root_folder=args.root,
        db_path=args.db_path,
        use_faiss=args.use_faiss,
        min_faces_per_person=args.min_faces,
    )


if __name__ == "__main__":
    main()
