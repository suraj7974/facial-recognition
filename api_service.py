#!/usr/bin/env python3
"""
API service for the face recognition system.
This API allows for face recognition by accepting image uploads.
"""

import os
import sys
import logging
import json
import base64
import time
import numpy as np
import cv2
from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join("logs", f'api_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Import from our modules
from config import settings

try:
    from src.face.opencv_detector import FaceDetector

    logger.info("Using OpenCV detector")
except ImportError:
    try:
        from src.face.detector_fixed import FaceDetector

        logger.info("Using fixed detector")
    except ImportError:
        logger.error(
            "Could not import any detector! Please run fix_dependencies.py first."
        )
        sys.exit(1)

from src.face.embedder import FaceEmbedder
from src.database.embeddings_db import EmbeddingsDatabase
from src.database.faiss_db import FaissDatabase

# Initialize Flask application
app = Flask(__name__)

# Set up upload folder
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize components
detector = FaceDetector(detection_threshold=settings.DETECTION_THRESHOLD)
embedder = FaceEmbedder()

# Initialize database (choose between FAISS and standard)
if settings.USE_FAISS:
    database = FaissDatabase()
else:
    database = EmbeddingsDatabase()


def process_image_recognition(image_data, recognition_threshold=None):
    """
    Process image and perform face recognition.

    Args:
        image_data: Image data as numpy array
        recognition_threshold: Optional recognition threshold

    Returns:
        Dictionary with recognition results
    """
    if recognition_threshold is None:
        recognition_threshold = settings.RECOGNITION_THRESHOLD

    try:
        # Start timing
        start_time = time.time()

        # Detect face
        face = detector.get_largest_face(image_data)
        if face is None:
            return {
                "success": False,
                "error": "No face detected in image",
                "processing_time": time.time() - start_time,
            }

        # Get embedding
        embedding = embedder.get_embedding(face)
        if embedding is None:
            return {
                "success": False,
                "error": "Failed to get face embedding",
                "processing_time": time.time() - start_time,
            }

        # Match against database
        name, score = database.find_match(embedding, recognition_threshold)

        # Get all similarity scores
        all_scores = database.get_all_similarity_scores(embedding)
        top_matches = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:5]

        # Calculate bbox coordinates for response
        bbox = face.bbox.astype(int).tolist()

        # Prepare response
        result = {
            "success": True,
            "recognized": name is not None,
            "person_name": name if name else "Unknown",
            "confidence": float(score),
            "face_bbox": bbox,
            "top_matches": [{"name": p, "score": float(s)} for p, s in top_matches],
            "processing_time": time.time() - start_time,
        }

        return result

    except Exception as e:
        logger.exception(f"Error in image processing: {e}")
        return {
            "success": False,
            "error": str(e),
            "processing_time": (
                time.time() - start_time if "start_time" in locals() else 0
            ),
        }


@app.route("/api/recognize", methods=["POST"])
def recognize_face():
    """API endpoint for face recognition."""
    # Check if image file is present in request
    if "image" not in request.files and "image_base64" not in request.json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "No image provided. Send an image file or base64 encoded image.",
                }
            ),
            400,
        )

    # Get recognition threshold from request (optional)
    try:
        recognition_threshold = float(
            request.args.get("threshold", settings.RECOGNITION_THRESHOLD)
        )
    except ValueError:
        recognition_threshold = settings.RECOGNITION_THRESHOLD

    # Process file upload
    if "image" in request.files:
        file = request.files["image"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No selected file"}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{int(time.time())}_{filename}"
        )
        file.save(filepath)

        # Read image
        img = cv2.imread(filepath)
        if img is None:
            return (
                jsonify({"success": False, "error": "Failed to read image file"}),
                400,
            )

        logger.info(f"Processing uploaded file: {filename}")

    # Process base64 encoded image
    elif "image_base64" in request.json:
        try:
            # Decode base64 image
            image_data = request.json["image_base64"]
            # Remove data URL prefix if present
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]

            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_data)

            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return (
                    jsonify(
                        {"success": False, "error": "Failed to decode base64 image"}
                    ),
                    400,
                )

            logger.info("Processing base64 encoded image")
        except Exception as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Error processing base64 image: {str(e)}",
                    }
                ),
                400,
            )

    # Process the image
    result = process_image_recognition(img, recognition_threshold)

    # Return the result
    return jsonify(result)


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "ok",
            "time": datetime.now().isoformat(),
            "database_size": len(database.get_database_info()["identities"]),
        }
    )


@app.route("/api/database/info", methods=["GET"])
def database_info():
    """Get database information."""
    db_info = database.get_database_info()
    return jsonify(
        {
            "success": True,
            "database_type": "FAISS" if settings.USE_FAISS else "Standard",
            "num_identities": db_info["num_identities"],
            "identities": db_info["identities"],
        }
    )


if __name__ == "__main__":
    # Check if database has identities
    db_info = database.get_database_info()
    if db_info["num_identities"] == 0:
        logger.warning("Database is empty. Please add identities first.")
        print("Warning: Database is empty. Please create a database first:")
        print("  python main.py create-db --root face_data")

    # Get port from environment or use default
    port = int(os.environ.get("PORT", 5000))

    # Run the application
    logger.info(f"Starting API server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
