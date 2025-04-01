#!/usr/bin/env python3
"""
Script to create face_data directory structure for the face recognition system.
"""

import os
import shutil
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_face_data_structure():
    """Create face_data directory with sample subdirectories."""
    face_data_dir = "celeb_images"

    # Create main directory if it doesn't exist
    if not os.path.exists(face_data_dir):
        os.makedirs(face_data_dir)
        logger.info(f"Created {face_data_dir} directory")
    else:
        logger.info(f"{face_data_dir} directory already exists")

    # Create sample person directories
    sample_people = ["John_Doe", "Jane_Doe", "Sample_Person"]
    for person in sample_people:
        person_dir = os.path.join(face_data_dir, person)
        if not os.path.exists(person_dir):
            os.makedirs(person_dir)
            logger.info(f"Created {person_dir} directory")

    # Check if any sample images exist
    has_samples = False
    for person in sample_people:
        person_dir = os.path.join(face_data_dir, person)
        if os.listdir(person_dir):
            has_samples = True
            break

    if not has_samples:
        logger.info(
            "No sample images found. Please add face images to the person directories."
        )
        logger.info(
            "Sample directory structure created. Add face images to these directories."
        )
        logger.info("For example:")
        logger.info(f"  face_data/John_Doe/photo1.jpg")
        logger.info(f"  face_data/Jane_Doe/photo1.jpg")
        logger.info(f"  ...")

    # Create a README file
    readme_path = os.path.join(face_data_dir, "README.txt")
    with open(readme_path, "w") as f:
        f.write(
            """Face Data Directory

This directory contains face images organized by person for the face recognition system.

Directory Structure:
- Each subdirectory should be named after a person
- Each person's directory contains their face images
- Supported image formats: JPG, JPEG, PNG

Example:
face_data/
├── John_Doe/
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── Jane_Doe/
│   ├── image1.jpg
│   └── ...
└── ...

For best results:
- Use 5-10 clear face images per person
- Images should be well-lit with the face clearly visible
- Include different angles and expressions
- Minimum recommended resolution: 640x480
"""
        )

    logger.info(f"Created README file at {readme_path}")


if __name__ == "__main__":
    print("Creating face data directory structure...")
    create_face_data_structure()
    print("\nComplete! Now you can add face images to the person directories.")
    print("Then run: python main.py create-db --root face_data")
