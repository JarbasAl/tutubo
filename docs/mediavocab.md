# mediavocab Integration

`tutubo/mediavocab_bridge.py`

mediavocab is a hard runtime dependency of tutubo. It provides:

- `ContentType` enum and `classify_video()` — consumed by every `VideoPreview` and `Video`
- `parse_title()` — title parser (year, season, episode, variant, edition, source format)
- `extract_tags()` — freeform label extractor (genre, era, format subtype, audience)
- `Work`, `Release`, `Entity` — typed data model for downstream consumers
- Locale system — `.voc` keyword files, `lang=` parameter, `MEDIAVOCAB_LANG` env var

All mapping logic lives in `tutubo/mediavocab_bridge.py`. Model classes delegate via thin `to_work()` / `to_release()` / `to_entity()` methods.

---

## Re-exports from `tutubo`

```python
from tutubo import (
    ContentType,
    classify_video, classify_video_dict, extract_tags,
    parse_title, TitleParseResult,
)
```

These are re-exported for convenience. They are identical to importing directly from mediavocab:

```python
from mediavocab.taxonomy import ContentType
from mediavocab.text import classify_video, classify_video_dict, extract_tags, parse_title, TitleParseResult
```

---

## `VideoPreview.to_work()` and `to_release()`

`tutubo/models.py:361` and `tutubo/models.py:376`

Converts a `VideoPreview` to a `mediavocab.Work` + `mediavocab.Release` pair.

```python
from tutubo import YoutubeSearch

for v in YoutubeSearch.for_movies("blade runner").iterate_movies(max_res=3):
    work = v.to_work()
    release = v.to_release()

    print(work.title, work.year, work.media_type)
    print(release.uri, release.resolution, release.stream_mode)
    print(release.external_ids)    # {"youtube": "<video_id>"}
```

Fields populated from search-result data (no extra network calls):

| `Work` field | Source |
|---|---|
| `title` | `parse_title(v.title).title` — cleaned of year/edition/format tokens |
| `year` | `parse_title(v.title).year` |
| `media_type` | `ContentType.to_routing()` |
| `runtime` | `v.length` (seconds) |
| `season`, `episode` | `parse_title()` |
| `variant_kind` | `parse_title()` — e.g. `FANEDIT`, `DIRECTORS_CUT` |
| `edition` | `parse_title().edition` |
| `content_genres` | From `ContentType.to_routing()` + `extract_tags()` tags, deduped |
| `credits` | Channel name + channel ID as a `Credit(role="channel")` |
| `external_ids` | `{"youtube": video_id}` |

| `Release` field | Source |
|---|---|
| `uri` | `v.watch_url` |
| `platform` | `"youtube"` |
| `resolution` | Badge: `"4K"` → `"2160p"`, `"8K"` → `"4320p"`, `"HD"` → `"1080p"` |
| `container` | `parse_title().source_format` (e.g. `"WEBRip"`, `"BluRay"`) |
| `stream_mode` | `LIVE` / `CONTINUOUS` / `ON_DEMAND` from `ContentType` |
| `accessibility` | `AccessibilityTrack(kind="captions")` when CC badge present |
| `external_ids` | `{"youtube": video_id}` |

Fields **not** populated (YouTube search renderers do not expose them): codec, bitrate, audio channels, default audio language, caption language list, chapters.

---

## Music entity conversion

`tutubo/mediavocab_bridge.py`

| Function | Input | Output |
|---|---|---|
| `music_track_to_work(track)` | `MusicTrack` | `Work` with `MediaType.MUSIC` or `MUSIC_VIDEO` |
| `music_track_to_release(track, work)` | `MusicTrack`, `Work` | `Release` on `platform="youtube_music"` |
| `music_video_to_release(track, work)` | `MusicVideo`, `Work` | `Release` on `platform="youtube"` |
| `music_playlist_to_work(pl)` | `MusicPlaylist` | `Work` with tracklist populated |
| `music_playlist_to_release(pl, work)` | `MusicPlaylist`, `Work` | `Release` on `platform="youtube_music"` |
| `music_album_to_release(album, work)` | `MusicAlbum`, `Work` | `Release` with `label` field |
| `channel_to_entity(channel)` | `Channel` | `Entity(kind=GROUP)` with RSS and channel ID |
| `channel_preview_to_entity(preview)` | `ChannelPreview` | `Entity(kind=GROUP)` |
| `music_artist_to_entity(artist)` | `MusicArtist` | `Entity(kind=GROUP)` |
| `podcast_preview_to_work(pod)` | `PodcastPreview` | `Work` with `MediaType.PODCAST` |
| `podcast_preview_to_release(pod, work)` | `PodcastPreview`, `Work` | `Release` with playlist URI |

---

## `ContentType` → `MediaType` routing

`tutubo/mediavocab_bridge.py:51`

`ContentType.to_routing()` (in mediavocab) returns `(MediaType, content_genres)`. One deliberate override in tutubo:

- `LIVE_NEWS` → `MediaType.GENERIC + [GENRE_NEWS]` instead of mediavocab's default `MediaType.TV`. YouTube live-news uploads are individual video files, not EPG-shaped TV channels — routing them to `TV` would mismatch the schema that EPG-aware downstream consumers expect.

`StreamMode` overrides (`tutubo/mediavocab_bridge.py:42`):

| `ContentType` | `StreamMode` |
|---|---|
| `LIVE` | `LIVE` |
| `LIVE_NEWS` | `LIVE` |
| `LIVE_RADIO` | `CONTINUOUS` |
| `IPTV` | `CONTINUOUS` |
| everything else | `ON_DEMAND` (or `LIVE` if `is_live=True`) |

---

## Example — full pipeline

See [`examples/rich_release.py`](../examples/rich_release.py) for a self-contained demo of all fields that `to_work()` / `to_release()` populate from a synthetic but representative search result.

See [`examples/fanedits.py`](../examples/fanedits.py) for fan-edit detection: `parse_title()` detects fan-edit vocabulary in the title and emits `VariantKind.FANEDIT`, which the bridge maps to `Work.variant_kind`.
