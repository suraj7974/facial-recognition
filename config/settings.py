"""
Configuration settings for the face recognition system.
"""

import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "face_db.pkl")
FAISS_DB_PATH = os.path.join(DATA_DIR, "face_db_faiss.bin")
FAISS_LABELS_PATH = os.path.join(DATA_DIR, "face_db_labels.pkl")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Face Detection and Recognition
DETECTION_THRESHOLD = 0.6  # Confidence threshold for face detection
RECOGNITION_THRESHOLD = 0.5  # Similarity threshold for face recognition
USE_FAISS = False  # Whether to use FAISS for database operations
MODEL_NAME = "buffalo_l"  # InsightFace model name

# Face Detection Context
DET_SIZE = (640, 640)  # Detection size
CTX_ID = 0  # 0 for GPU, -1 for CPU

# Image Processing
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Initialize directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
