import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Optional
from PIL import Image
import pypdfium2 as pdfium
from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY, NOTEBOOKLM_SOURCES_ROOT
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


def convert_handwritten_page(
    client: genai.Client,
    page_img: Image.Image,
    output_images_dir: Path,
    page_num: int,
    model_candidates: Optional[List[str]] = None,
    embed_images: bool = False
) -> str:
    if model_candidates is None:
        model_candidates = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash"]

    img_syntax_example = f"![Didascalia](images/p{page_num}_nome.png)" if embed_images else f"[Didascalia](images/p{page_num}_nome.png)"
    PROMPT_FILE = Path(__file__).resolve().parent / "prompt.txt"
    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        prompt = file.read().format(page=page_num, img_syntax=img_syntax_example)

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

                w, h = page_img.size
                for fig in data.get("figures", []):
                    box = fig.get("box_2d")
                    fname = fig.get("filename")
                    if box and fname and len(box) == 4:
                        ymin, xmin, ymax, xmax = box
                        y1 = max(0, min(h, int(ymin * h / 1000)))
                        x1 = max(0, min(w, int(xmin * w / 1000)))
                        y2 = max(0, min(h, int(ymax * h / 1000)))
                        x2 = max(0, min(w, int(xmax * w / 1000)))
                        if y2 > y1 and x2 > x1:
                            crop = page_img.crop((x1, y1, x2, y2))
                            target_file = output_images_dir / fname
                            crop.save(target_file)

                md = data.get("markdown", "")
                if not embed_images:
                    md = re.sub(r'!\[([^\]]+)\]\((images/[^\)]+)\)', r'[\1](\2)', md)
                return md
            except Exception as e:
                last_error = e
                wait_time = min(15, (2 ** attempt) + 1)
                time.sleep(wait_time)

    raise RuntimeError(f"Impossibile completare conversione OCR pagina {page_num}: {last_error}")


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

    def __init__(self, tracker: Optional[PipelineTracker] = None):
        self.tracker = tracker or PipelineTracker()
        self.client = get_gemini_client()

    def convert_pdf_to_md(
        self,
        pdf_path: Path,
        output_dir: Path,
        embed_images: bool = False,
        forced_prefix: Optional[str] = None
    ) -> Optional[Path]:
        pdf_path = Path(pdf_path).resolve()
        if not pdf_path.exists():
            print(f"[NON TROVATO] PDF non trovato: {pdf_path}")
            return None

        sha256 = calculate_sha256(pdf_path)
        if self.tracker.is_converted(sha256):
            print(f"[SKIP] Gia' convertito (SHA-256 cache): {pdf_path.name}")
            return None

        pdf_doc = pdfium.PdfDocument(str(pdf_path))
        total_pages = len(pdf_doc)
        if total_pages == 0:
            print(f"[AVVISO] PDF vuoto: {pdf_path.name}")
            return None

        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[OCR Gemini] Avvio conversione: {pdf_path.name} ({total_pages} pagine)")
        markdown_parts = []

        for idx in range(total_pages):
            page_num = idx + 1
            print(f"   [INFO] Trascrizione pagina {page_num}/{total_pages}...")
            page_img = extract_page_image(pdf_path, idx)
            md_page = convert_handwritten_page(
                client=self.client,
                page_img=page_img,
                output_images_dir=images_dir,
                page_num=page_num,
                embed_images=embed_images
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

        # Copia pulita per Fonti NotebookLM
        course_name = output_dir.name
        nblm_course_dir = NOTEBOOKLM_SOURCES_ROOT / course_name
        nblm_course_dir.mkdir(parents=True, exist_ok=True)
        nblm_md_path = nblm_course_dir / f"{clean_title}.md"
        with open(nblm_md_path, "w", encoding="utf-8") as f:
            f.write(content_text)

        self.tracker.record_conversion(
            sha256_hash=sha256,
            source_pdf=str(pdf_path),
            md_output=str(out_md_path),
            semantic_title=clean_title
        )

        print(f"[OK] Completata conversione: {out_md_path.name}")
        return out_md_path

    def register_existing_conversions(self, lezioni_dir: Path, source_pdf_dir: Optional[Path] = None):
        if not lezioni_dir.exists():
            return

        md_files = sorted(list(lezioni_dir.glob("*.md")))
        search_dirs = [lezioni_dir]
        if source_pdf_dir and source_pdf_dir.exists():
            search_dirs.append(source_pdf_dir)

        pdf_files = []
        for s_dir in search_dirs:
            pdf_files.extend(list(s_dir.glob("*.pdf")))

        for md in md_files:
            clean_md_stem = re.sub(r"^\s*\((?:NEW|New|new)\)\s*", "", md.stem).strip()
            num_match = re.search(r"^(\d{2})", clean_md_stem)
            prefix = num_match.group(1) if num_match else None
            for pdf in pdf_files:
                pdf_sha = calculate_sha256(pdf)
                if self.tracker.is_converted(pdf_sha):
                    continue
                matched = False
                has_date = bool(re.search(r"\d{1,2}\s*[-_/.]\s*\d{1,2}\s*[-_/.]\s*\d{2,4}", pdf.name))
                if not has_date:
                    pdf_num_match = re.search(r"^(\d{1,2})", pdf.name)
                    if prefix and pdf_num_match and f"{int(pdf_num_match.group(1)):02d}" == prefix:
                        matched = True
                if not matched and (pdf.stem.lower() in clean_md_stem.lower() or clean_md_stem.lower() in pdf.stem.lower()):
                    matched = True
                
                if matched:
                    self.tracker.record_conversion(
                        sha256_hash=pdf_sha,
                        source_pdf=str(pdf),
                        md_output=str(md),
                        semantic_title=md.stem
                    )
                    print(f"   [TRACKER] Registrato: {pdf.name} -> {md.name}")
