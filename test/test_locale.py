"""Tests for the (stateless, thread-safe) mediavocab locale system."""
import shutil
from pathlib import Path
from unittest.mock import patch

import mediavocab.locale as _locale_mod
from mediavocab.locale import voc_regex, voc_set
from mediavocab.taxonomy import ContentType
from mediavocab.text import classify_video


def test_voc_regex_movie_keywords_matches():
    rx = voc_regex("movie_keywords", lang="en-us")
    assert rx is not None
    assert rx.search("Full Movie 2024")
    assert rx.search("Watch this full film tonight")


def test_voc_regex_documentary_keywords_matches():
    rx = voc_regex("documentary_keywords", lang="en-us")
    assert rx is not None
    assert rx.search("A Documentary About Climate")
    assert rx.search("Watch this docuseries now")


def test_voc_regex_missing_file_returns_none(tmp_path):
    """A voc name that does not exist in any locale returns None."""
    with patch.object(_locale_mod, "_LOCALE_DIR", tmp_path):
        _locale_mod._load_voc.cache_clear()
        _locale_mod._voc_regex.cache_clear()
        _locale_mod._voc_set.cache_clear()
        result = voc_regex("nonexistent_file", lang="en-us")
    assert result is None


def test_fallback_unknown_lang_uses_en_us():
    rx = voc_regex("movie_keywords", lang="xx-xx")
    assert rx is not None
    assert rx.search("full movie")


def test_partial_locale_falls_back_for_missing_files(tmp_path):
    de_dir = tmp_path / "de-de"
    de_dir.mkdir()
    (de_dir / "movie_keywords.voc").write_text(
        "kompletter film\nganzer film\n", encoding="utf-8"
    )
    en_us_src = Path(_locale_mod._LOCALE_DIR) / "en-us"
    shutil.copytree(en_us_src, tmp_path / "en-us")

    with patch.object(_locale_mod, "_LOCALE_DIR", tmp_path):
        _locale_mod._load_voc.cache_clear()
        _locale_mod._voc_regex.cache_clear()
        _locale_mod._voc_set.cache_clear()

        rx_movie = voc_regex("movie_keywords", lang="de-de")
        assert rx_movie is not None
        assert rx_movie.search("kompletter Film")

        rx_doc = voc_regex("documentary_keywords", lang="de-de")
        assert rx_doc is not None
        assert rx_doc.search("documentary")


def test_non_english_locale_classify_video(tmp_path):
    de_dir = tmp_path / "de-de"
    de_dir.mkdir()
    (de_dir / "movie_keywords.voc").write_text(
        "kompletter film\nganzer film\n", encoding="utf-8"
    )
    en_us_src = Path(_locale_mod._LOCALE_DIR) / "en-us"
    shutil.copytree(en_us_src, tmp_path / "en-us")

    with patch.object(_locale_mod, "_LOCALE_DIR", tmp_path):
        _locale_mod._load_voc.cache_clear()
        _locale_mod._voc_regex.cache_clear()
        _locale_mod._voc_set.cache_clear()

        result = classify_video(
            "kompletter Film - Action 2024", length=7200, lang="de-de"
        )
        assert result == ContentType.MOVIE


def test_voc_set_returns_frozenset():
    result = voc_set("channel_sport_tags", lang="en-us")
    assert isinstance(result, frozenset)
    assert "football" in result


def test_classify_video_english_defaults():
    assert classify_video("Full Movie HD 2023", length=7200, lang="en-us") == ContentType.MOVIE
    assert classify_video("Avengers Official Trailer", lang="en-us") == ContentType.TRAILER
    assert classify_video("Nature Documentary Series", lang="en-us") == ContentType.DOCUMENTARY


def test_concurrent_lang_isolation():
    """Calls with different lang= are independently cached and never collide."""
    rx_en = voc_regex("movie_keywords", lang="en-us")
    rx_pt = voc_regex("movie_keywords", lang="pt-pt")
    assert rx_en is not None and rx_pt is not None
    assert voc_regex("movie_keywords", lang="en-us") is rx_en
