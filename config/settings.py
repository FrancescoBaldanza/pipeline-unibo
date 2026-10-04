from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
SOURCE_ROOT = Path("~/Desktop/Materiale").expanduser().resolve()
TARGET_ROOT = Path("~/Desktop/UniBo").expanduser().resolve()
TRACKER_FILE = Path(__file__).resolve().parent.parent / "data" / "pipeline_tracker.json"
TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
STAGING_DIR = Path("~/.unibo_pipeline_staging").expanduser().resolve()
PYTHON_BIN = "/Users/francescobaldanza/Workspace/miniconda3/bin/python3"
DLUB_BIN = "/Users/francescobaldanza/Workspace/miniconda3/bin/dlub"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".md"}

IGNORED_TARGET_COURSES = {
    "Analisi Matematica 2",
    "Reti Logiche",
    ".obsidian",
}

NOTEBOOKS = {
    "Architetture dei Calcolatori": "f28cf954-f4ca-4260-90d6-08c992246f79",
    "Basi di Dati": "b869784f-6d4f-48b9-8628-b573f7fd6b8e",
    "Matematica Applicata": "9a379012-88bf-441a-9855-452512d5550b",
    "Fisica Generale": "2de18ebb-7d45-4651-86df-cd84dadef0b2",
}