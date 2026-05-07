# tutubo

YouTube and YouTube Music metadata library. No pytube dependency. Searches videos, channels, playlists, music tracks, albums, and artists — with per-item content-type classification and lazy channel tab iteration.

## Install

```bash
pip install tutubo
# Downloading requires yt-dlp (optional):
pip install yt-dlp
```

Dependencies: `requests`, `ytmusicapi`, `bs4`, `mediavocab` (hard runtime dep — provides the title parser, content-type taxonomy, locale system, and the `Work`/`Release`/`Entity` data model).

```python
# Title parser, classifier, and ContentType live in mediavocab now.
# tutubo just consumes them for its YouTube use case.
from mediavocab.text import parse_title, classify_video, extract_tags
from mediavocab.taxonomy import ContentType
from mediavocab.locale import voc_regex, voc_set     # stateless — pass lang= per call
```

For convenience the same names are re-exported from the top-level `tutubo` package:

```python
from tutubo import parse_title, classify_video, extract_tags, ContentType, TitleParseResult
```

## Feature Overview

| Feature | What you get |
|---|---|
| YouTube search | `VideoPreview`, `ChannelPreview`, `PlaylistPreview`, mix previews, related queries |
| YouTube Music search | `MusicTrack`, `MusicVideo`, `MusicAlbum`, `MusicPlaylist`, `MusicArtist` |
| Content-type classification | 30 `ContentType` values inferred from title, duration, badges, and channel tags |
| Auto-tagging | `extract_tags()` adds freeform genre/era/format labels orthogonal to ContentType |
| Typed search factories | `YoutubeSearch.for_movies()`, `for_trailers()`, `for_podcasts()`, etc. — 24 factories |
| Channel tab iteration | `.videos`, `.shorts`, `.live`, `.current_live`, `.playlists`, `.podcasts` |
| Podcast shows | `PodcastPreview` with episode count and backing playlist |
| Lazy iteration | `DeferredGeneratorList` — network calls only as items are consumed |
| Downloading | `download()` and `download_playlist()` via yt-dlp subprocess |
| Offline testing | Fixture-based test suite — no network required once fixtures are recorded |

## 5-Minute Quickstart

### Search YouTube

```python
from tutubo import YoutubeSearch

s = YoutubeSearch("rob zombie")

for v in s.iterate_videos(max_res=5):
    print(v.title, v.length, v.published_time, v.short_view_count)
    print("  content_type:", v.content_type)
    print("  cc:", v.has_captions, "| official artist:", v.is_official_artist_channel)
    print("  badges:", v.badges)

for ch in s.iterate_channels():
    print(ch.title, ch.subscriber_count, "verified:", ch.is_verified)

for pl in s.iterate_playlists():
    print(pl.title, pl.video_count, "videos")

for q in s.iterate_queries():     # "People also searched for"
    print(q.query)
```

### Factory classmethods for intent-focused queries

Every factory appends a keyword to your query to improve YouTube's result ranking.

```python
from tutubo import YoutubeSearch

# Appends "full movie" → "blade runner full movie"
for v in YoutubeSearch.for_movies("blade runner").iterate_movies(max_res=5):
    print(v.title, v.length)

# Appends "official trailer"
for v in YoutubeSearch.for_trailers("dune 2").iterate_trailers(max_res=5):
    print(v.title)

# Appends "tutorial"
for v in YoutubeSearch.for_tutorials("python asyncio").iterate_tutorials():
    print(v.title)
```

### Auto-tagging

`extract_tags()` returns freeform labels covering genre, era, format subtype, audience, and niche — orthogonal to `ContentType`.

```python
from mediavocab.text import extract_tags

extract_tags("Lovecraft narrated by Wayne June")
# ["lovecraft", "narrated", "wayne-june"]
```

`VideoPreview.tags` and `Video.tags` expose this automatically. Both `as_dict` outputs include a `"tags"` key. See [docs/content_type.md](docs/content_type.md#auto-tagging) for the full label catalogue.

### Filter any search by content type

```python
from tutubo import YoutubeSearch
from mediavocab.taxonomy import ContentType

s = YoutubeSearch("free movies")
for v in s.iterate_by_content_type(ContentType.MOVIE, max_res=10):
    print(v.title, v.length)
```

### YouTube Music search

```python
from tutubo import YoutubeSearch

s = YoutubeSearch("black sabbath paranoid")

for track in s.iterate_music_tracks(max_res=5):
    print(track.title, track.artist, track.length)
    print("  audio_only:", track.is_audio_only, "| music_video:", track.is_music_video)
    print("  views:", track.views, "| explicit:", track.is_explicit)

for album in s.iterate_music_albums(max_res=3):
    print(album.title, album.artist, album.year, f"({album.track_count} tracks)")
    for t in album.tracks:
        print(f"  {t.track_number}. {t.title} [{t.length}s]")

for artist in s.iterate_music_artists(max_res=2):
    print(artist.name, artist.subscribers)
```

### Convenience functions (return dicts)

```python
from tutubo import search_yt, search_yt_music

for item in search_yt("rob zombie", max_res=10):
    print(item["title"], item["url"], item["published"], item["badges"])

for item in search_yt_music("rob zombie dragula"):
    print(item["title"], item["artist"], item["audio_only"])
```

### Channel metadata and tab iteration

```python
from tutubo import Channel

c = Channel("https://www.youtube.com/@Metallica")
print(c.channel_name, c.subscribers, c.video_count_label)
print("keywords:", c.keywords[:5])
print("rss:", c.rss_url)

# Regular uploads
for video in c.videos:
    print(video.title, video.view_count, video.published_time)
    print("  content_type:", video.content_type)

# Currently on-air stream — single Video or None (reads /@handle/live)
live = c.current_live
if live:
    print("LIVE:", live.title, live.watch_url)

# Full stream archive — past + current (reads /@handle/streams browse tab)
for stream in c.live:
    print(stream.title, stream.is_live)
# Note: .live returns a list, .current_live returns one item or None.
# See docs/channel.md for the full distinction.

# Podcast shows
c2 = Channel("https://www.youtube.com/@TheDissenterRL")
for pod in c2.podcasts:
    print(pod.title, pod.episode_count)
    pl = pod.get()            # hydrates to a Playlist
    for ep in pl.videos:
        print("  episode:", ep.watch_url)
        break
```

### Download

```python
from tutubo.download import download, download_playlist

# Best quality video as .mp4
path = download("https://www.youtube.com/watch?v=EqQuihD0hoI")

# Audio only as .mp3
path = download("https://www.youtube.com/watch?v=EqQuihD0hoI", audio_only=True)

# Max 720p, custom filename and directory
path = download(
    "https://www.youtube.com/watch?v=EqQuihD0hoI",
    output_path="/music",
    filename="dragula",
    quality="720",
)

# Full playlist
paths = download_playlist(
    "https://www.youtube.com/playlist?list=PLBxwSF9JxLuJea2Hn2b_xw-3X7IAfBMZT",
    output_path="/music/rob_zombie",
    audio_only=True,
)
```

## Language Support

Classification keywords are locale-aware. The default language is English
(`en-us`). The locale system is **stateless** — pass `lang=` to each
classification call so concurrent callers do not share global state.

### Setting the language

```python
from tutubo import classify_video, parse_title

ct = classify_video("Película completa HD", length=7200, lang="es")
parsed = parse_title("Star Wars [Edição do Director]", lang="pt-pt")
```

Set the process-wide default via environment variable before starting:

```bash
MEDIAVOCAB_LANG=es-es python my_script.py
```

### Supported language codes

| Code | Notes |
|---|---|
| `en-us` | Default; full coverage |
| `fr-fr` | French |
| `it-it` | Italian |
| `nl-nl` | Dutch |
| `es` | Spanish (shared base for all Spanish variants) |
| `es-es` | Spain Spanish — sparse overrides on top of `es` |
| `es-mx` | Mexican Spanish — sparse overrides on top of `es` |
| `pt` | Portuguese (shared base for all Portuguese variants) |
| `pt-pt` | European Portuguese — sparse overrides on top of `pt` |
| `pt-br` | Brazilian Portuguese — sparse overrides on top of `pt` |

Fallback chain: `es-es` → `es` → `en-us`. Any missing `.voc` file is filled in from the next candidate in the chain.

### Adding a new language

Create `mediavocab/locale/<lang>/` (the locale tree lives in mediavocab and is shared by every consumer) and add `.voc` files for each keyword category you want to translate. You only need to provide files for the patterns that differ — everything else falls back to `en-us`. See [docs/locale.md](docs/locale.md) for the full reference.

## Examples

| File | What it shows |
|---|---|
| `examples/search.py` | Full YouTube search bucketed by result type |
| `examples/mus.py` | YouTube Music search |
| `examples/music_albums.py` | Album track listings via YouTube Music |
| `examples/ch_playlists.py` | Listing channel playlists and their videos |
| `examples/livestreams.py` | Filtering live-only streams from a channel |
| `examples/iptv.py` | Generating `.m3u8` files from YouTube live channels |
| `examples/podcasts.py` | Listing podcast shows and their episodes |
| `examples/related_queries.py` | Related search suggestions |

## Documentation

- [docs/index.md](docs/index.md) — class index and overview
- [docs/search.md](docs/search.md) — full Search API reference
- [docs/channel.md](docs/channel.md) — Channel, Video, Playlist, and PodcastPreview
- [docs/content_type.md](docs/content_type.md) — ContentType enum and classify_video internals
- [docs/models.md](docs/models.md) — all model types with typed field reference
- [docs/downloading.md](docs/downloading.md) — download() and download_playlist()
- [docs/testing.md](docs/testing.md) — fixture-based testing and recording
- [docs/locale.md](docs/locale.md) — locale system, `.voc` files, and adding a new language

## License

Apache 2.0
