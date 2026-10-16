import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from config.settings import (
    SOURCE_ROOT,
    TARGET_ROOT,
    NOTEBOOKLM_SOURCES_ROOT,
    ALLOWED_EXTENSIONS,
    IGNORED_TARGET_COURSES
)
from config.course_rules import (
    COURSE_RULES,
    CourseRule,
    strip_new_prefix,
    add_new_prefix,
    format_architetture_filename,
    clean_lesson_filename,
    format_slide_filename
)


def unibo_file_exists(course_dir: Path, clean_filename: str) -> bool:
    """Verifica se il file è già presente nella cartella UniBo, con o senza prefisso (NEW)."""
    base = strip_new_prefix(clean_filename)
    return (course_dir / base).exists() or (course_dir / f"(NEW) {base}").exists()


class BaseSyncManager:

    def __init__(
        self,
        source_root: Path = SOURCE_ROOT,
        target_root: Path = TARGET_ROOT,
        notebooklm_root: Path = NOTEBOOKLM_SOURCES_ROOT
    ):
        self.source_root = Path(source_root).expanduser().resolve()
        self.target_root = Path(target_root).expanduser().resolve()
        self.notebooklm_root = Path(notebooklm_root).expanduser().resolve()

    def migrate_legacy_folders(self):
        print("Verifica ed eventuale migrazione note legacy e appiattimento UniBo...")
        self.target_root.mkdir(parents=True, exist_ok=True)
        self.notebooklm_root.mkdir(parents=True, exist_ok=True)

        # 1. Rimuove cartelle Context obsolete
        for rule in COURSE_RULES.values():
            course_dir = self.target_root / rule.target_name
            if not course_dir.exists():
                continue
            ctx_dir = course_dir / "Context"
            if ctx_dir.exists():
                shutil.rmtree(ctx_dir, ignore_errors=True)
                print(f"   [PULIZIA] Rimossa cartella '{rule.target_name}/Context'.")

        # 2. Appiattimento Matematica Applicata
        ma_dir = self.target_root / "Matematica Applicata"
        if ma_dir.exists():
            ma_lezioni = ma_dir / "Lezioni"
            if ma_lezioni.exists():
                ma_lez_images = ma_lezioni / "images"
                ma_target_images = ma_dir / "images"
                if ma_lez_images.exists():
                    ma_target_images.mkdir(parents=True, exist_ok=True)
                    for img in ma_lez_images.iterdir():
                        if img.is_file() and not img.name.startswith("."):
                            dest_img = ma_target_images / img.name
                            if not dest_img.exists():
                                shutil.move(str(img), str(dest_img))
                    shutil.rmtree(ma_lez_images, ignore_errors=True)

                for item in ma_lezioni.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        dest = ma_dir / item.name
                        if not dest.exists():
                            shutil.move(str(item), str(dest))
                shutil.rmtree(ma_lezioni, ignore_errors=True)
                print("   [OK] Appiattita cartella 'Matematica Applicata/Lezioni' nella radice del corso.")

            # Rimuove cartelle non previste per UniBo (vanno a Fonti NotebookLM)
            for sub in ["Esercizi", "Appunti"]:
                p = ma_dir / sub
                if p.exists():
                    shutil.rmtree(p, ignore_errors=True)
                    print(f"   [PULIZIA] Rimossa cartella 'Matematica Applicata/{sub}' da UniBo.")

        # 3. Appiattimento Fisica Generale
        fg_dir = self.target_root / "Fisica Generale"
        if fg_dir.exists():
            fg_lezioni = fg_dir / "Lezioni"
            if fg_lezioni.exists():
                fg_lez_images = fg_lezioni / "images"
                fg_target_images = fg_dir / "images"
                if fg_lez_images.exists():
                    fg_target_images.mkdir(parents=True, exist_ok=True)
                    for img in fg_lez_images.iterdir():
                        if img.is_file() and not img.name.startswith("."):
                            dest_img = fg_target_images / img.name
                            if not dest_img.exists():
                                shutil.move(str(img), str(dest_img))
                    shutil.rmtree(fg_lez_images, ignore_errors=True)

                for item in fg_lezioni.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        dest = fg_dir / item.name
                        if not dest.exists():
                            shutil.move(str(item), str(dest))
                shutil.rmtree(fg_lezioni, ignore_errors=True)
                print("   [OK] Appiattita cartella 'Fisica Generale/Lezioni' nella radice del corso.")

            fg_slides = fg_dir / "Slide Lezioni"
            if fg_slides.exists():
                for item in fg_slides.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        dest = fg_dir / item.name
                        if not dest.exists():
                            shutil.move(str(item), str(dest))
                shutil.rmtree(fg_slides, ignore_errors=True)
                print("   [OK] Appiattita cartella 'Fisica Generale/Slide Lezioni' nella radice del corso.")

            for sub in ["Informazioni Generali sul Corso", "Esercizi tutor", "Archivio prove d'esame"]:
                p = fg_dir / sub
                if p.exists():
                    shutil.rmtree(p, ignore_errors=True)
                    print(f"   [PULIZIA] Rimossa cartella 'Fisica Generale/{sub}' da UniBo.")

        # 4. Appiattimento Basi di Dati
        bd_dir = self.target_root / "Basi di Dati"
        if bd_dir.exists():
            bd_lezioni = bd_dir / "Lezioni"
            if bd_lezioni.exists():
                for item in bd_lezioni.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        dest = bd_dir / item.name
                        if not dest.exists():
                            shutil.move(str(item), str(dest))
                shutil.rmtree(bd_lezioni, ignore_errors=True)
                print("   [OK] Appiattita cartella 'Basi di Dati/Lezioni' nella radice del corso.")

            bd_intro = bd_dir / "Introduzione"
            if bd_intro.exists():
                shutil.rmtree(bd_intro, ignore_errors=True)
                print("   [PULIZIA] Rimossa cartella 'Basi di Dati/Introduzione' da UniBo.")

        # 5. Appiattimento Architetture dei Calcolatori
        ac_dir = self.target_root / "Architetture dei Calcolatori"
        if ac_dir.exists():
            for sub in ["Ripasso", "Introduzione e esami", "Mapping e decodifica", "Linguaggio macchina"]:
                p = ac_dir / sub
                if p.exists():
                    for item in p.iterdir():
                        if item.is_file() and not item.name.startswith("."):
                            # Formatta con pattern Architetture
                            formatted_name = format_architetture_filename(item.name)
                            dest = ac_dir / formatted_name
                            if not dest.exists():
                                shutil.move(str(item), str(dest))
                    shutil.rmtree(p, ignore_errors=True)
                    print(f"   [OK] Appiattita cartella 'Architetture dei Calcolatori/{sub}' nella radice del corso.")

        # 6. Sincronizzazione iniziale file Markdown verso Fonti NotebookLM
        for cname in ["Matematica Applicata", "Fisica Generale"]:
            c_dir = self.target_root / cname
            nblm_c_dir = self.notebooklm_root / cname
            if c_dir.exists():
                nblm_c_dir.mkdir(parents=True, exist_ok=True)
                for md_file in c_dir.glob("*.md"):
                    clean_md_name = strip_new_prefix(md_file.name)
                    dest_nblm = nblm_c_dir / clean_md_name
                    if not dest_nblm.exists() or md_file.stat().st_size != dest_nblm.stat().st_size:
                        shutil.copy2(md_file, dest_nblm)

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
        target_dir.mkdir(parents=True, exist_ok=True)
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
                merged_doc.save(str(merged_target))
                merged_doc.close()
                print(f"   [OK] Creato: {target_dir.name}/Prove d'esame.pdf ({merged_target.stat().st_size / (1024*1024):.1f} MB)")

        return True

    def sync_all_courses(self) -> Dict[str, List[Tuple[Path, Path]]]:
        self.migrate_legacy_folders()
        self.target_root.mkdir(parents=True, exist_ok=True)
        self.notebooklm_root.mkdir(parents=True, exist_ok=True)

        copied_summary = {}

        for source_course_name, rule in COURSE_RULES.items():
            source_course_dir = self.source_root / source_course_name
            if not source_course_dir.exists():
                print(f"[AVVISO] Cartella sorgente non trovata: {source_course_dir}")
                continue

            target_course_dir = self.target_root / rule.target_name
            target_course_dir.mkdir(parents=True, exist_ok=True)

            notebooklm_course_dir = self.notebooklm_root / rule.target_name
            notebooklm_course_dir.mkdir(parents=True, exist_ok=True)

            copied_summary[rule.target_name] = []
            print(f"\n[SYNC] Corso: {source_course_name} -> {rule.target_name}")

            for source_subfolder in sorted(source_course_dir.iterdir()):
                if not source_subfolder.is_dir() or source_subfolder.name.startswith("."):
                    continue

                sub_rule = rule.match_subfolder(source_subfolder.name)
                if sub_rule is None:
                    continue

                # Verifica unione esami
                is_exam = self._merge_exam_folder_if_needed(source_subfolder, notebooklm_course_dir)
                if rule.target_name == "Architetture dei Calcolatori":
                    self._merge_exam_folder_if_needed(source_subfolder, target_course_dir)

                has_sub_exam = (source_subfolder / "Prove_esame").exists()
                if is_exam and not has_sub_exam:
                    continue

                files_to_process = []
                for root_path, _, files in os.walk(source_subfolder):
                    # Salta le cartelle di singoli compiti d'esame già uniti in 'Prove d'esame.pdf'
                    root_name_lower = Path(root_path).name.lower()
                    if "prove_esame" in root_name_lower or "archivio prove d'esame" in root_name_lower:
                        continue
                    for f in sorted(files):
                        if f.startswith("."):
                            continue
                        f_path = Path(root_path) / f
                        ext = f_path.suffix.lower()
                        if ext in ALLOWED_EXTENSIONS:
                            files_to_process.append(f_path)

                for idx, src_file in enumerate(files_to_process, 1):
                    # Se il PDF deve essere convertito in Markdown (es. lavagne MA, lezioni modulo 1 FG),
                    # non copiamo il PDF raw (il markdown verrà generato da OCR)
                    if sub_rule and sub_rule.convert_to_markdown and src_file.suffix.lower() == ".pdf":
                        continue

                    # 1. Determina il nome base pulito (per NotebookLM e base UniBo)
                    if rule.target_name == "Architetture dei Calcolatori":
                        clean_filename = strip_new_prefix(format_architetture_filename(src_file.name))
                    elif sub_rule and sub_rule.is_slide_folder:
                        clean_filename = strip_new_prefix(format_slide_filename(src_file.name))
                    elif sub_rule and sub_rule.is_lesson_folder:
                        clean_filename = strip_new_prefix(clean_lesson_filename(src_file.name, index_fallback=idx))
                    else:
                        clean_filename = strip_new_prefix(src_file.name)

                    # 2. Copia verso NOTEBOOKLM_SOURCES_ROOT (tutte le fonti per l'AI, senza prefisso NEW)
                    nblm_dest = notebooklm_course_dir / clean_filename
                    should_copy_nblm = not nblm_dest.exists() or src_file.stat().st_size != nblm_dest.stat().st_size
                    if should_copy_nblm:
                        shutil.copy2(src_file, nblm_dest)
                        print(f"   [FONTE NOTEBOOKLM] {clean_filename}")

                    # 3. Determina se il file appartiene ad UniBo (solo lezioni / materiale studente)
                    belongs_to_unibo = False
                    if rule.target_name == "Architetture dei Calcolatori":
                        belongs_to_unibo = True
                    elif rule.target_name == "Basi di Dati":
                        belongs_to_unibo = (sub_rule is not None and sub_rule.is_lesson_folder)
                    elif rule.target_name == "Fisica Generale":
                        belongs_to_unibo = (sub_rule is not None and sub_rule.is_slide_folder)
                    elif rule.target_name == "Matematica Applicata":
                        belongs_to_unibo = False

                    if not belongs_to_unibo:
                        continue

                    # 4. Copia verso UniBo (radice del corso, con (NEW) se nuovo)
                    already_in_unibo = unibo_file_exists(target_course_dir, clean_filename)

                    if already_in_unibo:
                        # Se esiste già (sia come "nome" sia come "(NEW) nome"), non sovrascrive il nome
                        # Aggiorna il contenuto solo se la dimensione è cambiata
                        existing_target = target_course_dir / clean_filename
                        if not existing_target.exists():
                            existing_target = target_course_dir / f"(NEW) {clean_filename}"
                        if src_file.stat().st_size != existing_target.stat().st_size:
                            shutil.copy2(src_file, existing_target)
                            print(f"   [AGGIORNATO UNIBO] {existing_target.name}")
                        copied_summary[rule.target_name].append((src_file, existing_target))
                    else:
                        # File completamente nuovo in UniBo: prefisso (NEW)
                        unibo_dest = target_course_dir / f"(NEW) {clean_filename}"
                        shutil.copy2(src_file, unibo_dest)
                        print(f"   [NUOVO UNIBO] {unibo_dest.name}")
                        copied_summary[rule.target_name].append((src_file, unibo_dest))

        return copied_summary
