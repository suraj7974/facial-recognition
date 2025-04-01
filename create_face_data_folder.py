#!/usr/bin/env python3
"""
Create a basic face data folder structure for testing the system.
"""

import os
import shutil
import argparse
import logging
import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def create_sample_face_image(size=(640, 480), name="sample"):
    """Create a simple sample face image."""
    # Create a blank image
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)

    # Fill with a light gray background
    img.fill(200)

    # Draw a basic face shape
    center_x, center_y = size[0] // 2, size[1] // 2
    face_radius = min(size) // 3

    # Draw face circle
    cv2.circle(img, (center_x, center_y), face_radius, (220, 210, 170), -1)

    # Draw eyes
    eye_radius = face_radius // 5
    left_eye_x = center_x - face_radius // 2
    right_eye_x = center_x + face_radius // 2
    eyes_y = center_y - face_radius // 4

    cv2.circle(img, (left_eye_x, eyes_y), eye_radius, (255, 255, 255), -1)
    cv2.circle(img, (right_eye_x, eyes_y), eye_radius, (255, 255, 255), -1)

    # Draw pupils
    pupil_radius = eye_radius // 2
    cv2.circle(img, (left_eye_x, eyes_y), pupil_radius, (0, 0, 0), -1)
    cv2.circle(img, (right_eye_x, eyes_y), pupil_radius, (0, 0, 0), -1)

    # Draw mouth
    mouth_y = center_y + face_radius // 2
    cv2.ellipse(
        img,
        (center_x, mouth_y),
        (face_radius // 2, face_radius // 4),
        0,
        0,
        180,
        (0, 0, 0),
        2,
    )

    # Draw name
    cv2.putText(
        img,
        name,
        (center_x - face_radius, center_y + face_radius + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
    )

    return img


def create_face_data_folder(base_path="face_data", num_persons=3, images_per_person=5):
    """
    Create a basic face data folder structure.

    Args:
        base_path: Base path for face data
        num_persons: Number of sample persons to create
        images_per_person: Number of images per person
    """
    logger.info(f"Creating face data folder at {base_path}")

    # Create base folder if it doesn't exist
    os.makedirs(base_path, exist_ok=True)

    # Create person folders with sample images
    for i in range(1, num_persons + 1):
        person_name = f"Person_{i}"
        person_folder = os.path.join(base_path, person_name)

        # Create person folder
        os.makedirs(person_folder, exist_ok=True)
        logger.info(f"Created folder for {person_name}")

        # Create sample images
        for j in range(1, images_per_person + 1):
            img_name = f"image_{j}.jpg"
            img_path = os.path.join(person_folder, img_name)

            # Create a sample face image
            img = create_sample_face_image(name=person_name)

            # Make each image slightly different
            # Add some random noise
            noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
            img = cv2.add(img, noise)

            # Save image
            cv2.imwrite(img_path, img)
            logger.info(f"Created sample image: {img_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create a basic face data folder structure"
    )
    parser.add_argument("--output", default="face_data", help="Output folder path")
    parser.add_argument(
        "--persons", type=int, default=3, help="Number of sample persons"
    )
    parser.add_argument("--images", type=int, default=5, help="Images per person")

    args = parser.parse_args()

    create_face_data_folder(
        base_path=args.output, num_persons=args.persons, images_per_person=args.images
    )

    logger.info("Face data folder creation complete.")
    logger.info(f"You can now run: python main.py create-db --root {args.output}")


if __name__ == "__main__":
    main()
