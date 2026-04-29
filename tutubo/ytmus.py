import json
import time
from ytmusicapi import YTMusic

from tutubo.models import YoutubePreview, Video

_YTMUS = None


def _get_ytmus(max_retries=5):
    """Return the cached YTMusic singleton, creating it on first call.

    Retries on transient connection errors (rate-limiting, DNS hiccups).
    Returns None if all retries fail — callers must guard against this.
    """
    global _YTMUS
    if _YTMUS:
        return _YTMUS
    for i in range(max_retries):
        try:
            _YTMUS = YTMusic()
            break
        except Exception:
            time.sleep(0.5 * (i + 1))
    return _YTMUS


class YTMusicResult(YoutubePreview):
    @property
    def title(self):
        return self._raw_data.get("title")

    @property
    def thumbnail_url(self):
        img = self._raw_data.get("image")
        if not img and self._raw_data.get("thumbnails"):
            img = self._raw_data["thumbnails"][-1]["url"]
        return img

    @property
    def artist(self):
        artist = self._raw_data.get("artist")
        if not artist and self._raw_data.get("artists"):
            artist = ", ".join(a["name"] for a in self._raw_data['artists'])
        return artist

    @property
    def description(self):
        return self._raw_data.get("description")

    @property
    def as_dict(self):
        return self._raw_data

    def __str__(self):
        return json.dumps(self.as_dict, sort_keys=True)


# ---------------------------------------------------------------------------
# Track / Video
# ---------------------------------------------------------------------------

class MusicTrack(YTMusicResult):
    """A song from YouTube Music search or an album track listing."""

    @property
    def watch_url(self) -> str:
        vid = self._raw_data.get("videoId", "")
        return f"https://music.youtube.com/watch?v={vid}" if vid else ""

    @property
    def video_id(self) -> str:
        return self._raw_data.get("videoId", "")

    @property
    def length(self):
        """Duration in seconds, or None if unknown."""
        secs = self._raw_data.get("duration_seconds")
        if secs is not None:
            return int(secs)
        dur = self._raw_data.get("duration")
        if isinstance(dur, str):
            parts = dur.split(":")
            if len(parts) == 2:
                m, s = parts
                return 60 * int(m) + int(s)
            elif len(parts) == 3:
                h, m, s = parts
                return 3600 * int(h) + 60 * int(m) + int(s)
        return None

    @property
    def album(self) -> str:
        """Album name, or empty string."""
        raw = self._raw_data.get("album")
        if isinstance(raw, dict):
            return raw.get("name") or ""
        return raw or ""

    @property
    def year(self):
        """Release year as int, or None."""
        y = self._raw_data.get("year")
        return int(y) if y else None

    @property
    def is_explicit(self) -> bool:
        return bool(self._raw_data.get("isExplicit"))

    @property
    def views(self) -> str:
        """View count label, e.g. '682M views'. Empty string if unavailable."""
        return self._raw_data.get("views") or ""

    @property
    def track_number(self):
        """Track number within album, or None."""
        return self._raw_data.get("trackNumber") or self._raw_data.get("index")

    @property
    def video_type(self) -> str:
        """YouTube Music video type, e.g. 'MUSIC_VIDEO_TYPE_ATV' (audio-only),
        'MUSIC_VIDEO_TYPE_OMV' (official music video), 'MUSIC_VIDEO_TYPE_UGC'."""
        return self._raw_data.get("videoType", "")

    @property
    def is_audio_only(self) -> bool:
        """True for 'Official Audio' auto-generated tracks (no music video)."""
        return "ATV" in self.video_type or "OFFICIAL_SOURCE_MUSIC" in self.video_type

    @property
    def is_music_video(self) -> bool:
        """True for official music video uploads."""
        return "OMV" in self.video_type or "UGC" in self.video_type

    @property
    def category(self) -> str:
        """Result category, e.g. 'Songs', 'Videos'."""
        return self._raw_data.get("category", "")

    @property
    def as_dict(self):
        return {
            "videoId": self.video_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "year": self.year,
            "image": self.thumbnail_url,
            "url": self.watch_url,
            "duration": self.length,
            "views": self.views,
            "explicit": self.is_explicit,
            "audio_only": self.is_audio_only,
            "music_video": self.is_music_video,
            "video_type": self.video_type,
        }


class MusicVideo(MusicTrack):
    """A music video from YouTube (not YouTube Music — uses regular watch URLs)."""

    @property
    def watch_url(self) -> str:
        vid = self._raw_data.get("videoId", "")
        return f"https://www.youtube.com/watch?v={vid}" if vid else ""

    def get(self):
        return Video(self.video_id)


# ---------------------------------------------------------------------------
# Album / Playlist / Artist
# ---------------------------------------------------------------------------

class MusicPlaylist(YTMusicResult):
    """A YouTube Music playlist or album."""

    @property
    def playlist_id(self) -> str:
        return self._raw_data.get("audioPlaylistId") or self._raw_data.get("playlistId", "")

    @property
    def playlist_url(self) -> str:
        pid = self.playlist_id
        return f"https://music.youtube.com/playlist?list={pid}" if pid else ""

    @property
    def year(self):
        y = self._raw_data.get("year")
        return int(y) if y else None

    @property
    def track_count(self) -> int:
        return self._raw_data.get("trackCount", 0) or len(self.tracks)

    @property
    def duration_seconds(self) -> int:
        return self._raw_data.get("duration_seconds", 0) or 0

    @property
    def is_explicit(self) -> bool:
        return bool(self._raw_data.get("isExplicit"))

    @property
    def tracks(self):
        if "tracks" in self._raw_data:
            return [MusicTrack(t) for t in self._raw_data["tracks"] if t.get("videoId")]
        elif "songs" in self._raw_data:
            return [MusicTrack(t) for t in self._raw_data["songs"].get("results", []) if t.get("videoId")]
        return []

    @property
    def as_dict(self):
        return {
            "title": self.title,
            "artist": self.artist,
            "year": self.year,
            "image": self.thumbnail_url,
            "url": self.playlist_url,
            "track_count": self.track_count,
            "explicit": self.is_explicit,
            "playlist": [t.as_dict for t in self.tracks],
        }


def get_album(browse_id: str, playlist_id: str = "") -> dict:
    """Fetch album data, preferring get_playlist when a playlistId is available."""
    ytm = _get_ytmus()
    if playlist_id:
        try:
            data = ytm.get_playlist(playlist_id)
            data.setdefault("browseId", browse_id)
            data.setdefault("playlistId", playlist_id)
            return data
        except Exception:
            pass
    data = ytm.get_album(browse_id)
    data.setdefault("browseId", browse_id)
    return data


class MusicAlbum(MusicPlaylist):
    """A YouTube Music album."""

    @property
    def name(self):
        return self.title

    @property
    def label(self) -> str:
        return self._raw_data.get("label", "")

    @property
    def as_dict(self):
        d = super().as_dict
        d["label"] = self.label
        return d


class MusicArtist(YTMusicResult):
    """A YouTube Music artist."""

    @property
    def name(self) -> str:
        # raw search results nest the name under artists[0]["name"]
        artists = self._raw_data.get("artists")
        if artists and isinstance(artists, list) and artists[0].get("name"):
            return artists[0]["name"]
        return self._raw_data.get("artist") or self._raw_data.get("title") or ""

    @property
    def title(self) -> str:
        return self.name

    @property
    def subscribers(self) -> str:
        """Subscriber count label, e.g. '1.2M subscribers'."""
        return self._raw_data.get("subscribers") or self._raw_data.get("views", "")

    @property
    def description(self) -> str:
        return self._raw_data.get("description") or ""

    @property
    def tracks(self):
        """Top tracks for this artist."""
        songs = self._raw_data.get("songs", {})
        results = songs.get("results", []) if isinstance(songs, dict) else []
        return [MusicTrack(t) for t in results if t.get("videoId")]

    @property
    def as_dict(self):
        return {
            "artist": self.name,
            "image": self.thumbnail_url,
            "subscribers": self.subscribers,
            "description": self.description,
            "playlist": [t.as_dict for t in self.tracks],
        }


def search_yt_music(query, as_dict=True, n_retries=3):
    ytmusic = _get_ytmus(n_retries)
    for r in ytmusic.search(query):
        if r["resultType"] == "video":
            obj = MusicVideo(r)
        elif r["resultType"] == "song":
            obj = MusicTrack(r)
        elif r["resultType"] == "album":
            try:
                a = ytmusic.get_album(r["browseId"])
                r.update(a)
            except Exception:
                continue
            obj = MusicAlbum(r)
        elif r["resultType"] == "playlist":
            try:
                a = ytmusic.get_playlist(r.get("browseId", ""))
                r.update(a)
            except Exception:
                continue
            obj = MusicPlaylist(r)
        elif r["resultType"] == "artist":
            try:
                a = ytmusic.get_artist(r["browseId"])
                r.update(a)
            except Exception:
                continue
            obj = MusicArtist(r)
        else:
            continue
        yield obj.as_dict if as_dict else obj
