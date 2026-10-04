import sys
import re
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import TARGET_ROOT
from core.tracker import PipelineTracker
from core.base_sync import BaseSyncManager
from core.converter import PDFToMarkdownConverter
from core.notebooklm_sync import NotebookLMSyncManager
from core.downloader import run_dlub_download


def phase_download() -> bool:
    print("\n==================================================")
    print("[FASE 1] Download materiali tramite dlub")
    print("==================================================")
    return run_dlub_download()


def phase_base_sync() -> BaseSyncManager:
    print("\n==================================================")
    print("[FASE 2] Base Sync e Preparazione Obsidian Vault")
    print("==================================================")
    sync_mgr = BaseSyncManager()
    sync_mgr.sync_all_courses()
    return sync_mgr


from config.settings import SOURCE_ROOT, TARGET_ROOT


def phase_convert(tracker: PipelineTracker):
    print("\n==================================================")
    print("[FASE 3] Conversione OCR Gemini (LaTeX + Figure)")
    print("==================================================")
    converter = PDFToMarkdownConverter(tracker=tracker)

    conversion_targets = [
        (
            "Matematica Applicata",
            SOURCE_ROOT / "Matematica Applicata T" / "Schermate di lavagne",
            TARGET_ROOT / "Matematica Applicata" / "Lezioni"
        ),
        (
            "Fisica Generale",
            SOURCE_ROOT / "Fisica Generale T" / "Lezioni modulo 1",
            TARGET_ROOT / "Fisica Generale" / "Lezioni"
        )
    ]

    for course_name, src_dir, dest_dir in conversion_targets:
        if not src_dir.exists():
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[INFO] Analisi lezioni per: {course_name}")

        converter.register_existing_conversions(lezioni_dir=dest_dir, source_pdf_dir=src_dir)

        existing_indices = []
        for md_file in dest_dir.glob("*.md"):
            m = re.match(r"^(\d{1,2})\s*[-_–—.]", md_file.name)
            if m:
                existing_indices.append(int(m.group(1)))
        max_index = max(existing_indices, default=0)

        from core.converter import extract_chronological_key, calculate_sha256
        
        all_pdfs = [f for f in src_dir.glob("*.pdf") if not f.name.startswith(".")]
        unconverted_pdfs = [p for p in all_pdfs if not tracker.is_converted(calculate_sha256(p))]
        
        unconverted_pdfs = sorted(unconverted_pdfs, key=extract_chronological_key)

        for pdf_path in unconverted_pdfs:
            next_idx = max_index + 1
            max_index += 1
            forced_prefix = f"{next_idx:02d} - "
            print(f"   [PROGRESSIVO] Assegnazione automatica indice: {pdf_path.name} -> [{forced_prefix.strip()}]")
            try:
                converter.convert_pdf_to_md(
                    pdf_path=pdf_path,
                    output_dir=dest_dir,
                    forced_prefix=forced_prefix
                )
            except Exception as e:
                print(f"[ERRORE] Conversione per {pdf_path.name}: {e}")


def phase_push(tracker: PipelineTracker):
    print("\n==================================================")
    print("[FASE 4] Push e Sincronizzazione Google NotebookLM")
    print("==================================================")
    nblm_mgr = NotebookLMSyncManager(tracker=tracker)
    nblm_mgr.sync_all()


def main():
    parser = argparse.ArgumentParser(description="Pipeline UniBo: Download -> Sync -> OCR Convert -> Push NotebookLM")
    parser.add_argument("--all", action="store_true", help="Esegui tutte le fasi in sequenza (default)")
    parser.add_argument("--download", action="store_true", help="Esegui solo la fase di download")
    parser.add_argument("--sync-base", action="store_true", help="Esegui solo la sincronizzazione base verso Obsidian")
    parser.add_argument("--convert", action="store_true", help="Esegui solo la conversione OCR dei PDF")
    parser.add_argument("--push", action="store_true", help="Esegui solo il push su NotebookLM")
    parser.add_argument("--no-download", action="store_true", help="Esegui Sync + Convert + Push saltando il download")

    args = parser.parse_args()
    tracker = PipelineTracker()


    run_all = args.all or not (args.download or args.sync_base or args.convert or args.push or args.no_download)

    if args.download or run_all:
        phase_download()

    if args.sync_base or args.no_download or run_all:
        phase_base_sync()

    if args.convert or args.no_download or run_all:
        phase_convert(tracker)

    if args.push or args.no_download or run_all:
        phase_push(tracker)

    print("\n==================================================")
    print("[OK] Pipeline completata con successo!")
    print("==================================================")


if __name__ == "__main__":
    main()
