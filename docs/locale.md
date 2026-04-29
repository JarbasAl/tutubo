# Locale System

`tutubo/_locale.py`

Classification keywords are stored in plain `.voc` files, one phrase per line, organised by language. This lets tutubo classify content in languages other than English without changing Python code.

---

## Directory layout

```
tutubo/locale/
    en-us/
        movie_keywords.voc
        documentary_keywords.voc
        music_video_keywords.voc
        channel_movie_tags.voc
        channel_news_tags.voc
        ... (one .voc file per keyword category)
        tags/
            horror.voc
            sci-fi.voc
            full-album.voc
            ... (one .voc file per auto-tag label)
    es/
        movie_keywords.voc      # shared Spanish base
        documentary_keywords.voc
        ...
        tags/
            ...
    es-es/
        live_news_keywords.voc  # Spain-specific overrides only
    es-mx/
        ...                     # Mexico-specific overrides only
    fr-fr/
        ...
    it-it/
        ...
    nl-nl/
        ...
    pt/
        ...                     # shared Portuguese base
    pt-pt/
        ...                     # sparse overrides
    pt-br/
        ...                     # sparse overrides
```

A variant directory (e.g. `es-es`) only needs files that differ from the shared base (`es`). Everything else falls back through the chain.

---

## .voc file format

A `.voc` file contains one phrase per line.

- Blank lines are ignored.
- Lines starting with `#` are comments and are ignored.
- Leading and trailing whitespace is stripped.
- Phrases are matched case-insensitively.
- Multi-word phrases are supported: `full movie` is a single entry.

Example — `en-us/movie_keywords.voc`:

```
# full-length feature film indicators
full movie
full film
full length
full length movie
full length film
complete film
complete movie
```

Example — `es/movie_keywords.voc`:

```
película completa
pelicula completa
largometraje
película en español
```

---

## Fallback chain

When a `.voc` file is requested for a given language, the loader walks this chain and returns the first file it finds:

1. Exact locale match — e.g. `es-es`
2. Language-only code — e.g. `es`
3. `en-us`

This means:

- `es-es` and `es-mx` automatically inherit all `es/` files they do not override.
- Any unsupported locale falls back to English.
- You can add a minimal variant directory with only the files that need to differ.

Example: requesting `movie_keywords` with lang `es-es`:

```
es-es/movie_keywords.voc   → not found
es/movie_keywords.voc      → found, use this
```

Example: requesting `movie_keywords` with lang `de-de` (not supported):

```
de-de/movie_keywords.voc   → not found
de/movie_keywords.voc      → not found
en-us/movie_keywords.voc   → found, use this
```

---

## Public API

### `set_lang(lang: str) -> None`

Set the active classification language. Accepts BCP-47 codes, case-insensitive. Clears all cached patterns so the next `classify_video()` call rebuilds them from the new language files.

```python
import tutubo
tutubo.set_lang("fr-fr")
```

### `get_lang() -> str`

Return the currently active language code (lowercased).

```python
tutubo.get_lang()   # "fr-fr"
```

### `TUTUBO_LANG` environment variable

Set before starting the Python process. Equivalent to calling `set_lang()` at import time.

```bash
TUTUBO_LANG=it-it python my_script.py
```

If both `TUTUBO_LANG` and `set_lang()` are used, `set_lang()` wins — it overwrites the value initialised from the environment variable.

---

## How `voc_regex()` builds patterns

`voc_regex(name)` returns a compiled `re.Pattern` or `None` if the file is empty.

The pattern is built as a word-boundary alternation:

1. Load all phrases from the `.voc` file via the fallback chain.
2. Sort phrases longest-first. This ensures `full length movie` is tried before `full movie` before `movie`, preventing short phrases from shadowing longer ones.
3. Escape each phrase with `re.escape()`.
4. Join with `|` and wrap in `\b(?:...)\b`.
5. Compile with `re.IGNORECASE`.

Example — two-phrase file:

```
full movie
film complet
```

Produces:

```python
re.compile(r'\b(?:film\ complet|full\ movie)\b', re.IGNORECASE)
```

Results are cached per `(name, lang)` pair. Calling `set_lang()` clears the cache.

---

## How `voc_set()` works

`voc_set(name)` returns a `frozenset` of lowercased phrases from the `.voc` file.

This is used for channel-tag intersection checks. Channel tags from YouTube are arbitrary strings; the intersection test (`channel_tags & voc_set("channel_movie_tags")`) is fast and exact.

```python
from tutubo._locale import voc_set

movie_tags = voc_set("channel_movie_tags")
channel_tags = {"full movie", "bollywood films", "comedy"}
if channel_tags & movie_tags:
    # channel is a movie channel
```

---

## Structural patterns that stay in Python

Some patterns are not expressed in `.voc` files because they are numeric, structural, or language-universal:

| Pattern | Reason |
|---|---|
| `S01E02`, `Season N Episode N` | Standardised production codes; identical across all languages |
| `Top \d+` | Numeric; the word "top" plus a number needs no translation |
| Duration gates (`length < 62`, `length >= 3600`, etc.) | Numeric thresholds; not linguistic |
| `is_live`, `is_upcoming`, `is_podcast` flag checks | Boolean signals from YouTube data; not text patterns |

---

## The `tags/` subdirectory

Auto-tags (returned by `extract_tags()`) are also keyword-driven. Their `.voc` files live in `locale/<lang>/tags/`. The mapping from label name to file stem is defined in `_TAG_MANIFEST` in `tutubo/content_type.py`.

Example entries from `_TAG_MANIFEST`:

```python
("horror",     "tags/horror"),
("full-album", "tags/full-album"),
("narrated",   "tags/narrated"),
```

So `voc_regex("tags/horror")` loads `locale/<lang>/tags/horror.voc`. The label returned by `extract_tags()` is the first element of each tuple, regardless of language.

---

## Channel tag `.voc` files

Files named `channel_*.voc` (e.g. `channel_news_tags.voc`, `channel_music_tags.voc`) list phrases that, when found in a channel's keyword tags, boost that channel's content into a specific `ContentType`.

These files should include multilingual signals. Channel operators tag their channels in whatever language they operate in — a French news channel may use `"actualités"` or `"journal télévisé"` regardless of what language the viewer has set. Including those terms in `en-us/channel_news_tags.voc` (or the appropriate language file) ensures they are recognised.

The `TUTUBO_LANG` setting does affect which `channel_*.voc` file is loaded, so you can have both a broad `en-us` set and a language-specific supplement.

---

## Supported languages

| Code | Notes |
|---|---|
| `en-us` | Default; all `.voc` files present |
| `fr-fr` | French |
| `it-it` | Italian |
| `nl-nl` | Dutch |
| `es` | Spanish base; shared by `es-es` and `es-mx` |
| `es-es` | Spain Spanish — sparse overrides |
| `es-mx` | Mexican Spanish — sparse overrides |
| `pt` | Portuguese base; shared by `pt-pt` and `pt-br` |
| `pt-pt` | European Portuguese — sparse overrides |
| `pt-br` | Brazilian Portuguese — sparse overrides |

---

## Adding a new language

### Step 1 — Create the directory

```bash
mkdir tutubo/locale/de-de
mkdir tutubo/locale/de-de/tags
```

If the language has regional variants (e.g. `de-at`, `de-ch`), create `de/` as the shared base and add the variant directories with only the files that differ.

### Step 2 — Translate `.voc` files

Copy from `en-us/` and translate phrase by phrase. You only need to provide files for patterns that have meaningful translations. Skip files where the English phrases will work (e.g. episode codes, brand names).

```
tutubo/locale/de-de/
    movie_keywords.voc        # ganzer Film, Spielfilm, ...
    documentary_keywords.voc
    ...
```

### Step 3 — Register nothing

The fallback chain is automatic. As soon as the directory exists and at least one `.voc` file is present, calling `set_lang("de-de")` will use your files for the patterns you provided and fall back to `en-us` for everything else.

### Step 4 — Test your translation

Run classification against a set of representative titles in the target language:

```python
import tutubo
from tutubo.content_type import classify_video, ContentType

tutubo.set_lang("de-de")

assert classify_video("Der Pate — Ganzer Film Deutsch") == ContentType.MOVIE
assert classify_video("Metallica — Live in Berlin — Komplettes Konzert") == ContentType.CONCERT
assert classify_video("Tagesschau — Aktuelle Nachrichten Live") == ContentType.LIVE_NEWS
```

No network access is needed. `classify_video()` works entirely offline.

### Step 5 — Translate `tags/` if needed

Auto-tags in `extract_tags()` are used to enrich results with genre, format, and audience labels. If you want genre detection to work in the new language, add translated `.voc` files under `locale/de-de/tags/`. The label names in `_TAG_MANIFEST` are always English; only the phrases inside the files change.

---

## Caching behaviour

All `.voc` loads and compiled patterns are cached with `functools.lru_cache(maxsize=512)`, keyed by `(name, lang)`. The cache is shared across calls for the same language within a process.

Calling `set_lang()` clears all three caches (`_load_voc`, `_voc_regex`, `_voc_set`). If you switch languages frequently in a tight loop, the cache will warm up again on the first classify call after each switch. For bulk processing in a single language, set the language once at startup and leave it.
