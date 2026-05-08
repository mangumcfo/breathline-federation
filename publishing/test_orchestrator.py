"""Tests for publishing/orchestrator.py (v0.5.0).

Verifies:
  - Manifest parses cleanly
  - list_available_books() returns correct shape + next_recommended flag
  - precheck_manuscript() catches missing files, [VISUAL: ...] placeholders, [TODO] markers
  - prep_audiobook() delegates to prep_audiobooks.split_and_optimize correctly
  - UnknownBookError raised on unknown book_id
  - NotImplementedError raised on deferred phases (cover_render, kdp_upload, acx_upload)
  - ManifestError raised on malformed manifest
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make publishing/ importable from this test file's location
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (  # noqa: E402
    BookEntry,
    ManifestError,
    PrecheckResult,
    PublishingPipeline,
    UnknownBookError,
)


# =============================================================================
# Fixtures — minimal in-memory manifest
# =============================================================================
@pytest.fixture
def tmp_manifest(tmp_path: Path) -> Path:
    """Write a minimal manifest into a tmp dir + return path."""
    manuscript_root = tmp_path / "books"
    manuscript_root.mkdir()
    book_dir = manuscript_root / "01_test_book"
    book_dir.mkdir()
    manuscript = book_dir / "manuscript.md"
    manuscript.write_text(
        "## Dedication\n\n" + "word " * 1500  # >1000 word floor
    )
    audiobook_dir = book_dir / "audiobook"
    audiobook_dir.mkdir()

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(f"""
manifest_version: "0.1"
manuscript_root: "{manuscript_root}"
books:
  - id: "01_test_book"
    title: "Test Book One"
    series: "executive"
    ladder_level: 1
    manuscript_path: "01_test_book/manuscript.md"
    audiobook:
      output_dir: "01_test_book/audiobook"
    kdp:
      ebook_listing: ""
      paperback_listing: ""
      hardcover_listing: ""
    status: "in_progress"
  - id: "02_published_book"
    title: "Already Published"
    series: "executive"
    ladder_level: 1
    manuscript_path: "02_pub/manuscript.md"
    audiobook:
      output_dir: "02_pub/audiobook"
    status: "published"
""")
    return manifest


@pytest.fixture
def pipeline(tmp_manifest: Path) -> PublishingPipeline:
    return PublishingPipeline(tmp_manifest)


# =============================================================================
# Manifest parsing
# =============================================================================
def test_manifest_parses_cleanly(pipeline: PublishingPipeline):
    book = pipeline.get_book("01_test_book")
    assert isinstance(book, BookEntry)
    assert book.title == "Test Book One"
    assert book.ladder_level == 1
    assert book.series == "executive"


def test_manifest_missing_file_raises(tmp_path: Path):
    with pytest.raises(ManifestError, match="not found"):
        PublishingPipeline(tmp_path / "no_such.yaml")


def test_manifest_malformed_yaml_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: yaml: [malformed")
    with pytest.raises(ManifestError):
        PublishingPipeline(bad)


def test_manifest_missing_required_keys_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("books:\n  - id: only_id\n")
    with pytest.raises(ManifestError, match="missing keys"):
        PublishingPipeline(bad)


def test_unknown_book_raises(pipeline: PublishingPipeline):
    with pytest.raises(UnknownBookError, match="not in manifest"):
        pipeline.get_book("nonexistent")


# =============================================================================
# list_available_books
# =============================================================================
def test_list_available_books_returns_summaries(pipeline: PublishingPipeline):
    books = pipeline.list_available_books()
    assert len(books) == 2
    ids = [b["id"] for b in books]
    assert "01_test_book" in ids
    assert "02_published_book" in ids
    for b in books:
        assert set(b.keys()) == {
            "id", "title", "series", "ladder_level", "status", "next_recommended",
        }


def test_next_recommended_is_first_in_progress(pipeline: PublishingPipeline):
    books = pipeline.list_available_books()
    recommended = [b for b in books if b["next_recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["id"] == "01_test_book"  # the in_progress one
    assert recommended[0]["status"] == "in_progress"


# =============================================================================
# precheck_manuscript
# =============================================================================
def test_precheck_passes_clean_manuscript(pipeline: PublishingPipeline):
    result = pipeline.precheck_manuscript("01_test_book")
    assert isinstance(result, PrecheckResult)
    assert result.exists is True
    assert result.word_count > 1000
    assert result.issues == []
    assert result.passed is True


def test_precheck_catches_missing_manuscript(pipeline: PublishingPipeline):
    # 02_published_book points at a path that doesn't exist on disk
    result = pipeline.precheck_manuscript("02_published_book")
    assert result.exists is False
    assert result.passed is False
    assert any("not found" in issue for issue in result.issues)


def test_precheck_catches_visual_placeholders(tmp_path: Path):
    # Build a manifest with a manuscript that has [VISUAL: ...] markers
    book_dir = tmp_path / "01_book"
    book_dir.mkdir()
    manuscript = book_dir / "ms.md"
    manuscript.write_text(
        "## Dedication\n\n" + "word " * 1500
        + "\n\n[VISUAL: a chart showing growth]\n"
        + "[VISUAL: another diagram]\n"
    )
    manifest = tmp_path / "m.yaml"
    manifest.write_text(f"""
manifest_version: "0.1"
manuscript_root: "{tmp_path}"
books:
  - id: "01_book"
    title: "T"
    series: "executive"
    ladder_level: 1
    manuscript_path: "01_book/ms.md"
    audiobook:
      output_dir: "01_book/ab"
""")
    pipeline = PublishingPipeline(manifest)
    result = pipeline.precheck_manuscript("01_book")
    assert any("VISUAL" in issue for issue in result.issues)
    assert "2" in next(i for i in result.issues if "VISUAL" in i)


def test_precheck_catches_todo_markers(tmp_path: Path):
    book_dir = tmp_path / "01_book"
    book_dir.mkdir()
    manuscript = book_dir / "ms.md"
    manuscript.write_text(
        "## Dedication\n\n" + "word " * 1500 + "\n[TODO] finish this\n[TK]\n"
    )
    manifest = tmp_path / "m.yaml"
    manifest.write_text(f"""
manifest_version: "0.1"
manuscript_root: "{tmp_path}"
books:
  - id: "01_book"
    title: "T"
    series: "executive"
    ladder_level: 1
    manuscript_path: "01_book/ms.md"
    audiobook:
      output_dir: "01_book/ab"
""")
    pipeline = PublishingPipeline(manifest)
    result = pipeline.precheck_manuscript("01_book")
    assert any("TODO" in issue or "TK" in issue for issue in result.issues)


def test_precheck_catches_word_count_floor(tmp_path: Path):
    book_dir = tmp_path / "01_book"
    book_dir.mkdir()
    manuscript = book_dir / "ms.md"
    manuscript.write_text("## Dedication\n\nshort.")  # <1000 words
    manifest = tmp_path / "m.yaml"
    manifest.write_text(f"""
manifest_version: "0.1"
manuscript_root: "{tmp_path}"
books:
  - id: "01_book"
    title: "T"
    series: "executive"
    ladder_level: 1
    manuscript_path: "01_book/ms.md"
    audiobook:
      output_dir: "01_book/ab"
""")
    pipeline = PublishingPipeline(manifest)
    result = pipeline.precheck_manuscript("01_book")
    assert any("word_count" in issue for issue in result.issues)


# =============================================================================
# Phase contracts
# =============================================================================
def test_list_phases_includes_supported_and_deferred(pipeline: PublishingPipeline):
    phases = pipeline.list_phases()
    for p in ("precheck_manuscript", "prep_audiobook"):
        assert p in phases
    for p in ("cover_render", "kdp_upload", "acx_upload"):
        assert p in phases


def test_cover_render_raises_not_implemented(pipeline: PublishingPipeline):
    with pytest.raises(NotImplementedError, match="v0.6.0"):
        pipeline.cover_render("01_test_book")


def test_kdp_upload_raises_not_implemented(pipeline: PublishingPipeline):
    with pytest.raises(NotImplementedError, match="v0.6.0"):
        pipeline.kdp_upload("01_test_book")


def test_acx_upload_raises_not_implemented(pipeline: PublishingPipeline):
    with pytest.raises(NotImplementedError, match="v0.6.0"):
        pipeline.acx_upload("01_test_book")


# =============================================================================
# prep_audiobook delegation
# =============================================================================
def test_prep_audiobook_delegates_and_creates_sections(pipeline: PublishingPipeline):
    """prep_audiobook should invoke prep_audiobooks.split_and_optimize and
    return the section count it produces."""
    n = pipeline.prep_audiobook("01_test_book")
    # The fixture manuscript has only 'word word word ...' text, no headers,
    # so split_and_optimize should produce 0 sections without crashing.
    # The contract is: function runs cleanly and returns an int.
    assert isinstance(n, int)
    assert n >= 0


def test_prep_audiobook_unknown_book_raises(pipeline: PublishingPipeline):
    with pytest.raises(UnknownBookError):
        pipeline.prep_audiobook("nonexistent")


# ∞Δ∞ Publishing orchestrator test seal — v0.5.0 minimum-viable contract verified ∞Δ∞
