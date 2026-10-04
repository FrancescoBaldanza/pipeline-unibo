import os
import sys
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pymupdf

from config.settings import (
    TARGET_ROOT,
    NOTEBOOKS,
    PYTHON_BIN,
    STAGING_DIR
)
from core.tracker import PipelineTracker, calculate_sha256


def clean_display_name(name: str) -> str:
    cleaned = re.sub(r"^\s*\((?:NEW|New|new)\)\s*", "", name)
    return cleaned.strip()


def validate_for_notebooklm(file_path: Path) -> Tuple[bool, str]:
    if not file_path.exists():
        return False, "File non trovato su disco"

    filename = file_path.name
    if filename.startswith(".") or filename.endswith("~") or filename.endswith(".tmp"):
        return False, "File temporaneo o nascosto"

    if filename.startswith("ERRORE_"):
        return False, "File contrassegnato con ERRORE_"

    ext = file_path.suffix.lower()
    if ext not in (".pdf", ".md"):
        return False, f"Formato non supportato: '{ext}'"

    file_size = file_path.stat().st_size
    if file_size == 0:
        return False, "File vuoto (0 byte)"

    max_bytes = 200 * 1024 * 1024
    if file_size > max_bytes:
        return False, f"Dimensione eccede 200 MB ({file_size / (1024 * 1024):.1f} MB)"

    if ext == ".pdf":
        try:
            doc = pymupdf.open(str(file_path))
            if len(doc) == 0:
                doc.close()
                return False, "PDF privo di pagine"
            if doc.is_encrypted:
                doc.close()
                return False, "PDF protetto da password"
            doc.close()
        except Exception as e:
            return False, f"PDF non valido ({e})"

    if ext == ".md":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(500)
            if len(content.strip()) < 30:
                return False, "Markdown troppo corto o vuoto"
        except Exception as e:
            return False, f"Impossibile leggere file MD ({e})"

    return True, "OK"


class NotebookLMSyncManager:

    def __init__(self, tracker: Optional[PipelineTracker] = None):
        self.tracker = tracker or PipelineTracker()

    def check_auth(self) -> bool:
        try:
            cmd = [PYTHON_BIN, "-m", "notebooklm", "auth", "check"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return res.returncode == 0
        except Exception:
            return False

    def upload_single_source(self, course_name: str, file_path: Path) -> bool:
        can_upload, reason = validate_for_notebooklm(file_path)
        if not can_upload:
            if not file_path.name.startswith("."):
                print(f"    File escluso dall'upload ({file_path.name}): {reason}")
            return False

        notebook_id = NOTEBOOKS.get(course_name)
        if not notebook_id:
            print(f"  ️ Nessun Notebook ID configurato per il corso: {course_name}")
            return False

        sha256 = calculate_sha256(file_path)
        if self.tracker.is_uploaded_to_notebooklm(course_name, sha256):
            return False

        filename = file_path.name
        clean_title = clean_display_name(filename)
        title_stem = Path(clean_title).stem

        print(f"   Upload NotebookLM ({course_name}): '{clean_title}'...")

        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        staged_file = STAGING_DIR / clean_title
        target_path_to_upload = file_path.resolve()
        need_cleanup = False

        if filename != clean_title:
            try:
                shutil.copy2(file_path, staged_file)
                target_path_to_upload = staged_file
                need_cleanup = True
            except Exception:
                target_path_to_upload = file_path.resolve()

        cmd = [
            PYTHON_BIN,
            "-m",
            "notebooklm",
            "source",
            "add",
            str(target_path_to_upload),
            "-n",
            notebook_id,
            "--title",
            title_stem,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                print(f"\tCaricato con successo in NotebookLM: '{title_stem}'")
                self.tracker.record_notebooklm_upload(course_name, sha256, filename)
                return True
            else:
                err_msg = res.stderr or res.stdout
                print(f"\tErrore upload NotebookLM ({clean_title}): {err_msg.strip()[:200]}")
                return False
        except Exception as e:
            print(f"\tEccezione durante l'upload NotebookLM: {e}")
            return False
        finally:
            if need_cleanup and staged_file.exists():
                try:
                    os.remove(staged_file)
                except Exception:
                    pass

    def sync_course(self, course_name: str, course_dir: Path) -> int:
        if not course_dir.exists():
            return 0

        print(f"\n[SYNC] NotebookLM -> {course_name}")
        uploaded_count = 0

        for root, dirs, files in os.walk(course_dir):
            if Path(root).name == "images":
                continue

            for f in sorted(files):
                if f.startswith("."):
                    continue
                file_path = Path(root) / f
                ext = file_path.suffix.lower()

                if ext not in (".pdf", ".md"):
                    continue

                if self.upload_single_source(course_name, file_path):
                    uploaded_count += 1

        return uploaded_count

    def sync_all(self) -> Dict[str, int]:
        if not self.check_auth():
            print("Errore: Autenticazione NotebookLM non attiva. Esegui 'notebooklm login'.")
            return {}

        results = {}
        for course_name in NOTEBOOKS.keys():
            course_dir = TARGET_ROOT / course_name
            count = self.sync_course(course_name, course_dir)
            results[course_name] = count

        return results
