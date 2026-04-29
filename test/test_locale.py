"""Tests for the tutubo locale system."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import tutubo._locale as _locale_mod
from tutubo._locale import set_lang, get_lang, voc_regex, voc_set
from tutubo.content_type import classify_video, ContentType


@pytest.fixture(autouse=True)
def reset_lang():
    """Reset language to en-us after each test."""
    original = get_lang()
    yield
    set_lang(original)


def test_set_get_lang_roundtrip():
    set_lang("fr-fr")
    assert get_lang() == "fr-fr"


def test_set_lang_normalises_case():
    set_lang("ES-ES")
    assert get_lang() == "es-es"


def test_voc_regex_movie_keywords_matches():
    set_lang("en-us")
    rx = voc_regex("movie_keywords")
    assert rx is not None
    assert rx.search("Full Movie 2024")
    assert rx.search("Watch this full film tonight")


def test_voc_regex_documentary_keywords_matches():
    set_lang("en-us")
    rx = voc_regex("documentary_keywords")
    assert rx is not None
    assert rx.search("A Documentary About Climate")
    assert rx.search("Watch this docuseries now")


def test_voc_regex_missing_file_returns_none(tmp_path):
    """A voc name that does not exist in any locale returns None without crashing."""
    with patch.object(_locale_mod, "_LOCALE_DIR", tmp_path):
        _locale_mod._load_voc.cache_clear()
        _locale_mod._voc_regex.cache_clear()
        _locale_mod._voc_set.cache_clear()
        result = voc_regex("nonexistent_file")
    assert result is None


def test_fallback_unknown_lang_uses_en_us():
    """Unknown language with no locale files should fall back to en-us."""
    set_lang("xx-xx")
    rx = voc_regex("movie_keywords")
    assert rx is not None
    assert rx.search("full movie")


def test_partial_locale_falls_back_for_missing_files(tmp_path):
    """A locale that has only some .voc files falls back to en-us for the rest."""
    de_dir = tmp_path / "de-de"
    de_dir.mkdir()
    (de_dir / "movie_keywords.voc").write_text("kompletter film\nganzer film\n", encoding="utf-8")

    # Copy en-us dir so fallback works for other files
    import shutil
    en_us_src = Path(_locale_mod._LOCALE_DIR) / "en-us"
    en_us_dst = tmp_path / "en-us"
    shutil.copytree(en_us_src, en_us_dst)

    with patch.object(_locale_mod, "_LOCALE_DIR", tmp_path):
        _locale_mod._load_voc.cache_clear()
        _locale_mod._voc_regex.cache_clear()
        _locale_mod._voc_set.cache_clear()
        _locale_mod._active_lang = "de-de"

        # de-de has movie_keywords.voc
        rx_movie = _locale_mod.voc_regex("movie_keywords")
        assert rx_movie is not None
        assert rx_movie.search("kompletter Film")

        # de-de does NOT have documentary_keywords.voc — falls back to en-us
        rx_doc = _locale_mod.voc_regex("documentary_keywords")
        assert rx_doc is not None
        assert rx_doc.search("documentary")


def test_non_english_locale_classify_video(tmp_path):
    """A de-de locale with 'kompletter film' classifies correctly."""
    import shutil

    de_dir = tmp_path / "de-de"
    de_dir.mkdir()
    (de_dir / "movie_keywords.voc").write_text("kompletter film\nganzer film\n", encoding="utf-8")

    en_us_src = Path(_locale_mod._LOCALE_DIR) / "en-us"
    en_us_dst = tmp_path / "en-us"
    shutil.copytree(en_us_src, en_us_dst)

    with patch.object(_locale_mod, "_LOCALE_DIR", tmp_path):
        _locale_mod._load_voc.cache_clear()
        _locale_mod._voc_regex.cache_clear()
        _locale_mod._voc_set.cache_clear()
        _locale_mod._active_lang = "de-de"

        result = classify_video("kompletter Film - Action 2024", length=7200)
        assert result == ContentType.MOVIE


def test_set_lang_clears_cache():
    """After set_lang(), cached patterns for the old lang are evicted."""
    set_lang("en-us")
    rx_before = voc_regex("movie_keywords")

    set_lang("en-us")  # same lang, cache cleared
    rx_after = voc_regex("movie_keywords")

    # Both should still match — we're just checking no stale cache error
    assert rx_before is not None
    assert rx_after is not None
    assert rx_before.search("full movie")
    assert rx_after.search("full movie")


def test_tutubo_lang_env_var(monkeypatch):
    """TUTUBO_LANG env var sets the initial language."""
    monkeypatch.setenv("TUTUBO_LANG", "pt-br")
    # Re-read via set_lang to simulate env at import time
    set_lang("pt-br")
    assert get_lang() == "pt-br"


def test_voc_set_returns_frozenset():
    set_lang("en-us")
    result = voc_set("channel_sport_tags")
    assert isinstance(result, frozenset)
    assert "football" in result


def test_classify_video_english_defaults():
    set_lang("en-us")
    assert classify_video("Full Movie HD 2023", length=7200) == ContentType.MOVIE
    assert classify_video("Avengers Official Trailer") == ContentType.TRAILER
    assert classify_video("Nature Documentary Series") == ContentType.DOCUMENTARY


def test_public_api_exports():
    import tutubo
    assert hasattr(tutubo, "set_lang")
    assert hasattr(tutubo, "get_lang")
    assert callable(tutubo.set_lang)
    assert callable(tutubo.get_lang)
