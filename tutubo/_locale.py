"""Locale loader for tutubo classification keywords.

.voc files contain one plain phrase per line. Blank lines and lines starting
with '#' are ignored. The loader builds word-boundary alternation regexes and
frozensets from these files.

Fallback chain: exact match → language-only → en-us.

Usage:
    from tutubo._locale import voc_regex, voc_set, set_lang, get_lang
    import os; os.environ["TUTUBO_LANG"] = "es-es"   # or call set_lang()
"""
import os
import re
from functools import lru_cache
from pathlib import Path

_LOCALE_DIR = Path(__file__).parent / "locale"
_active_lang: str = os.environ.get("TUTUBO_LANG", "en-us").lower()


def set_lang(lang: str) -> None:
    """Set the active classification language (BCP-47, e.g. 'es-es').
    Clears all cached patterns so the next classify_video() call rebuilds them.
    """
    global _active_lang
    _active_lang = lang.lower()
    _load_voc.cache_clear()
    _voc_regex.cache_clear()
    _voc_set.cache_clear()


def get_lang() -> str:
    """Return the active classification language code."""
    return _active_lang


def _fallback_chain(lang: str) -> list[str]:
    chain = [lang]
    if "-" in lang:
        chain.append(lang.split("-")[0])
    if "en-us" not in chain:
        chain.append("en-us")
    return chain


@lru_cache(maxsize=512)
def _load_voc(name: str, lang: str) -> tuple[str, ...]:
    """Load phrases from a .voc file with fallback chain. Cached per (name, lang)."""
    for candidate in _fallback_chain(lang):
        path = _LOCALE_DIR / candidate / f"{name}.voc"
        if path.exists():
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            return tuple(
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            )
    return ()


@lru_cache(maxsize=512)
def _voc_regex(name: str, lang: str) -> re.Pattern | None:
    phrases = _load_voc(name, lang)
    if not phrases:
        return None
    sorted_phrases = sorted(phrases, key=len, reverse=True)
    alternation = "|".join(re.escape(p) for p in sorted_phrases)
    return re.compile(rf"\b(?:{alternation})\b", re.IGNORECASE)


@lru_cache(maxsize=512)
def _voc_set(name: str, lang: str) -> frozenset[str]:
    return frozenset(p.lower() for p in _load_voc(name, lang))


def voc_regex(name: str) -> re.Pattern | None:
    """Return a compiled regex for the given .voc file in the active language."""
    return _voc_regex(name, _active_lang)


def voc_set(name: str) -> frozenset[str]:
    """Return a frozenset of lowercase phrases from the given .voc file."""
    return _voc_set(name, _active_lang)
