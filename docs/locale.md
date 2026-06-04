# Locale System

`mediavocab.locale` is the canonical home for the keyword vocab and the
loader API. tutubo just consumes it; nothing locale-related ships in
tutubo any more.

Classification keywords are stored in plain `.voc` files, one phrase per
line, organised by language. This lets tutubo classify content in
languages other than English without changing Python code.

The locale loader is **stateless** — there is no `set_lang()` /
`get_lang()` / `TUTUBO_LANG` any more. Pass `lang="xx-yy"` per call;
the default is read once from `MEDIAVOCAB_LANG` at import.

---

## Directory layout

```
mediavocab/locale/
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
        ...
    es-es/
        live_news_keywords.voc  # Spain-specific overrides only
    es-mx/  fr-fr/  it-it/  nl-nl/  pt/  pt-pt/  pt-br/
        ...
```

A variant directory (e.g. `es-es`) only needs files that differ from
the shared base (`es`). Everything else falls back through the chain.

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
complete film
```

Example — `es/movie_keywords.voc`:

```
película completa
pelicula completa
largometraje
```

---

## Fallback chain

When a `.voc` file is requested for a given language, the loader walks
this chain and returns the first file it finds:

1. Exact locale match — e.g. `es-es`
2. Language-only code — e.g. `es`
3. `en-us`

So `es-es` and `es-mx` automatically inherit all `es/` files they do
not override. Any unsupported locale falls back to English.

Example — requesting `movie_keywords` with lang `de-de` (not supported):

```
de-de/movie_keywords.voc   → not found
de/movie_keywords.voc      → not found
en-us/movie_keywords.voc   → found, use this
```

---

## Public API

The locale system is **stateless** and thread-safe — there is no global
mutable language. Pass `lang=` to every call. The default comes from the
`MEDIAVOCAB_LANG` environment variable read once at import (falling back
to `"en-us"`); this default is read-only at runtime.

### `voc_regex(name, lang=None) -> Optional[re.Pattern]`

Compiled word-boundary alternation regex from the named `.voc` file.
Returns `None` if the file is empty or missing in the fallback chain.

```python
from mediavocab.locale import voc_regex

rx_en = voc_regex("cut_directors", lang="en-us")
rx_pt = voc_regex("cut_directors", lang="pt-pt")
rx_default = voc_regex("cut_directors")  # uses MEDIAVOCAB_LANG / "en-us"
```

### `voc_set(name, lang=None) -> frozenset[str]`

Frozenset of lowercased phrases from the named `.voc` file. Used for
intersection checks against tag-like input (channel tags, hashtags).

```python
from mediavocab.locale import voc_set

movie_tags = voc_set("channel_movie_tags", lang="en-us")
channel_tags = {"full movie", "bollywood films", "comedy"}
if channel_tags & movie_tags:
    # channel is a movie channel
    ...
```

### `get_default_lang() -> str`

Return the import-time default language (the value of `MEDIAVOCAB_LANG`
or `"en-us"` if unset). Read-only.

### `MEDIAVOCAB_LANG` environment variable

Set before starting the Python process to switch the default language:

```bash
MEDIAVOCAB_LANG=it-it python my_script.py
```

---

## Per-call language

Concurrent callers should always pass `lang=` explicitly so different
tenants / requests / threads do not interfere — the cache is keyed on
`(name, lang)` so different languages cannot collide.

```python
from mediavocab.text import classify_video, parse_title

ct_pt  = classify_video("Filme Completo HD", length=7200, lang="pt-pt")
ct_es  = classify_video("Película completa HD", length=7200, lang="es")
parsed = parse_title("Star Wars [Edição do Director]", lang="pt-pt")
```

---

## Caching behaviour

All `.voc` loads and compiled patterns are cached with
`functools.lru_cache(maxsize=512)`, keyed on `(name, lang)`. The cache
is shared across calls for the same `(name, lang)` pair within a
process; different languages are cached independently and never evict
each other.

There is no public cache-clear API. The only way to invalidate is to
restart the process.

---

## Structural patterns that stay in Python

Some patterns are not expressed in `.voc` files because they are
numeric, structural, or language-universal:

| Pattern | Reason |
|---|---|
| `S01E02`, `Season N Episode N` | Standardised production codes; identical across all languages |
| `Top \d+` | Numeric; the word "top" plus a number needs no translation |
| Duration gates (`length < 62`, `length >= 3600`, …) | Numeric thresholds; not linguistic |
| `is_live`, `is_upcoming`, `is_podcast` flag checks | Boolean signals from publisher data |

---

## The `tags/` subdirectory

Auto-tags (returned by `extract_tags()`) are also keyword-driven. Their
`.voc` files live in `locale/<lang>/tags/`. The mapping from label name
to file stem is defined in `_TAG_MANIFEST` inside
`mediavocab.text.classify`.

```python
("horror",     "tags/horror"),
("full-album", "tags/full-album"),
("narrated",   "tags/narrated"),
```

So `voc_regex("tags/horror")` loads `locale/<lang>/tags/horror.voc`.
The label returned by `extract_tags()` is the first element of each
tuple, regardless of language.

---

## Channel tag `.voc` files

Files named `channel_*.voc` (e.g. `channel_news_tags.voc`,
`channel_music_tags.voc`) list phrases that, when found in a channel's
keyword tags, boost that channel's content into a specific
`ContentType`.

These files should include multilingual signals. Channel operators tag
their channels in whatever language they operate in — a French news
channel may use `"actualités"` regardless of what language the viewer
has set. Include those terms in `en-us/channel_news_tags.voc` so they
are recognised under the default fallback.

---

## Supported languages

| Code | Notes |
|---|---|
| `en-us` | Default; full `.voc` coverage |
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
mkdir mediavocab/locale/de-de
mkdir mediavocab/locale/de-de/tags
```

If the language has regional variants (e.g. `de-at`, `de-ch`), create
`de/` as the shared base and add the variant directories with only the
files that differ.

### Step 2 — Translate `.voc` files

Copy from `en-us/` and translate phrase by phrase. You only need to
provide files for patterns that have meaningful translations. Skip
files where the English phrases will work (episode codes, brand names).

### Step 3 — Test your translation

```python
from mediavocab.text import classify_video
from tutubo import ContentType

assert classify_video("Der Pate — Ganzer Film Deutsch", lang="de-de") == ContentType.MOVIE
assert classify_video("Metallica — Live in Berlin — Komplettes Konzert", lang="de-de") == ContentType.CONCERT
```

No network access is needed. `classify_video()` works entirely offline.
