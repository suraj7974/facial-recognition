#!/usr/bin/env python3
"""
Test face recognition without using GUI components.
This script is useful for environments where Qt/GUI is not properly configured.
"""

import os
import sys
import logging
import argparse
import cv2
import numpy as np
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Add project root to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from src.face.opencv_detector import FaceDetector  # Use OpenCV detector directly
from src.face.embedder import FaceEmbedder
from src.database.embeddings_db import EmbeddingsDatabase
from src.utils.image import read_image


def test_recognition_headless(image_path, output_path=None, threshold=0.5):
    """
    Test face recognition without GUI display.

    Args:
        image_path: Path to the test image
        output_path: Path to save the output image with recognition
        threshold: Recognition threshold
    """
    logger.info(f"Testing recognition on {image_path}")

    # Initialize components
    detector = FaceDetector()
    embedder = FaceEmbedder()
    database = EmbeddingsDatabase()

    # Read image
    img = read_image(image_path)
    if img is None:
        logger.error(f"Could not read image: {image_path}")
        return

    # Detect face
    face = detector.get_largest_face(img)
    if face is None:
        logger.error("No face detected in image")
        return

    logger.info("Face detected")

    # Get embedding
    embedding = embedder.get_embedding(face)
    if embedding is None:
        logger.error("Failed to get embedding")
        return

    # Find match
    name, score = database.find_match(embedding, threshold)

    # Draw result
    result_img = img.copy()
    color = (0, 255, 0) if name else (0, 0, 255)

    # Get face coordinates
    x1, y1, x2, y2 = face.bbox.astype(int)

    # Draw rectangle
    cv2.rectangle(result_img, (x1, y1), (x2, y2), color, 2)

    # Draw name and score
    if name:
        text = f"{name}: {score:.4f}"
        logger.info(f"Recognized as: {name} with score {score:.4f}")
    else:
        text = "Unknown"
        logger.info(f"Not recognized (max score: {score:.4f})")

    cv2.putText(
        result_img, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
    )

    # Get top matches
    all_scores = database.get_all_similarity_scores(embedding)
    top_matches = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:5]

    logger.info("Top 5 matches:")
    for person, similarity in top_matches:
        logger.info(f"  {person}: {similarity:.4f}")

    # Save result if output path is specified
    if output_path:
        # Fix for empty directory name: Make sure we use absolute paths or create directory if needed
        if os.path.dirname(output_path):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the output image
        cv2.imwrite(output_path, result_img)
        logger.info(f"Saved result to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Test face recognition without GUI")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--output", help="Path to save result image")
    parser.add_argument(
        "--threshold", type=float, default=0.5, help="Recognition threshold"
    )

    args = parser.parse_args()

    # Use a default output path in the current directory if not specified
    output_path = args.output
    if not output_path:
        # Create default output filename in current directory
        timestamp = int(time.time())
        output_path = f"recognition_result_{timestamp}.jpg"

    test_recognition_headless(
        image_path=args.image,
        output_path=output_path,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
