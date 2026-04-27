# Models

Models are thin wrappers around raw YouTube API response dicts. All "Preview" types are returned directly from search without fetching the full page; call `.get()` to hydrate a full pytube object.

## VideoPreview / RelatedVideoPreview

```python
v.title          # str
v.author         # channel name
v.video_id       # YouTube video ID
v.watch_url      # https://www.youtube.com/watch?v=...
v.length         # seconds (0 for live streams)
v.is_live        # bool
v.thumbnail_url  # https://img.youtube.com/vi/<id>/default.jpg
v.keywords       # list[str] (empty on preview, populated on full Video)
v.as_dict        # dict representation
v.get()          # returns pytube YouTube object
```

## ChannelPreview

```python
ch.title         # str
ch.channel_id    # YouTube channel ID
ch.channel_url   # https://www.youtube.com/channel/<id>
ch.thumbnail_url # str
ch.get()         # returns pytube Channel object
```

## PlaylistPreview / YoutubeMixPreview

```python
pl.title           # str
pl.playlist_id     # str
pl.playlist_url    # https://www.youtube.com/playlist?list=...
pl.thumbnail_url   # str
pl.featured_videos # list of dicts {videoId, url, image, title}
pl.get()           # returns pytube Playlist object
```

## RelatedSearch

```python
rs.query         # str — the suggested search term
rs.thumbnail_url # str
rs.get()         # returns a new YoutubeSearch for this query
```

## MusicTrack / MusicVideo

```python
t.title       # str
t.artist      # str
t.watch_url   # YouTube Music or YouTube URL
t.length      # seconds or None
t.album       # album name or None (MusicTrack only)
t.thumbnail_url
t.as_dict     # {title, artist, image, url, duration}
```

## MusicAlbum / MusicPlaylist / MusicArtist

```python
a.title        # str
a.artist       # str
a.thumbnail_url
a.tracks       # list[MusicTrack]
a.as_dict      # {title, artist, image, playlist: [...]}
```
