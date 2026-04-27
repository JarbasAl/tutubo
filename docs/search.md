# Search API

`YoutubeSearch` extends pytube's `Search` with typed result iteration and YouTube Music support.

## Basic search

```python
from tutubo import YoutubeSearch, search_yt

# Quick generator — returns dicts by default
for item in search_yt("rob zombie", max_res=5):
    print(item["title"], item["url"])
```

## Typed iterators

```python
from tutubo import YoutubeSearch

s = YoutubeSearch("rob zombie")

for v in s.iterate_videos(max_res=10):
    print(v.title, v.watch_url, v.length)

for ch in s.iterate_channels():
    print(ch.title, ch.channel_url)

for pl in s.iterate_playlists():
    print(pl.title, pl.playlist_url)

for mix in s.iterate_mixes():
    print(mix.title)

for q in s.iterate_queries():
    print(q.query)
```

### `max_res` parameter

`max_res=-1` (default) means unlimited. Pass a positive integer to cap results.

## YouTube Music

```python
from tutubo import YoutubeSearch, search_yt_music

# Convenience generator
for track in search_yt_music("rob zombie dragula"):
    print(track)  # dict with title, artist, url, duration

# Typed Music iterators via YoutubeSearch
s = YoutubeSearch("rob zombie")

for track in s.iterate_music_tracks(max_res=5):
    print(track.title, track.artist, track.watch_url)

for album in s.iterate_music_albums(max_res=3):
    print(album.title, [t.title for t in album.tracks])

for artist in s.iterate_music_artists(max_res=2):
    print(artist.name, [t.title for t in artist.tracks])

for playlist in s.iterate_music_playlists(max_res=2):
    print(playlist.title)

for video in s.iterate_music_videos(max_res=5):
    print(video.title, video.watch_url)
```

## Result types

| Class | Key attributes |
|---|---|
| `VideoPreview` | `title`, `author`, `video_id`, `watch_url`, `length`, `thumbnail_url` |
| `RelatedVideoPreview` | same as `VideoPreview` |
| `ChannelPreview` | `title`, `channel_id`, `channel_url`, `thumbnail_url` |
| `PlaylistPreview` | `title`, `playlist_id`, `playlist_url`, `featured_videos` |
| `YoutubeMixPreview` | same as `PlaylistPreview` |
| `RelatedSearch` | `query`, `thumbnail_url` |
| `MusicTrack` | `title`, `artist`, `watch_url`, `length`, `album` |
| `MusicVideo` | `title`, `artist`, `watch_url`, `length` |
| `MusicAlbum` | `title`, `artist`, `thumbnail_url`, `tracks` |
| `MusicArtist` | `name`, `thumbnail_url`, `tracks` |
| `MusicPlaylist` | `title`, `artist`, `thumbnail_url`, `tracks` |

All preview types have a `.get()` method that fetches the full pytube object.
All types have an `.as_dict` property.
