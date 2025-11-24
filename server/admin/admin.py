# admin.py
import os
import sys
import shutil
import subprocess
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

# ---------- CONFIG ----------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
# Use your Windows absolute path
CELEB_ROOT = PROJECT_ROOT / "server" / "data" / "celeb_images"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
MAIN_SCRIPT = PROJECT_ROOT / "server" / "main.py"
PYTHON = sys.executable
LOG_DIR = PROJECT_ROOT / "logs"
PORT = 5001
# ---------------------------

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

CELEB_ROOT.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


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
    # optional: further restrictions could be applied (max length, allowed charset)
    return name


def ensure_within_root(path: Path):
    """
    Ensure that resolved path is inside CELEB_ROOT. Raises ValueError if not.
    """
    try:
        path_resolved = path.resolve()
        root_resolved = CELEB_ROOT.resolve()
        # Python 3.9+: use relative_to
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
    # Flask auto-decodes percent-encoding; name may contain spaces now
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
    # person and filename can contain spaces (browser uses percent-encoding)
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
    # send_from_directory safely serves file; filename may contain spaces
    return send_from_directory(str(folder), filename)


@app.route("/api/enroll", methods=["POST"])
def api_enroll():
    name = (request.form.get("name") or "").strip()
    info = request.form.get("info") or ""
    files = request.files.getlist("images")

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
        if f and allowed_file(f.filename):
            # keep original filename but prefix timestamp to avoid collisions
            fname = secure_filename(f.filename)
            out_path = folder / f"{int(os.times()[4])}_{fname}"
            f.save(str(out_path))
            saved += 1
    return jsonify({"success": True, "message": f"saved {saved} images to {folder}"})


@app.route("/api/add_image", methods=["POST"])
def api_add_image():
    person = (request.form.get("person") or "").strip()
    f = request.files.get("image")
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
        out_path = folder / f"{int(os.times()[4])}_{fname}"
        f.save(str(out_path))
        return jsonify({"success": True, "message": f"saved {out_path}"})
    return jsonify({"success": False, "error": "invalid file type"}), 400


@app.route("/api/delete_person", methods=["POST"])
def api_delete_person():
    person = (request.form.get("person") or "").strip()
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
    return jsonify({"success": True, "message": f"deleted {folder}"})


@app.route("/api/rebuild_db", methods=["POST"])
def api_rebuild_db():
    if not MAIN_SCRIPT.exists():
        return (
            jsonify(
                {"success": False, "error": f"main script not found: {MAIN_SCRIPT}"}
            ),
            500,
        )
    cmd = [PYTHON, str(MAIN_SCRIPT), "create-db", "--root", str(CELEB_ROOT)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    lf = LOG_DIR / f"rebuild_{int(os.times()[4])}.log"
    lf.write_text(proc.stdout + "\n\nSTDERR:\n" + proc.stderr, encoding="utf-8")
    
    # Touch the api_service.py to trigger a reload
    os.utime(PROJECT_ROOT / "server" / "api_service.py", None)
    
    return jsonify(
        {
            "success": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    )


@app.route("/api/latest_log")
def api_latest_log():
    lf = latest_log_file()
    if lf is None:
        return jsonify({"content": "No logs found"})
    try:
        txt = lf.read_text(encoding="utf-8", errors="ignore")
        if len(txt) > 20000:
            txt = txt[-20000:]
        return jsonify({"content": txt})
    except Exception as e:
        return jsonify({"content": f"Failed to read log: {e}"})


if __name__ == "__main__":
    print(f"Starting admin (serve admin.html from {BASE_DIR})")
    print(f"Open http://127.0.0.1:{PORT}/admin.html")
    app.run(host="0.0.0.0", port=PORT, debug=False)
