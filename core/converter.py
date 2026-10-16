import os
import sys
import json
import time
import re
import subprocess
from pathlib import Path
from typing import List, Optional
from PIL import Image
import pypdfium2 as pdfium
from google import genai
from google.genai import types

from config.settings import (
    GEMINI_API_KEY,
    PYTHON_BIN,
    PROCESS_GATE_SCRIPT,
)
from core.tracker import PipelineTracker, calculate_sha256


def get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY non trovata nelle variabili d'ambiente o in settings.py.")
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60000))


def extract_page_image(pdf_path: Path, page_idx: int, scale: float = 2.0) -> Image.Image:
    pdf = pdfium.PdfDocument(str(pdf_path))
    if page_idx >= len(pdf):
        raise IndexError(f"Pagina {page_idx + 1} non presente nel PDF (totale: {len(pdf)})")
    page = pdf[page_idx]
    return page.render(scale=scale).to_pil()


def convert_handwritten_page_student(
    client: genai.Client,
    page_img: Image.Image,
    page_num: int,
    model_candidates: Optional[List[str]] = None
) -> str:
    """Trascrive la pagina per lo studente: formule in LaTeX e disegni descritti testualmente senza ritagliare immagini."""
    if model_candidates is None:
        model_candidates = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash"]

    PROMPT_FILE = Path(__file__).resolve().parent / "prompt.txt"
    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        prompt = file.read().format(page=page_num)

    last_error = None
    for model_name in model_candidates:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=[page_img, prompt],
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.1
                    }
                )
                data = json.loads(resp.text)
                return data.get("markdown", "")
            except Exception as e:
                last_error = e
                time.sleep(min(10, (2 ** attempt) + 1))

    raise RuntimeError(f"Impossibile completare conversione OCR pagina {page_num}: {last_error}")


def convert_page_process_skill(
    client: genai.Client,
    page_img: Image.Image,
    page_num: int,
    total_pages: int,
    model_candidates: Optional[List[str]] = None
) -> str:
    """Trascrive la pagina secondo lo standard della skill 'process' v2.0 per l'AI."""
    if model_candidates is None:
        model_candidates = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash"]

    pad = 3 if total_pages > 99 else 2
    prompt = f"""Sei l'elaboratore della skill 'process' (v2.0) di Google Antigravity.
Converti l'immagine della pagina {page_num} di {total_pages} in Markdown semantico ad altissima densità informativa per l'AI al minor costo di token possibile, con affidabilità al primo colpo (First-Time-Right).

REGOLE TASSATIVE:
1. Intestazione Pagina: Inizia la trascrizione esattamente con:
   ## P{page_num:0{pad}d} - [Titolo/Argomento sintetico]
2. Zero Caratteri PUA:
   - È severamente vietato inserire caratteri Unicode Private Use Area (U+E000–U+F8FF).
   - Usa notazione LaTeX scientifica rigorosa per qualsiasi simbolo matematico o greco ($...$ inline, $$...$$ a blocco).
   - Bilancia sempre i delimitatori LaTeX.
3. Rappresentazione Grafica (Mermaid o ASCII):
   - Converti schemi logici, circuiti, cronogrammi, FSM o architetture di memoria in Mermaid valido (```mermaid ... ```) o diagrammi ASCII compatti.
4. Risoluzione dei Quesiti Aperti:
   - Se la pagina pone una domanda aperta o retorica, riportala e fornisci la RISOLUZIONE TECNICA esatta subito sotto.
5. Zero Convenevoli:
   - Nessun saluto, preambolo decorativo o introduzione prolissa. Solo contenuto tecnico puro ad alta densità.

Restituisci SOLO il testo Markdown della pagina {page_num}."""

    last_error = None
    for model_name in model_candidates:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=[page_img, prompt],
                    config={"temperature": 0.1}
                )
                text = resp.text.strip()
                if text:
                    return text
            except Exception as e:
                last_error = e
                time.sleep(min(10, (2 ** attempt) + 1))

    raise RuntimeError(f"Impossibile completare trascrizione process pagina {page_num}: {last_error}")


def extract_chronological_key(file_path: Path) -> tuple:
    stem = file_path.stem
    m1 = re.search(r'(\d{4})(\d{2})(\d{2})', stem)
    if m1:
        return (int(m1.group(1)), int(m1.group(2)), int(m1.group(3)), stem)

    m2 = re.search(r'(\d{1,2})\s*[-_/\.]\s*(\d{1,2})\s*[-_/\.]\s*(\d{2,4})', stem)
    if m2:
        day = int(m2.group(1))
        month = int(m2.group(2))
        yr_str = m2.group(3)
        year = int(yr_str) if len(yr_str) == 4 else 2000 + int(yr_str)
        return (year, month, day, stem)

    try:
        mtime = file_path.stat().st_mtime
        return (2099, 12, int(mtime % 30) + 1, stem)
    except Exception:
        return (2099, 12, 31, stem)


def generate_semantic_title(
    client: genai.Client,
    first_page_md: str,
    current_stem: str,
    forced_prefix: Optional[str] = None
) -> str:
    if forced_prefix:
        num_prefix = forced_prefix.strip() + " " if not forced_prefix.endswith(" ") else forced_prefix
    else:
        num_match = re.search(r"(\d{2})", current_stem)
        num_prefix = f"{num_match.group(1)} - " if num_match else ""

    prompt = f"""Dato il seguente testo trascritto dalla prima pagina di una lezione universitaria, fornisci un titolo breve, descrittivo e coerente (massimo 5-7 parole, in lingua italiana, senza caratteri speciali proibiti per nomi di file come / \\ : * ? " < > |):

TESTO:
{first_page_md[:2000]}

Rispondi con SOLO il titolo conciso."""

    for model_name in ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash"]:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.2}
            )
            title = resp.text.strip().replace("\n", "").replace("/", "-").replace('"', "").replace(":", " -")
            title = re.sub(r"[\\*?<>|]", "", title)
            title = re.sub(r"^\d+\s*[-_.]?\s*", "", title).strip()
            if len(title) > 60:
                title = title[:60].strip()
            if title:
                return f"{num_prefix}{title}".strip()
        except Exception:
            continue

    clean_stem = re.sub(r"^\s*\((?:NEW|New|new)\)\s*", "", current_stem).strip()
    return f"{num_prefix}{clean_stem}".strip()


class PDFToMarkdownConverter:
    """Converte le lezioni manoscritte per lo studente (in root corso con (NEW), senza ritagliare immagini)."""

    def __init__(self, tracker: Optional[PipelineTracker] = None):
        self.tracker = tracker or PipelineTracker()
        self.client = get_gemini_client()

    def convert_pdf_to_md(
        self,
        pdf_path: Path,
        output_dir: Path,
        forced_prefix: Optional[str] = None
    ) -> Optional[Path]:
        pdf_path = Path(pdf_path).resolve()
        if not pdf_path.exists():
            print(f"[NON TROVATO] PDF non trovato: {pdf_path}")
            return None

        sha256 = calculate_sha256(pdf_path)
        if self.tracker.is_converted(sha256):
            print(f"[SKIP] Gia' convertito per lo studente: {pdf_path.name}")
            return None

        pdf_doc = pdfium.PdfDocument(str(pdf_path))
        total_pages = len(pdf_doc)
        if total_pages == 0:
            print(f"[AVVISO] PDF vuoto: {pdf_path.name}")
            return None

        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[OCR Studente] Avvio conversione: {pdf_path.name} ({total_pages} pagine)")
        markdown_parts = []

        for idx in range(total_pages):
            page_num = idx + 1
            print(f"   [INFO] Trascrizione pagina {page_num}/{total_pages}...")
            page_img = extract_page_image(pdf_path, idx)
            md_page = convert_handwritten_page_student(
                client=self.client,
                page_img=page_img,
                page_num=page_num
            )
            markdown_parts.append(md_page)

        first_page_text = markdown_parts[0] if markdown_parts else ""
        semantic_title = generate_semantic_title(
            self.client,
            first_page_text,
            pdf_path.stem,
            forced_prefix=forced_prefix
        )

        clean_title = re.sub(r"^\s*\((?:NEW|New|new)\)\s*", "", semantic_title).strip()
        out_md_path = output_dir / f"(NEW) {clean_title}.md"
        content_text = "\n\n---\n\n".join(markdown_parts) + "\n"
        with open(out_md_path, "w", encoding="utf-8") as f:
            f.write(content_text)

        self.tracker.record_conversion(
            sha256_hash=sha256,
            source_pdf=str(pdf_path),
            md_output=str(out_md_path),
            semantic_title=clean_title
        )

        print(f"[OK Studente] Completata conversione: {out_md_path.name}")
        return out_md_path


class ProcessConverter:
    """Converte le lezioni per l'AI in .ai/lezioni/ usando la skill 'process' di Antigravity."""

    def __init__(self, tracker: Optional[PipelineTracker] = None):
        self.tracker = tracker or PipelineTracker()
        self.client = get_gemini_client()

    def convert_lecture_for_ai(
        self,
        pdf_path: Path,
        output_dir: Path,
        forced_title: Optional[str] = None
    ) -> Optional[Path]:
        pdf_path = Path(pdf_path).resolve()
        if not pdf_path.exists():
            return None

        sha256 = calculate_sha256(pdf_path)
        if self.tracker.is_ai_converted(sha256):
            return None

        pdf_doc = pdfium.PdfDocument(str(pdf_path))
        total_pages = len(pdf_doc)
        if total_pages == 0:
            return None

        output_dir.mkdir(parents=True, exist_ok=True)

        # Se esiste già un file per questa lezione in .ai/lezioni/, non sovrascrivere
        stem_clean = forced_title or pdf_path.stem
        stem_clean = re.sub(r"^\s*\((?:NEW|New|new)\)\s*", "", stem_clean).strip()
        out_md_path = output_dir / f"{stem_clean}.md"
        if out_md_path.exists():
            print(f"[SKIP AI] Lezione già presente in .ai/lezioni/: {out_md_path.name}")
            self.tracker.record_ai_conversion(sha256, str(pdf_path), str(out_md_path), stem_clean)
            return out_md_path

        print(f"\n[Skill Process AI] Conversione: {pdf_path.name} ({total_pages} pagine) -> {out_md_path.name}")
        markdown_pages = []

        for idx in range(total_pages):
            page_num = idx + 1
            print(f"   [Process] Elaborazione pagina {page_num}/{total_pages}...")
            page_img = extract_page_image(pdf_path, idx)
            md_page = convert_page_process_skill(
                client=self.client,
                page_img=page_img,
                page_num=page_num,
                total_pages=total_pages
            )
            markdown_pages.append(md_page)

        full_md_content = f"# {stem_clean}\n\n" + "\n\n---\n\n".join(markdown_pages) + "\n"
        with open(out_md_path, "w", encoding="utf-8") as f:
            f.write(full_md_content)

        # Quality Gate Automatico con verify_and_sanitize.py
        if PROCESS_GATE_SCRIPT.exists():
            try:
                cmd = [
                    PYTHON_BIN,
                    str(PROCESS_GATE_SCRIPT),
                    str(out_md_path),
                    "--pdf",
                    str(pdf_path),
                    "--fix"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if res.returncode == 0:
                    print(f"   [Quality Gate OK] Sanitizzazione e verifica superate: {out_md_path.name}")
                else:
                    print(f"   [Quality Gate Avviso] Output: {res.stderr or res.stdout}")
            except Exception as e:
                print(f"   [Quality Gate Errore]: {e}")

        self.tracker.record_ai_conversion(
            sha256_hash=sha256,
            source_pdf=str(pdf_path),
            md_output=str(out_md_path),
            title=stem_clean
        )
        print(f"[OK AI] Salvata lezione per l'AI: {out_md_path.name}")
        return out_md_path
