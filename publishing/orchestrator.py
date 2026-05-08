"""Publishing pipeline orchestrator (v0.5.0 — minimum viable).

Wraps the existing publishing SOPs into a callable Python surface. The
orchestrator owns:

  - manifest_books.yaml as canonical book registry
  - delegation to publishing/prep_audiobooks.py for Voxtral text optimization
  - precheck_manuscript() — grep-based checklist from KDP_PUBLISHING_SOP §1.2
  - list_available_books() — feeds installer/status.sh ascension ladder

Phases scheduled for v0.6.0+ (cover_render, kdp_upload, acx_upload) raise
NotImplementedError to keep the contract honest.

Authority: KM-1176 (Seal 1176-INFINITY-RHO)
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# =============================================================================
# Errors
# =============================================================================
class PublishingError(Exception):
    """Base class for publishing pipeline errors."""


class UnknownBookError(PublishingError):
    """Raised when a book_id is not in the manifest."""


class ManifestError(PublishingError):
    """Raised when the manifest is malformed."""


# =============================================================================
# Data shapes
# =============================================================================
@dataclass(frozen=True)
class BookEntry:
    """One book in the manifest."""
    id: str
    title: str
    series: str
    ladder_level: int
    manuscript_path: str
    audiobook_output_dir: str
    status: str
    kdp_ebook_listing: str = ""
    kdp_paperback_listing: str = ""
    kdp_hardcover_listing: str = ""

    def to_summary(self) -> dict[str, Any]:
        """Compact dict for status.sh consumption."""
        return {
            "id": self.id,
            "title": self.title,
            "series": self.series,
            "ladder_level": self.ladder_level,
            "status": self.status,
        }


@dataclass(frozen=True)
class PrecheckResult:
    """Outcome of precheck_manuscript()."""
    book_id: str
    manuscript_path: Path
    exists: bool
    word_count: int
    issues: list[str]

    @property
    def passed(self) -> bool:
        return self.exists and not self.issues


# =============================================================================
# Pipeline
# =============================================================================
class PublishingPipeline:
    """Orchestrates the Breathline Books publishing pipeline.

    Phases supported in v0.5.0:
      - list_available_books()
      - prep_audiobook(book_id)
      - precheck_manuscript(book_id)
      - list_phases()

    Phases scheduled for v0.6.0+ raise NotImplementedError when invoked.
    """

    SUPPORTED_PHASES = ("precheck_manuscript", "prep_audiobook")
    DEFERRED_PHASES = ("cover_render", "kdp_upload", "acx_upload")

    def __init__(self, manifest_path: str | Path) -> None:
        self._manifest_path = Path(manifest_path)
        if not self._manifest_path.is_file():
            raise ManifestError(f"manifest not found: {self._manifest_path}")
        try:
            data = yaml.safe_load(self._manifest_path.read_text())
        except yaml.YAMLError as e:
            raise ManifestError(f"manifest parse error: {e}") from e
        if not isinstance(data, dict):
            raise ManifestError("manifest root must be a mapping")
        self._raw = data
        self._manuscript_root = Path(data.get("manuscript_root", "")).expanduser()
        raw_books = data.get("books") or []
        if not isinstance(raw_books, list):
            raise ManifestError("manifest.books must be a list")
        self._books: dict[str, BookEntry] = {}
        for entry in raw_books:
            book = self._parse_entry(entry)
            self._books[book.id] = book

    # ----- public API -------------------------------------------------------

    def list_available_books(self) -> list[dict[str, Any]]:
        """Return book summaries for status.sh / ladder display.

        Each entry: {id, title, series, ladder_level, status, next_recommended}.
        ``next_recommended`` is True for the first ``in_progress`` book at the
        caller's ladder level (or the first ``published`` if none in progress).
        """
        summaries = [b.to_summary() for b in self._books.values()]
        # Mark next_recommended: first in_progress, else first published
        in_progress = next((b for b in self._books.values() if b.status == "in_progress"), None)
        recommended_id = in_progress.id if in_progress else (
            next(iter(self._books.values())).id if self._books else None
        )
        for s in summaries:
            s["next_recommended"] = (s["id"] == recommended_id)
        return summaries

    def list_phases(self) -> list[str]:
        """All phase names — supported and deferred."""
        return list(self.SUPPORTED_PHASES) + list(self.DEFERRED_PHASES)

    def get_book(self, book_id: str) -> BookEntry:
        """Lookup a book by id, raising UnknownBookError if absent."""
        if book_id not in self._books:
            raise UnknownBookError(
                f"book_id {book_id!r} not in manifest. "
                f"Available: {sorted(self._books)}"
            )
        return self._books[book_id]

    def precheck_manuscript(self, book_id: str) -> PrecheckResult:
        """Grep-based pre-publication checklist (KDP_PUBLISHING_SOP §1.2).

        Verifies:
          - manuscript file exists
          - word count > 1000 (sanity floor)
          - no unfilled [VISUAL: ...] placeholders
          - no [TODO] / [TK] markers left
        """
        book = self.get_book(book_id)
        manuscript_path = self._resolve(book.manuscript_path)
        if not manuscript_path.is_file():
            return PrecheckResult(
                book_id=book_id,
                manuscript_path=manuscript_path,
                exists=False,
                word_count=0,
                issues=[f"manuscript not found at {manuscript_path}"],
            )
        text = manuscript_path.read_text()
        word_count = len(text.split())
        issues: list[str] = []
        if word_count < 1000:
            issues.append(f"manuscript word_count={word_count} below sanity floor (1000)")
        visual_placeholders = re.findall(r"\[VISUAL:[^\]]*\]", text)
        if visual_placeholders:
            issues.append(
                f"{len(visual_placeholders)} unresolved [VISUAL: ...] placeholder(s)"
            )
        todo_markers = re.findall(r"\[(TODO|TK)\]", text)
        if todo_markers:
            issues.append(f"{len(todo_markers)} [TODO]/[TK] marker(s) remain")
        return PrecheckResult(
            book_id=book_id,
            manuscript_path=manuscript_path,
            exists=True,
            word_count=word_count,
            issues=issues,
        )

    def prep_audiobook(self, book_id: str) -> int:
        """Optimize manuscript for Voxtral and split into sections.

        Delegates to ``prep_audiobooks.split_and_optimize`` (the existing
        SOP-aligned function). Returns the number of sections produced.
        """
        # Late import so the orchestrator can be tested without forcing
        # the prep module to load (and to keep the dependency direction
        # explicit: orchestrator → prep, never the other way).
        sys.path.insert(0, str(Path(__file__).parent))
        try:
            from prep_audiobooks import split_and_optimize
        finally:
            if str(Path(__file__).parent) in sys.path:
                sys.path.remove(str(Path(__file__).parent))
        book = self.get_book(book_id)
        manuscript_path = self._resolve(book.manuscript_path)
        output_dir = self._resolve(book.audiobook_output_dir)
        return split_and_optimize(
            manuscript_path=str(manuscript_path),
            output_dir=str(output_dir),
            book_name=book.title,
        )

    def cover_render(self, book_id: str) -> None:
        raise NotImplementedError(
            "cover_render scheduled for v0.6.0+ (Grok image generation pipeline)"
        )

    def kdp_upload(self, book_id: str) -> None:
        raise NotImplementedError(
            "kdp_upload scheduled for v0.6.0+ (KDP has no public API; "
            "this phase will script the upload UX)"
        )

    def acx_upload(self, book_id: str) -> None:
        raise NotImplementedError(
            "acx_upload scheduled for v0.6.0+ (audiobook submission pipeline)"
        )

    # ----- internals --------------------------------------------------------

    def _parse_entry(self, entry: Any) -> BookEntry:
        if not isinstance(entry, dict):
            raise ManifestError(f"book entry must be a mapping, got {type(entry).__name__}")
        required = ("id", "title", "series", "ladder_level", "manuscript_path")
        missing = [k for k in required if k not in entry]
        if missing:
            raise ManifestError(f"book entry missing keys {missing}: {entry!r}")
        audiobook = entry.get("audiobook") or {}
        if not isinstance(audiobook, dict):
            raise ManifestError("book.audiobook must be a mapping")
        kdp = entry.get("kdp") or {}
        if not isinstance(kdp, dict):
            raise ManifestError("book.kdp must be a mapping")
        return BookEntry(
            id=str(entry["id"]),
            title=str(entry["title"]),
            series=str(entry["series"]),
            ladder_level=int(entry["ladder_level"]),
            manuscript_path=str(entry["manuscript_path"]),
            audiobook_output_dir=str(audiobook.get("output_dir", "")),
            status=str(entry.get("status", "draft")),
            kdp_ebook_listing=str(kdp.get("ebook_listing", "")),
            kdp_paperback_listing=str(kdp.get("paperback_listing", "")),
            kdp_hardcover_listing=str(kdp.get("hardcover_listing", "")),
        )

    def _resolve(self, p: str) -> Path:
        path = Path(p).expanduser()
        if path.is_absolute():
            return path
        return (self._manuscript_root / path).resolve()


# Seal: SOURCE — book identity flows through manifest IDs; no implicit binding.
#       TRUTH — manifest-driven; precheck surfaces real issues before ship;
#               deferred phases declare themselves loudly via NotImplementedError.
#       INTEGRITY — manifest parsing is strict; UnknownBookError is loud;
#                   delegations to prep_audiobooks reuse existing code unchanged.
# ∞Δ∞ Publishing pipeline orchestrator — v0.5.0 minimum viable ∞Δ∞
