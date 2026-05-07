# tutubo

YouTube and YouTube Music metadata library. Searches videos, music tracks, albums, artists, podcasts, and channels — with rich per-item metadata and content-type classification. No pytube dependency.

## Overview

tutubo queries YouTube and YouTube Music search endpoints and channel pages, returning typed Python objects. All metadata comes from search results or channel tabs — no per-video page fetches required unless you explicitly call `.get()`.

## Key Classes

| Class | Purpose | Source |
|---|---|---|
| `YoutubeSearch` | Search YouTube by query, yield typed results | `tutubo/search.py:37` |
| `VideoPreview` | Video result from a YouTube search | `tutubo/models.py:170` |
| `ChannelPreview` | Channel result from a YouTube search | `tutubo/models.py:89` |
| `PlaylistPreview` | Playlist result from a YouTube search | `tutubo/models.py:14` |
| `MusicTrack` | Track result from YouTube Music search | `tutubo/ytmus.py` |
| `MusicAlbum` | Album result from YouTube Music search | `tutubo/ytmus.py` |
| `MusicArtist` | Artist result from YouTube Music search | `tutubo/ytmus.py` |
| `Channel` | Full channel object with tab iteration | `tutubo/channel.py` |
| `Playlist` | Playlist object with video iteration | `tutubo/channel.py` |
| `Video` | Video stub from a channel tab | `tutubo/channel.py` |
| `PodcastPreview` | Podcast show card from channel podcasts tab | `tutubo/channel.py` |
| `YoutubeMusicSearch` | Search YouTube Music catalogue, yield music entities | `tutubo/search.py:416` |
| `ContentType` | Enum of semantic video content types | `mediavocab.taxonomy.ContentType` |
| `classify_video` | Infer `ContentType` from metadata | `mediavocab.text.classify_video` |

## Contents

- [Installation & Quick Start](../README.md)
- [Search API](search.md) — `YoutubeSearch`, 24 factories, `YoutubeMusicSearch`
- [Models Reference](models.md) — all preview types, `Video`, `MusicTrack`, `MusicAlbum`, etc.
- [Channel API](channel.md) — `Channel`, `Playlist`, `PodcastPreview`, `Video`
- [Content-Type Classification](content_type.md) — `ContentType` enum, 30-step priority chain
- [mediavocab Integration](mediavocab.md) — `to_work()` / `to_release()` / `to_entity()` bridge
- [Transport](transport.md) — pluggable session, `curl_cffi` stealth extra, `TUTUBO_TRANSPORT`
- [Locale System](locale.md) — `.voc` files, `lang=` parameter, `MEDIAVOCAB_LANG`
- [Downloading](downloading.md) — `download()` and `download_playlist()` via yt-dlp
- [Testing](testing.md) — fixture-based offline test suite
