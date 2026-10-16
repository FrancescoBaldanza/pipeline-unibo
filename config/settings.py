from pathlib import Path
import os
from dotenv import load_dotenv

LOCAL_REPO_MATERIALE = Path(__file__).resolve().parent.parent / "materiale"
if LOCAL_REPO_MATERIALE.exists():
    SOURCE_ROOT = LOCAL_REPO_MATERIALE
else:
    SOURCE_ROOT = Path("~/Desktop/Materiale").expanduser().resolve()

TARGET_ROOT = Path("~/Desktop/UniBo").expanduser().resolve()
TRACKER_FILE = Path(__file__).resolve().parent.parent / "data" / "pipeline_tracker.json"
TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
STAGING_DIR = Path("~/.unibo_pipeline_staging").expanduser().resolve()
PYTHON_BIN = "/Users/francescobaldanza/Workspace/miniconda3/bin/python3"
DLUB_BIN = "/Users/francescobaldanza/Workspace/miniconda3/bin/dlub"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".md"}

PROCESS_SKILL_DIR = Path("/Users/francescobaldanza/.gemini/config/skills/process")
PROCESS_GATE_SCRIPT = PROCESS_SKILL_DIR / "scripts" / "verify_and_sanitize.py"

AI_LEZIONI_SUBDIR = ".ai/lezioni"
AI_ESERCIZI_SUBDIR = ".ai/esercizi"

IGNORED_TARGET_COURSES = {
    "Analisi Matematica 2",
    "Reti Logiche",
    ".obsidian",
}