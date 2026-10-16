from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import re
from pathlib import Path


@dataclass
class SubfolderRule:
    source_name_pattern: str
    target_name: str
    is_lesson_folder: bool = False
    is_exercise_folder: bool = False
    convert_to_markdown: bool = False
    is_slide_folder: bool = False


@dataclass
class CourseRule:
    source_name: str
    target_name: str
    allow_all_subfolders: bool = True
    subfolder_rules: List[SubfolderRule] = field(default_factory=list)

    def match_subfolder(self, folder_name: str) -> Optional[SubfolderRule]:
        for rule in self.subfolder_rules:
            if re.search(rule.source_name_pattern, folder_name, re.IGNORECASE):
                return rule
        if self.allow_all_subfolders:
            return SubfolderRule(
                source_name_pattern=".*",
                target_name=folder_name,
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=False,
                is_slide_folder=False
            )
        return None


COURSE_RULES: Dict[str, CourseRule] = {
    "Architetture dei Calcolatori T": CourseRule(
        source_name="Architetture dei Calcolatori T",
        target_name="Architetture dei Calcolatori",
        allow_all_subfolders=True,
        subfolder_rules=[
            SubfolderRule(
                source_name_pattern=r"^Introduzione.*",
                target_name="Introduzione",
                is_lesson_folder=True,
                is_exercise_folder=False,
            ),
            SubfolderRule(
                source_name_pattern=r"^Complementi.*",
                target_name="Ripasso",
                is_lesson_folder=True,
                is_exercise_folder=False,
            ),
            SubfolderRule(
                source_name_pattern=r"^Mapping.*",
                target_name="Mapping e decodifica",
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=False
            ),
            SubfolderRule(
                source_name_pattern=r"^Linguaggio.*",
                target_name="Linguaggio macchina",
                is_lesson_folder=True,
                is_exercise_folder=False,
            ),
            SubfolderRule(
                source_name_pattern=r"^Interruzioni.*",
                target_name="Interruzioni",
                is_lesson_folder=True,
                is_exercise_folder=False,
            ),
        ]
    ),
    "Basi di Dati T": CourseRule(
        source_name="Basi di Dati T",
        target_name="Basi di Dati",
        allow_all_subfolders=False,
        subfolder_rules=[
            SubfolderRule(
                source_name_pattern=r"^Modulo\s*1.*",
                target_name="Lezioni",
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=False
            ),
            SubfolderRule(
                source_name_pattern=r"^Modulo\s*2.*",
                target_name="Laboratorio",
                is_lesson_folder=False,
                is_exercise_folder=True,
                convert_to_markdown=False
            ),
            SubfolderRule(
                source_name_pattern=r"^Esercizi.*",
                target_name="Esercizi",
                is_lesson_folder=False,
                is_exercise_folder=True,
                convert_to_markdown=False
            ),
            SubfolderRule(
                source_name_pattern=r"^Introduzione\s*al\s*corso.*",
                target_name="Introduzione",
                is_lesson_folder=False,
                is_exercise_folder=False
            ),
        ]
    ),
    "Matematica Applicata T": CourseRule(
        source_name="Matematica Applicata T",
        target_name="Matematica Applicata",
        allow_all_subfolders=False,
        subfolder_rules=[
            SubfolderRule(
                source_name_pattern=r"^Schermate\s*di\s*lavagne.*",
                target_name="Lezioni",
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=True
            ),
            SubfolderRule(
                source_name_pattern=r"^Appunti.*",
                target_name="Appunti",
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=False
            ),
            SubfolderRule(
                source_name_pattern=r"^Fogli\s*di\s*esercizi.*",
                target_name="Esercizi",
                is_lesson_folder=False,
                is_exercise_folder=True,
                convert_to_markdown=False
            ),
        ]
    ),
    "Fisica Generale T": CourseRule(
        source_name="Fisica Generale T",
        target_name="Fisica Generale",
        allow_all_subfolders=True,
        subfolder_rules=[
            SubfolderRule(
                source_name_pattern=r"^Lezioni\s*modulo\s*1.*",
                target_name="Lezioni",
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=True
            ),
            SubfolderRule(
                source_name_pattern=r"^Slides?\s*Lezioni.*",
                target_name="Slide Lezioni",
                is_lesson_folder=True,
                is_exercise_folder=False,
                convert_to_markdown=False,
                is_slide_folder=True
            ),
            SubfolderRule(
                source_name_pattern=r"^Esercizi\s*tutor.*",
                target_name="Esercizi tutor",
                is_lesson_folder=False,
                is_exercise_folder=True,
                convert_to_markdown=False
            ),
            SubfolderRule(
                source_name_pattern=r"^Archivio\s*prove\s*d'esame.*",
                target_name="Prove d'esame",
                is_lesson_folder=False,
                is_exercise_folder=True,
                convert_to_markdown=False
            ),
        ]
    ),
}


def strip_new_prefix(filename: str) -> str:
    """Rimuove il prefisso (NEW), (New) o (new) dal nome del file se presente."""
    return re.sub(r"^\s*\((?:NEW|New|new)\)\s*", "", filename).strip()


def add_new_prefix(filename: str) -> str:
    """Aggiunge il prefisso '(NEW) ' al nome del file se non già presente."""
    clean = strip_new_prefix(filename)
    return f"(NEW) {clean}"


def format_architetture_filename(filename: str) -> str:
    """
    Formatta i file di Architetture:
    sostituisce il primo '_' tra numero e titolo con ' - ', e tutti i successivi '_' con spazi.
    Esempio: '03_Linguaggio_macchina.pdf' -> '03 - Linguaggio macchina.pdf'
    """
    ext = Path(filename).suffix
    stem = Path(filename).stem
    has_new = bool(re.match(r"^\s*\((?:NEW|New|new)\)\s*", stem))
    clean_stem = strip_new_prefix(stem)

    match = re.match(r"^(\d+(?:\.\d+)?)\s*_(.*)$", clean_stem)
    if match:
        num_part = match.group(1)
        rest_part = match.group(2)
        title_clean = rest_part.replace("_", " ").strip()
        title_clean = re.sub(r"\s+", " ", title_clean)
        if num_part.isdigit() and len(num_part) == 1:
            num_part = f"0{num_part}"
        formatted = f"{num_part} - {title_clean}{ext}"
    else:
        formatted = f"{clean_stem}{ext}"

    if has_new:
        return f"(NEW) {formatted}"
    return formatted


def format_slide_filename(original_name: str) -> str:
    stem = Path(original_name).stem
    ext = Path(original_name).suffix
    clean_stem = strip_new_prefix(stem)
    clean_stem = re.sub(r"^[sS]\s*", "", clean_stem).strip()
    clean_stem = re.sub(r"^\((\d+)\)", r"\1", clean_stem).strip()

    match = re.match(r"^(\d+(?:\.\d+)?)\s*[-_–—.]?\s*(.*)$", clean_stem)
    if match:
        num_part = match.group(1)
        title_part = match.group(2).strip().replace("_", " ")
        if num_part.isdigit() and len(num_part) == 1:
            num_part = f"0{num_part}"
        if title_part:
            clean_title = title_part.capitalize()
            return f"S{num_part} - {clean_title}{ext}"
        else:
            return f"S{num_part}{ext}"

    return f"{stem.capitalize()}{ext}"


def clean_lesson_filename(original_name: str, index_fallback: Optional[int] = None) -> str:
    stem = Path(original_name).stem
    ext = Path(original_name).suffix
    stem = strip_new_prefix(stem)

    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem).strip()

    match_num_start = re.match(r"^(\d+(?:\.\d+)?)\s*[-_–—.]?\s*(.*)$", stem)
    if match_num_start:
        num_part = match_num_start.group(1)
        title_part = match_num_start.group(2).strip()
        if num_part.isdigit() and len(num_part) == 1:
            num_part = f"0{num_part}"
        if title_part:
            return f"{num_part} - {title_part}{ext}"
        else:
            return f"{num_part}{ext}"

    match_lez = re.match(r"^Lezione\s+(\d+)\s*(.*)$", stem, re.IGNORECASE)
    if match_lez:
        num_part = int(match_lez.group(1))
        title_part = match_lez.group(2).strip()
        num_str = f"{num_part:02d}"
        if title_part:
            return f"{num_str} - Lezione {num_part} {title_part}{ext}".replace("  ", " ")
        else:
            return f"{num_str} - Lezione {num_part}{ext}"

    if index_fallback is not None:
        return f"{index_fallback:02d} - {stem}{ext}"

    return f"{stem}{ext}"
