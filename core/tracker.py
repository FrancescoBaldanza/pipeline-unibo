import json
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from config.settings import TRACKER_FILE


def calculate_sha256(filepath: Path | str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class PipelineTracker:

    def __init__(self, tracker_path: Path = TRACKER_FILE):
        self.tracker_path = Path(tracker_path)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> dict:
        if self.tracker_path.exists():
            try:
                with open(self.tracker_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "converted_files": {},
            "notebooklm_uploads": {},
        }

    def save(self):
        self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracker_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _seed_from_legacy_if_needed(self):
        legacy_path = Path("~/.unibo_notebooklm_tracker.json").expanduser()
        if legacy_path.exists():
            try:
                with open(legacy_path, "r", encoding="utf-8") as f:
                    legacy_data = json.load(f)

                id_to_course = {
                    "81475": "Architetture dei Calcolatori",
                    "80238": "Basi di Dati",
                    "80900": "Matematica Applicata",
                    "83152": "Fisica Generale",
                }

                uploaded_hashes = legacy_data.get("uploaded_hashes", {})
                for c_id, hashes in uploaded_hashes.items():
                    c_name = id_to_course.get(c_id, c_id)
                    course_dict = self.data.setdefault("notebooklm_uploads", {}).setdefault(c_name, {})
                    for sha, info in hashes.items():
                        if sha not in course_dict:
                            course_dict[sha] = info

                uploaded_sources = legacy_data.get("uploaded_sources", {})
                for c_id, sources in uploaded_sources.items():
                    c_name = id_to_course.get(c_id, c_id)
                    course_dict = self.data.setdefault("notebooklm_uploads", {}).setdefault(c_name, {})
                    for fname, sha in sources.items():
                        if sha not in course_dict:
                            course_dict[sha] = {"filename": fname, "uploaded_at": "legacy"}

                self.save()
            except Exception:
                pass

    def is_converted(self, sha256_hash: str) -> bool:
        return sha256_hash in self.data.get("converted_files", {})

    def record_conversion(self, sha256_hash: str, source_pdf: str, md_output: str, semantic_title: str):
        self.data.setdefault("converted_files", {})[sha256_hash] = {
            "source_pdf": str(source_pdf),
            "md_output": str(md_output),
            "semantic_title": semantic_title,
            "converted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save()

    def is_uploaded_to_notebooklm(self, course_name: str, sha256_hash: str) -> bool:
        course_uploads = self.data.get("notebooklm_uploads", {}).get(course_name, {})
        return sha256_hash in course_uploads

    def record_notebooklm_upload(self, course_name: str, sha256_hash: str, filename: str):
        self.data.setdefault("notebooklm_uploads", {}).setdefault(course_name, {})[sha256_hash] = {
            "filename": filename,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save()
