import sys
import os
import re
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import TARGET_ROOT, SOURCE_ROOT
from config.course_rules import strip_new_prefix, COURSE_RULES
from core.tracker import PipelineTracker, calculate_sha256
from core.base_sync import BaseSyncManager
from core.converter import (
    PDFToMarkdownConverter,
    ProcessConverter,
    extract_chronological_key
)
from core.downloader import run_dlub_download


def phase_download() -> bool:
    print("\n==================================================")
    print("[FASE 1] Verifica e Download Materiali")
    print("==================================================")

    # 1. Se SOURCE_ROOT è un repository Git (o dentro una directory git), prova a sincronizzare da remoto
    git_dir = SOURCE_ROOT / ".git"
    if git_dir.exists():
        print(f"Aggiornamento da server GitHub in {SOURCE_ROOT}...")
        try:
            res = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(SOURCE_ROOT),
                capture_output=True,
                text=True,
                timeout=60
            )
            if res.returncode == 0:
                print(f"[OK Git Pull] {res.stdout.strip()}")
                return True
            else:
                print(f"[Avviso Git Pull] {res.stderr.strip()}")
        except Exception as e:
            print(f"[Avviso Git] Impossibile eseguire git pull: {e}")

    # 2. Fallback su dlub locale se configurato
    return run_dlub_download()


def phase_base_sync() -> BaseSyncManager:
    print("\n==================================================")
    print("[FASE 2] Base Sync (Obsidian Vault e .ai/esercizi)")
    print("==================================================")
    sync_mgr = BaseSyncManager()
    sync_mgr.sync_all_courses()
    return sync_mgr


def phase_convert_student(tracker: PipelineTracker):
    print("\n==================================================")
    print("[FASE 3] Conversione OCR Studente (Descrizione Disegni, No Crop)")
    print("==================================================")
    converter = PDFToMarkdownConverter(tracker=tracker)

    conversion_targets = [
        (
            "Matematica Applicata",
            SOURCE_ROOT / "Matematica Applicata T" / "Schermate di lavagne",
            TARGET_ROOT / "Matematica Applicata"
        ),
        (
            "Fisica Generale",
            SOURCE_ROOT / "Fisica Generale T" / "Lezioni modulo 1",
            TARGET_ROOT / "Fisica Generale"
        )
    ]

    for course_name, src_dir, dest_dir in conversion_targets:
        if not src_dir.exists():
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[INFO Studente] Analisi lezioni per: {course_name}")

        existing_indices = []
        for md_file in dest_dir.glob("*.md"):
            clean_name = strip_new_prefix(md_file.name)
            m = re.match(r"^(\d{1,2})\s*[-_–—.]", clean_name)
            if m:
                existing_indices.append(int(m.group(1)))
        max_index = max(existing_indices, default=0)

        all_pdfs = [f for f in src_dir.glob("*.pdf") if not f.name.startswith(".")]
        unconverted_pdfs = [p for p in all_pdfs if not tracker.is_converted(calculate_sha256(p))]
        unconverted_pdfs = sorted(unconverted_pdfs, key=extract_chronological_key)

        for pdf_path in unconverted_pdfs:
            next_idx = max_index + 1
            max_index += 1
            forced_prefix = f"{next_idx:02d} - "
            print(f"   [PROGRESSIVO] Assegnazione automatica indice studente: {pdf_path.name} -> [{forced_prefix.strip()}]")
            try:
                converter.convert_pdf_to_md(
                    pdf_path=pdf_path,
                    output_dir=dest_dir,
                    forced_prefix=forced_prefix
                )
            except Exception as e:
                print(f"[ERRORE Studente] Conversione per {pdf_path.name}: {e}")


def phase_convert_ai_process(tracker: PipelineTracker):
    print("\n==================================================")
    print("[FASE 4] Conversione AI via Skill 'process' (.ai/lezioni/)")
    print("==================================================")
    proc_converter = ProcessConverter(tracker=tracker)

    # I target per l'AI includono le lezioni di tutti i corsi attivi
    ai_targets = [
        (
            "Matematica Applicata",
            SOURCE_ROOT / "Matematica Applicata T" / "Schermate di lavagne",
            TARGET_ROOT / "Matematica Applicata" / ".ai" / "lezioni"
        ),
        (
            "Fisica Generale",
            SOURCE_ROOT / "Fisica Generale T" / "Lezioni modulo 1",
            TARGET_ROOT / "Fisica Generale" / ".ai" / "lezioni"
        ),
        (
            "Fisica Generale",
            SOURCE_ROOT / "Fisica Generale T" / "Slides Lezioni",
            TARGET_ROOT / "Fisica Generale" / ".ai" / "lezioni"
        ),
        (
            "Basi di Dati",
            SOURCE_ROOT / "Basi di Dati T" / "Modulo 1 (materiale in aggiornamento)",
            TARGET_ROOT / "Basi di Dati" / ".ai" / "lezioni"
        ),
        (
            "Architetture dei Calcolatori",
            SOURCE_ROOT / "Architetture dei Calcolatori T" / "Mapping e decodifica",
            TARGET_ROOT / "Architetture dei Calcolatori" / ".ai" / "lezioni"
        ),
    ]

    for course_name, src_dir, ai_dest_dir in ai_targets:
        if not src_dir.exists():
            continue

        ai_dest_dir.mkdir(parents=True, exist_ok=True)
        all_pdfs = [f for f in src_dir.glob("*.pdf") if not f.name.startswith(".")]

        for pdf_path in sorted(all_pdfs):
            sha = calculate_sha256(pdf_path)
            if tracker.is_ai_converted(sha):
                continue

            # Se esiste già un markdown con lo stesso stem o stesso numero, non sovrascrivere i pregressi
            clean_stem = strip_new_prefix(pdf_path.stem)
            num_match = re.search(r"^(\d{1,2})", clean_stem)
            already_exists = False
            if (ai_dest_dir / f"{clean_stem}.md").exists():
                already_exists = True
            elif num_match:
                prefix = f"{int(num_match.group(1)):02d}"
                for existing_md in ai_dest_dir.glob("*.md"):
                    if existing_md.name.startswith(prefix):
                        already_exists = True
                        break

            if already_exists:
                tracker.record_ai_conversion(sha, str(pdf_path), str(ai_dest_dir / f"{clean_stem}.md"), clean_stem)
                continue

            try:
                proc_converter.convert_lecture_for_ai(
                    pdf_path=pdf_path,
                    output_dir=ai_dest_dir,
                    forced_title=clean_stem
                )
            except Exception as e:
                print(f"[ERRORE AI Process] {pdf_path.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline UniBo: Download -> Sync -> OCR Studente -> AI Process (.ai/lezioni)")
    parser.add_argument("--all", action="store_true", help="Esegui tutte le fasi in sequenza (default)")
    parser.add_argument("--download", action="store_true", help="Esegui solo la fase di download/pull")
    parser.add_argument("--sync-base", action="store_true", help="Esegui solo la sincronizzazione base (Obsidian + .ai/esercizi)")
    parser.add_argument("--convert", action="store_true", help="Esegui solo la conversione note studente (senza immagini)")
    parser.add_argument("--ai-process", action="store_true", help="Esegui solo la conversione AI via skill process in .ai/lezioni")
    parser.add_argument("--no-download", action="store_true", help="Esegui Sync + Convert saltando il download")

    args = parser.parse_args()
    tracker = PipelineTracker()

    run_all = args.all or not (args.download or args.sync_base or args.convert or args.ai_process or args.no_download)

    if args.download or run_all:
        phase_download()

    if args.sync_base or args.no_download or run_all:
        phase_base_sync()

    if args.convert or args.no_download or run_all:
        phase_convert_student(tracker)

    if args.ai_process or args.no_download or run_all:
        phase_convert_ai_process(tracker)

    print("\n==================================================")
    print("[OK] Pipeline completata con successo!")
    print("==================================================")


if __name__ == "__main__":
    main()
