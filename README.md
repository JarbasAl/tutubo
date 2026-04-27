# tutubo

YouTube search wrapper built on top of a bundled pytube fork with YouTube Music support.

## Install

```bash
pip install tutubo
```

## Quick start

```python
from tutubo import search_yt, search_yt_music

# YouTube search — returns dicts
for item in search_yt("rob zombie", max_res=10):
    print(item["title"], item["url"])

# YouTube Music search — returns dicts
for item in search_yt_music("rob zombie dragula"):
    print(item)
```

## Typed search

```python
from tutubo import YoutubeSearch
from tutubo.models import VideoPreview, ChannelPreview, PlaylistPreview

s = YoutubeSearch("rob zombie")

for v in s.iterate_videos(max_res=10):
    print(v.title, v.length, v.watch_url)

for ch in s.iterate_channels():
    print(ch.title, ch.channel_url)

for pl in s.iterate_playlists():
    print(pl.title, [f["title"] for f in pl.featured_videos])
```

## YouTube Music

```python
s = YoutubeSearch("rob zombie")

for track in s.iterate_music_tracks(max_res=5):
    print(track.title, track.artist, track.watch_url)

for album in s.iterate_music_albums(max_res=3):
    print(album.title, [t.title for t in album.tracks])
```

## Docs

- [Search API](docs/search.md)
- [Models](docs/models.md)

## Examples

See the [`examples/`](examples/) directory.
