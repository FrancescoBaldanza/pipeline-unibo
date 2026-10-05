import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

from config.settings import (
    SOURCE_ROOT,
    TARGET_ROOT,
    ALLOWED_EXTENSIONS,
    IGNORED_TARGET_COURSES
)
from config.course_rules import COURSE_RULES, CourseRule, clean_lesson_filename, format_slide_filename


class BaseSyncManager:

    def __init__(self, source_root: Path = SOURCE_ROOT, target_root: Path = TARGET_ROOT):
        self.source_root = Path(source_root).expanduser().resolve()
        self.target_root = Path(target_root).expanduser().resolve()

    def migrate_legacy_folders(self):
        print("Verifica ed eventuale migrazione note legacy...")
        
        fg_context = self.target_root / "Fisica Generale" / "Context"
        fg_lezioni = self.target_root / "Fisica Generale" / "Lezioni"
        if fg_context.exists():
            fg_lezioni.mkdir(parents=True, exist_ok=True)
            for item in fg_context.iterdir():
                if item.name.startswith("."):
                    continue
                dest = fg_lezioni / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
                print(f"   [Migrazione] Fisica Generale Context -> Lezioni: {item.name}")
            shutil.rmtree(fg_context)
            print("   [OK] Cartella 'Fisica Generale/Context' rimossa con successo.")

        ma_legacy = self.target_root / "MA"
        ma_target = self.target_root / "Matematica Applicata"
        if ma_legacy.exists():
            ma_target.mkdir(parents=True, exist_ok=True)
            
            folder_map = {
                "Lezioni": ma_target / "Lezioni",
                "Appunti": ma_target / "Appunti",
                "Fogli di esercizi": ma_target / "Esercizi"
            }
            for sub_name, dest_dir in folder_map.items():
                src_sub = ma_legacy / sub_name
                if src_sub.exists():
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    for file_item in src_sub.iterdir():
                        if file_item.is_file() and not file_item.name.startswith("."):
                            dest_file = dest_dir / file_item.name
                            shutil.copy2(file_item, dest_file)
                            print(f"   [Migrazione] MA/{sub_name} -> Matematica Applicata/{dest_dir.name}: {file_item.name}")
            
            shutil.rmtree(ma_legacy)
            print("   [OK] Cartella 'MA' rimossa con successo.")

        ma_context = ma_target / "Context"
        if ma_context.exists():
            ma_lezioni = ma_target / "Lezioni"
            ma_lezioni.mkdir(parents=True, exist_ok=True)
            for item in ma_context.iterdir():
                if item.name.startswith(".") or not item.is_file():
                    continue
                dest = ma_lezioni / item.name
                if not dest.exists():
                    shutil.copy2(item, dest)
            shutil.rmtree(ma_context)
            print("   [OK] Cartella 'Matematica Applicata/Context' rimossa con successo.")

        ma_note = ma_target / "Note"
        if ma_note.exists():
            shutil.rmtree(ma_note)

        for rule in COURSE_RULES.values():
            course_dir = self.target_root / rule.target_name
            if not course_dir.exists():
                continue

            ctx_dir = course_dir / "Context"
            if ctx_dir.exists():
                shutil.rmtree(ctx_dir)
                print(f"   [OK] Cartella '{rule.target_name}/Context' rimossa con successo.")

            for item in list(course_dir.iterdir()):
                if item.is_file() and not item.name.startswith("."):
                    item.unlink()
                    print(f"   [PULIZIA] Rimosso file obsoleto dalla radice di {rule.target_name}: {item.name}")

    def _merge_exam_folder_if_needed(self, source_dir: Path, target_dir: Path) -> bool:
        is_exam_archive = (
            "prove d'esame" in source_dir.name.lower() or
            "prove_esame" in source_dir.name.lower() or
            "archivio prove d'esame" in source_dir.name.lower()
        )
        
        has_sub_exam = (source_dir / "Prove_esame").exists()

        if not is_exam_archive and not has_sub_exam:
            return False

        import pymupdf
        exam_src = source_dir / "Prove_esame" if has_sub_exam else source_dir
        merged_target = target_dir / "Prove d'esame.pdf"

        exam_pdfs = []
        for root, _, files in os.walk(exam_src):
            for f in sorted(files):
                if f.lower().endswith(".pdf") and not f.startswith("."):
                    exam_pdfs.append(Path(root) / f)

        if exam_pdfs:
            should_rebuild = True
            if merged_target.exists():
                newest_src = max((p.stat().st_mtime for p in exam_pdfs), default=0)
                if merged_target.stat().st_mtime >= newest_src and merged_target.stat().st_size > 0:
                    should_rebuild = False

            if should_rebuild:
                print(f"   [UNIONE ESAMI] Unione di {len(exam_pdfs)} PDF da '{exam_src.name}' in '{merged_target.name}'...")
                merged_doc = pymupdf.open()
                for p in exam_pdfs:
                    try:
                        doc = pymupdf.open(str(p))
                        try:
                            merged_doc.insert_pdf(doc)
                        except Exception:
                            pdf_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
                            doc_clean = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                            merged_doc.insert_pdf(doc_clean)
                            doc_clean.close()
                        doc.close()
                    except Exception as e:
                        print(f"      [ERRORE] Lettura {p.name}: {e}")
                target_dir.mkdir(parents=True, exist_ok=True)
                merged_doc.save(str(merged_target))
                merged_doc.close()
                print(f"   [OK] Creato: {target_dir.name}/Prove d'esame.pdf ({merged_target.stat().st_size / (1024*1024):.1f} MB)")

        if has_sub_exam:
            for item in source_dir.iterdir():
                if item.is_file() and item.suffix.lower() in ALLOWED_EXTENSIONS and not item.name.startswith("."):
                    dest = target_dir / item.name
                    if not dest.exists() or item.stat().st_size != dest.stat().st_size:
                        shutil.copy2(item, dest)
                        print(f"   [COPIA] {target_dir.name}/{item.name}")

        return True

    def sync_all_courses(self) -> Dict[str, List[Tuple[Path, Path]]]:
        self.migrate_legacy_folders()
        self.target_root.mkdir(parents=True, exist_ok=True)

        copied_summary = {}

        for source_course_name, rule in COURSE_RULES.items():
            source_course_dir = self.source_root / source_course_name
            if not source_course_dir.exists():
                print(f"[AVVISO] Cartella sorgente non trovata: {source_course_dir}")
                continue

            target_course_dir = self.target_root / rule.target_name
            target_course_dir.mkdir(parents=True, exist_ok=True)
            copied_summary[rule.target_name] = []

            print(f"\n[SYNC] Corso: {source_course_name} -> {rule.target_name}")

            for source_subfolder in sorted(source_course_dir.iterdir()):
                if not source_subfolder.is_dir() or source_subfolder.name.startswith("."):
                    continue

                sub_rule = rule.match_subfolder(source_subfolder.name)
                if sub_rule is None:
                    print(f"   [IGNORATA] Cartella: {source_subfolder.name}")
                    continue

                target_subfolder = target_course_dir / sub_rule.target_name
                target_subfolder.mkdir(parents=True, exist_ok=True)

                if self._merge_exam_folder_if_needed(source_subfolder, target_subfolder):
                    continue

                files_to_process = []
                for root_path, _, files in os.walk(source_subfolder):
                    for f in sorted(files):
                        if f.startswith("."):
                            continue
                        f_path = Path(root_path) / f
                        ext = f_path.suffix.lower()
                        if ext in ALLOWED_EXTENSIONS:
                            files_to_process.append(f_path)
                        else:
                            print(f"   [ESCLUSO] File non consentito (estensione '{ext}'): {f}")

                for idx, src_file in enumerate(files_to_process, 1):
                    if sub_rule.convert_to_markdown and src_file.suffix.lower() == ".pdf":
                        continue

                    if sub_rule.is_slide_folder:
                        dest_filename = format_slide_filename(src_file.name)
                    elif sub_rule.is_lesson_folder:
                        dest_filename = clean_lesson_filename(src_file.name, index_fallback=idx)
                    else:
                        dest_filename = src_file.name

                    dest_file_path = target_subfolder / dest_filename

                    should_copy = False
                    if not dest_file_path.exists():
                        should_copy = True
                    else:
                        if src_file.stat().st_size != dest_file_path.stat().st_size:
                            should_copy = True

                    if should_copy:
                        shutil.copy2(src_file, dest_file_path)
                        print(f"   [COPIA] {sub_rule.target_name}/{dest_filename}")
                        copied_summary[rule.target_name].append((src_file, dest_file_path))
                    else:
                        copied_summary[rule.target_name].append((src_file, dest_file_path))

        return copied_summary
