# admin.py - Modern Admin API with Auto-Rebuild
import os
import sys
import shutil
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests

# ---------- CONFIG ----------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent  # /face_recognition_system
CELEB_ROOT = PROJECT_ROOT / "server" / "data" / "celeb_images"
ALLOWED_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".gif",
    ".tiff",
    ".tif",
    ".heic",
    ".heif",
    ".avif",
}
MAIN_SCRIPT = PROJECT_ROOT / "server" / "main.py"
PYTHON = sys.executable
LOG_DIR = PROJECT_ROOT / "logs"
PORT = 5001
API_SERVER_URL = "http://localhost:5000"
# ---------------------------

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)  # Enable CORS for React dev server

CELEB_ROOT.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------- REBUILD STATUS TRACKING ----------
rebuild_status = {
    "is_rebuilding": False,
    "progress": 0,
    "status": "idle",  # idle, rebuilding, reloading, completed, failed
    "message": "",
    "started_at": None,
    "completed_at": None,
    "last_error": None,
    "triggered_by": None,  # enroll, delete, add_image, manual
}
rebuild_lock = threading.Lock()


def update_rebuild_status(**kwargs):
    """Thread-safe update of rebuild status."""
    with rebuild_lock:
        rebuild_status.update(kwargs)


def get_rebuild_status():
    """Thread-safe read of rebuild status."""
    with rebuild_lock:
        return rebuild_status.copy()


# ---------- HELPER FUNCTIONS ----------
def allowed_file(filename: str) -> bool:
    return "." in filename and Path(filename).suffix.lower() in ALLOWED_EXT


def validate_name_safe(name: str) -> str:
    """
    Validate folder name provided by user:
    - must not be empty
    - must not contain path separators or traversal segments like '..', '/' or '\'
    - spaces are allowed
    Returns the original name (not sanitized) on success.
    """
    if not name:
        raise ValueError("empty name")
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("invalid characters in name")
    return name


def ensure_within_root(path: Path):
    """
    Ensure that resolved path is inside CELEB_ROOT. Raises ValueError if not.
    """
    try:
        path_resolved = path.resolve()
        root_resolved = CELEB_ROOT.resolve()
        path_resolved.relative_to(root_resolved)
    except Exception:
        raise ValueError("path escapes celeb root")


def list_identities():
    out = []
    for p in sorted(CELEB_ROOT.iterdir()):
        if p.is_dir():
            cnt = sum(1 for f in p.iterdir() if f.suffix.lower() in ALLOWED_EXT)
            out.append((p.name, cnt))
    return out


def latest_log_file():
    files = [f for f in LOG_DIR.iterdir() if f.is_file()] if LOG_DIR.exists() else []
    if not files:
        return None
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]


# ---------- DATABASE REBUILD FUNCTIONS ----------
def trigger_api_reload():
    """
    Notify the main API server to reload its database from disk.
    Returns True on success, False on failure.
    """
    try:
        response = requests.post(f"{API_SERVER_URL}/api/database/reload", timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("success", False), data
        else:
            return False, {"error": f"API returned status {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return False, {"error": "API server not reachable"}
    except Exception as e:
        return False, {"error": str(e)}


def run_database_rebuild(triggered_by="manual"):
    """
    Run the database rebuild process in the current thread.
    Updates rebuild_status throughout the process.
    """
    update_rebuild_status(
        is_rebuilding=True,
        progress=10,
        status="rebuilding",
        message="Starting database rebuild...",
        started_at=datetime.now().isoformat(),
        completed_at=None,
        last_error=None,
        triggered_by=triggered_by,
    )

    try:
        # Run the create-db command
        update_rebuild_status(progress=20, message="Processing face images...")

        if not MAIN_SCRIPT.exists():
            raise Exception(f"Main script not found: {MAIN_SCRIPT}")

        cmd = [PYTHON, str(MAIN_SCRIPT), "create-db", "--root", str(CELEB_ROOT)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Log the output
        lf = LOG_DIR / f"rebuild_{int(time.time())}.log"
        lf.write_text(
            f"Triggered by: {triggered_by}\n"
            f"Time: {datetime.now().isoformat()}\n"
            f"Command: {' '.join(cmd)}\n\n"
            f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
            encoding="utf-8",
        )

        if proc.returncode != 0:
            raise Exception(f"Database rebuild failed: {proc.stderr}")

        update_rebuild_status(
            progress=70,
            status="reloading",
            message="Notifying API server to reload database...",
        )

        # Trigger API server to reload
        success, result = trigger_api_reload()

        if success:
            num_identities = result.get("num_identities", 0)
            update_rebuild_status(
                is_rebuilding=False,
                progress=100,
                status="completed",
                message=f"Database rebuilt successfully with {num_identities} identities",
                completed_at=datetime.now().isoformat(),
            )
        else:
            # Database was rebuilt but API reload failed
            update_rebuild_status(
                is_rebuilding=False,
                progress=100,
                status="completed",
                message=f"Database rebuilt but API reload failed: {result.get('error', 'Unknown error')}. Restart API server manually.",
                completed_at=datetime.now().isoformat(),
                last_error=result.get("error"),
            )

    except subprocess.TimeoutExpired:
        update_rebuild_status(
            is_rebuilding=False,
            progress=0,
            status="failed",
            message="Database rebuild timed out after 5 minutes",
            completed_at=datetime.now().isoformat(),
            last_error="Timeout",
        )
    except Exception as e:
        update_rebuild_status(
            is_rebuilding=False,
            progress=0,
            status="failed",
            message=f"Database rebuild failed: {str(e)}",
            completed_at=datetime.now().isoformat(),
            last_error=str(e),
        )


def async_rebuild(triggered_by="manual"):
    """
    Start database rebuild in a background thread.
    Returns immediately, status can be checked via /api/rebuild_status
    """
    current_status = get_rebuild_status()
    if current_status["is_rebuilding"]:
        return False, "Rebuild already in progress"

    thread = threading.Thread(
        target=run_database_rebuild, args=(triggered_by,), daemon=True
    )
    thread.start()
    return True, "Rebuild started"


# ---------- API ENDPOINTS ----------


# Serve admin.html from the script directory
@app.route("/admin.html")
def admin_page():
    html_path = BASE_DIR / "admin.html"
    if not html_path.exists():
        return f"admin.html not found in {BASE_DIR}", 404
    return send_from_directory(str(BASE_DIR), "admin.html")


@app.route("/api/identities")
def api_identities():
    return jsonify({"identities": list_identities()})


@app.route("/api/person/<name>")
def api_person(name):
    try:
        name = validate_name_safe(name)
    except ValueError:
        return jsonify({"error": "invalid name"}), 400
    folder = CELEB_ROOT / name
    try:
        ensure_within_root(folder)
    except ValueError:
        return jsonify({"error": "invalid path"}), 400
    if not folder.exists():
        return jsonify({"error": "person not found"}), 404
    imgs = [f.name for f in sorted(folder.iterdir()) if f.suffix.lower() in ALLOWED_EXT]
    info_file = folder / "info.txt"
    info = info_file.read_text(encoding="utf-8") if info_file.exists() else ""
    return jsonify({"images": imgs, "info": info})


@app.route("/images/<person>/<filename>")
def serve_image(person, filename):
    try:
        person = validate_name_safe(person)
    except ValueError:
        return "Invalid person name", 400
    folder = CELEB_ROOT / person
    try:
        ensure_within_root(folder)
    except ValueError:
        return "Invalid path", 400
    file_path = folder / filename
    if not file_path.exists():
        return "Not found", 404
    return send_from_directory(str(folder), filename)


@app.route("/api/enroll", methods=["POST"])
def api_enroll():
    """Enroll a new identity with auto-rebuild."""
    name = (request.form.get("name") or "").strip()
    info = request.form.get("info") or ""
    files = request.files.getlist("images")
    auto_rebuild = request.form.get("auto_rebuild", "true").lower() == "true"

    if not name or not files:
        return (
            jsonify(
                {"success": False, "error": "name and at least one image required"}
            ),
            400,
        )
    try:
        name = validate_name_safe(name)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    folder = CELEB_ROOT / name
    try:
        ensure_within_root(folder.parent)
    except ValueError:
        return jsonify({"success": False, "error": "invalid folder location"}), 400

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "info.txt").write_text(info or "", encoding="utf-8")

    saved = 0
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            fname = secure_filename(f.filename)
            out_path = folder / f"{int(time.time() * 1000)}_{fname}"
            f.save(str(out_path))
            saved += 1

    response = {
        "success": True,
        "message": f"Saved {saved} images for {name}",
        "person": name,
        "images_saved": saved,
    }

    # Auto-rebuild if enabled
    if auto_rebuild and saved > 0:
        started, msg = async_rebuild(triggered_by="enroll")
        response["rebuild_started"] = started
        response["rebuild_message"] = msg

    return jsonify(response)


@app.route("/api/add_image", methods=["POST"])
def api_add_image():
    """Add an image to an existing identity with auto-rebuild."""
    person = (request.form.get("person") or "").strip()
    f = request.files.get("image")
    auto_rebuild = request.form.get("auto_rebuild", "true").lower() == "true"

    if not person or not f:
        return jsonify({"success": False, "error": "person and image required"}), 400
    try:
        person = validate_name_safe(person)
    except ValueError:
        return jsonify({"success": False, "error": "invalid person name"}), 400

    folder = CELEB_ROOT / person
    try:
        ensure_within_root(folder)
    except ValueError:
        return jsonify({"success": False, "error": "invalid folder path"}), 400
    if not folder.exists():
        return jsonify({"success": False, "error": "person not found"}), 404

    if f and allowed_file(f.filename):
        fname = secure_filename(f.filename)
        out_path = folder / f"{int(time.time() * 1000)}_{fname}"
        f.save(str(out_path))

        response = {
            "success": True,
            "message": f"Added image to {person}",
            "person": person,
            "filename": out_path.name,
        }

        # Auto-rebuild if enabled
        if auto_rebuild:
            started, msg = async_rebuild(triggered_by="add_image")
            response["rebuild_started"] = started
            response["rebuild_message"] = msg

        return jsonify(response)

    return jsonify({"success": False, "error": "invalid file type"}), 400


@app.route("/api/delete_person", methods=["POST"])
def api_delete_person():
    """Delete an identity with auto-rebuild."""
    person = (request.form.get("person") or "").strip()
    auto_rebuild = request.form.get("auto_rebuild", "true").lower() == "true"

    try:
        person = validate_name_safe(person)
    except ValueError:
        return jsonify({"success": False, "error": "invalid name"}), 400
    folder = CELEB_ROOT / person
    try:
        ensure_within_root(folder)
    except ValueError:
        return jsonify({"success": False, "error": "invalid folder path"}), 400
    if not folder.exists():
        return jsonify({"success": False, "error": "person not found"}), 404

    shutil.rmtree(folder)

    response = {
        "success": True,
        "message": f"Deleted {person}",
        "person": person,
    }

    # Auto-rebuild if enabled
    if auto_rebuild:
        started, msg = async_rebuild(triggered_by="delete")
        response["rebuild_started"] = started
        response["rebuild_message"] = msg

    return jsonify(response)


@app.route("/api/delete_image", methods=["POST"])
def api_delete_image():
    """Delete a single image from an identity with auto-rebuild."""
    person = (request.form.get("person") or "").strip()
    filename = (request.form.get("filename") or "").strip()
    auto_rebuild = request.form.get("auto_rebuild", "true").lower() == "true"

    try:
        person = validate_name_safe(person)
    except ValueError:
        return jsonify({"success": False, "error": "invalid person name"}), 400

    if not filename:
        return jsonify({"success": False, "error": "filename required"}), 400

    folder = CELEB_ROOT / person
    try:
        ensure_within_root(folder)
    except ValueError:
        return jsonify({"success": False, "error": "invalid folder path"}), 400

    if not folder.exists():
        return jsonify({"success": False, "error": "person not found"}), 404

    file_path = folder / filename
    if not file_path.exists():
        return jsonify({"success": False, "error": "image not found"}), 404

    # Ensure file is within the folder (prevent traversal)
    try:
        file_path.resolve().relative_to(folder.resolve())
    except ValueError:
        return jsonify({"success": False, "error": "invalid file path"}), 400

    file_path.unlink()

    response = {
        "success": True,
        "message": f"Deleted {filename} from {person}",
        "person": person,
        "filename": filename,
    }

    # Auto-rebuild if enabled
    if auto_rebuild:
        started, msg = async_rebuild(triggered_by="delete_image")
        response["rebuild_started"] = started
        response["rebuild_message"] = msg

    return jsonify(response)


@app.route("/api/rebuild_db", methods=["POST"])
def api_rebuild_db():
    """Manual database rebuild (async)."""
    current_status = get_rebuild_status()
    if current_status["is_rebuilding"]:
        return jsonify(
            {
                "success": False,
                "error": "Rebuild already in progress",
                "status": current_status,
            }
        ), 409

    started, msg = async_rebuild(triggered_by="manual")

    if started:
        return jsonify(
            {"success": True, "message": msg, "status": get_rebuild_status()}
        )
    else:
        return jsonify(
            {"success": False, "error": msg, "status": get_rebuild_status()}
        ), 409


@app.route("/api/rebuild_status")
def api_rebuild_status():
    """Get current rebuild status."""
    return jsonify(get_rebuild_status())


@app.route("/api/latest_log")
def api_latest_log():
    lf = latest_log_file()
    if lf is None:
        return jsonify({"content": "No logs found"})
    try:
        txt = lf.read_text(encoding="utf-8", errors="ignore")
        if len(txt) > 20000:
            txt = txt[-20000:]
        return jsonify({"content": txt, "filename": lf.name})
    except Exception as e:
        return jsonify({"content": f"Failed to read log: {e}"})


@app.route("/api/stats")
def api_stats():
    """Get dashboard statistics."""
    identities = list_identities()
    total_images = sum(cnt for _, cnt in identities)

    # Get database file info
    db_file = PROJECT_ROOT / "server" / "data" / "face_db.pkl"
    db_info = {
        "exists": db_file.exists(),
        "size": db_file.stat().st_size if db_file.exists() else 0,
        "modified": datetime.fromtimestamp(db_file.stat().st_mtime).isoformat()
        if db_file.exists()
        else None,
    }

    return jsonify(
        {
            "total_identities": len(identities),
            "total_images": total_images,
            "database": db_info,
            "rebuild_status": get_rebuild_status(),
        }
    )


if __name__ == "__main__":
    print(f"Starting admin server on port {PORT}")
    print(f"Celeb images root: {CELEB_ROOT}")
    print(f"API server URL: {API_SERVER_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
