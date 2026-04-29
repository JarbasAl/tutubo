# tutubo

YouTube and YouTube Music metadata library. Searches videos, music tracks, albums, artists, podcasts, and channels — with rich per-item metadata and content-type classification. No pytube dependency.

## Overview

tutubo queries YouTube and YouTube Music search endpoints and channel pages, returning typed Python objects. All metadata comes from search results or channel tabs — no per-video page fetches required unless you explicitly call `.get()`.

## Key Classes

| Class | Purpose | Source |
|---|---|---|
| `YoutubeSearch` | Search YouTube and YouTube Music | `tutubo/search.py` |
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
| `ContentType` | Enum of semantic video content types | `tutubo/content_type.py:246` |
| `classify_video` | Infer `ContentType` from metadata | `tutubo/content_type.py:281` |

## Contents

- [Installation & Quick Start](../README.md)
- [Search API](search.md)
- [Models Reference](models.md)
- [Channel API](channel.md)
- [Content-Type Classification](content_type.md)
- [Locale System](locale.md)
- [Downloading](downloading.md)
- [Testing](testing.md)
