from .settings import (
    SOURCE_ROOT,
    TARGET_ROOT,
    ALLOWED_EXTENSIONS,
    IGNORED_TARGET_COURSES,
    TRACKER_FILE,
    STAGING_DIR,
    PYTHON_BIN,
    DLUB_BIN,
    GEMINI_API_KEY,
    PROCESS_SKILL_DIR,
    PROCESS_GATE_SCRIPT,
    AI_LEZIONI_SUBDIR,
    AI_ESERCIZI_SUBDIR,
)
from .course_rules import COURSE_RULES, CourseRule, SubfolderRule, clean_lesson_filename

__all__ = [
    "SOURCE_ROOT",
    "TARGET_ROOT",
    "ALLOWED_EXTENSIONS",
    "IGNORED_TARGET_COURSES",
    "TRACKER_FILE",
    "STAGING_DIR",
    "PYTHON_BIN",
    "DLUB_BIN",
    "GEMINI_API_KEY",
    "PROCESS_SKILL_DIR",
    "PROCESS_GATE_SCRIPT",
    "AI_LEZIONI_SUBDIR",
    "AI_ESERCIZI_SUBDIR",
    "COURSE_RULES",
    "CourseRule",
    "SubfolderRule",
    "clean_lesson_filename"
]
